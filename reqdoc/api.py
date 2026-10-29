"""FastAPI app: JSON API under /api, and the built React app at /."""
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, flowchart, storage
from .changes import apply_change, item_text, next_id, prefix_for
from .dates import resolve_due, today_sgt
from .jobs import runner
from .models import ITEM_CATEGORIES, LIST_CATEGORIES, Register
from .parsers import parse_lines
from .transcribe import AUDIO_EXTENSIONS

app = FastAPI(title="ReqDoc AI")

TRANSCRIPT_EXTENSIONS = {".vtt", ".docx", ".txt", ".md"}
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@app.exception_handler(storage.StorageError)
async def storage_error(_: Request, exc: storage.StorageError):
    status = 404 if "not found" in str(exc).lower() else 400
    return JSONResponse({"detail": str(exc)}, status_code=status)


class NewProject(BaseModel):
    code: str
    name: str
    owner: str = ""


class Approve(BaseModel):
    reviewer: str
    major: bool = False


class Decision(BaseModel):
    decision: str


class DiagramRequest(BaseModel):
    steps: list[str]
    cols: int = 4
    palette: str = "web"


# --- health --------------------------------------------------------------------

@app.get("/api/health")
def health():
    from .transcribe import model_available

    ollama_ok, model_ok, detail = False, False, ""
    try:
        import ollama

        names = [m.model for m in ollama.Client(host=config.OLLAMA_HOST).list().models]
        ollama_ok = True
        model_ok = any(n == config.OLLAMA_MODEL or n.split(":")[0] == config.OLLAMA_MODEL for n in names)
        if not model_ok:
            detail = f"Model '{config.OLLAMA_MODEL}' is not downloaded. Run: ollama pull {config.OLLAMA_MODEL}"
    except Exception:
        detail = "Cannot connect to Ollama. Start Ollama (system tray), then refresh."
    return {"ollama": ollama_ok, "model": model_ok, "model_name": config.OLLAMA_MODEL, "detail": detail,
            "whisper_model": config.WHISPER_MODEL, "whisper_ready": model_available()}


# --- projects ------------------------------------------------------------------

@app.get("/api/projects")
def list_projects():
    return storage.list_projects()


@app.post("/api/projects", status_code=201)
def create_project(body: NewProject):
    return storage.create_project(body.code, body.name, body.owner)


@app.get("/api/projects/{code}")
def get_project(code: str):
    proj = storage.get_project(code)
    master = storage.load_master(code)
    draft = storage.load_draft(code)
    job = runner.latest_for(proj.code)
    changes = storage.load_changes(code) if draft else []
    return {
        "project": proj,
        "master_version": master.version if master else None,
        "has_draft": draft is not None,
        "draft_status": draft.doc_status if draft else None,
        "pending_changes": sum(1 for c in changes if c.decision == "pending"),
        "total_changes": len(changes),
        "versions": storage.list_versions(code),
        "meetings": storage.list_meetings(code),
        "job": job.public() if job else None,
        "accepted_files": sorted(AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS),
    }


# --- upload and jobs -----------------------------------------------------------

@app.post("/api/projects/{code}/meetings", status_code=202)
def upload_meeting(code: str, file: UploadFile = File(...), title: str = Form(...), date: str = Form(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS:
        raise HTTPException(400, f"'{ext or 'this'}' files are not supported. Use a recording "
                                 f"({', '.join(sorted(AUDIO_EXTENSIONS))}) or a transcript (.vtt, .docx, .txt).")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise HTTPException(400, "Date must look like 2026-10-22")
    title = title.strip()
    if not title or len(title) > 120:
        raise HTTPException(400, "Meeting title is required (max 120 characters)")
    job = runner.submit(code, title, date, file.filename or "upload", file.file)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = runner.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job.public()


# --- registers -----------------------------------------------------------------

@app.get("/api/projects/{code}/register")
def get_register(code: str, version: str = "latest"):
    """Read-only view: 'latest' (approved master, else draft), 'draft', or a version like '1.0'."""
    return storage.get_register(code, version)


# --- draft ---------------------------------------------------------------------

@app.get("/api/projects/{code}/draft")
def get_draft(code: str):
    draft = storage.load_draft(code)
    if draft is None:
        raise HTTPException(404, "There is no open draft")
    return draft


def _stamp_actions(body: Register, current: Register) -> None:
    """Keep the action dates honest when people edit them in the browser."""
    meeting_dates = {m.id: m.date for m in current.meetings}
    old = {a.id: a for a in current.actions}
    for a in body.actions:
        prev = old.get(a.id)
        if prev:  # history is written by the server, not the browser
            a.raised_date, a.updates = prev.raised_date, prev.updates
            a.closed_meeting, a.closed_date = prev.closed_meeting, prev.closed_date
        a.raised_date = a.raised_date or meeting_dates.get(a.source_meeting, "")
        # the spoken due text changed and nobody picked a date by hand: work the date out again
        typed_new_text = a.due.strip() and (prev is None or prev.due != a.due)
        if typed_new_text and (prev is None or a.due_date == prev.due_date):
            a.due_date = resolve_due(a.due, a.raised_date) or a.due_date
        if a.status in ("Done", "Withdrawn") and not a.closed_date:
            a.closed_date = today_sgt()
        elif a.status == "Open":
            a.closed_meeting = a.closed_date = ""


@app.put("/api/projects/{code}/draft")
def put_draft(code: str, body: Register):
    with storage.draft_lock():
        current = storage.load_draft(code)
        if current is None:
            raise HTTPException(404, "There is no open draft")
        # the browser may edit content, never identity, status or history
        for field in ("schema_version", "project_code", "project_name", "version", "doc_status", "reviewer",
                      "meetings", "change_log"):
            setattr(body, field, getattr(current, field))
        meeting = current.meetings[-1].id if current.meetings else ""
        for cat in ITEM_CATEGORIES:  # rows added in the browser: drop blanks, number the rest
            kept = [i for i in getattr(body, cat) if i.id or item_text(i).strip()]
            setattr(body, cat, kept)
            for item in kept:
                if not item.id:
                    item.id = next_id(body, prefix_for(cat, item.model_dump()))
                if not item.source_meeting:
                    item.source_meeting = meeting
        _stamp_actions(body, current)
        for cat in LIST_CATEGORIES:
            if cat == "glossary":
                body.glossary = [g for g in body.glossary if g.term.strip()]
            else:
                setattr(body, cat, [s.strip() for s in getattr(body, cat) if s.strip()])
        storage.save_draft(code, body)
        return storage.load_draft(code)


@app.delete("/api/projects/{code}/draft", status_code=204)
def discard_draft(code: str):
    storage.discard_draft(code)
    return Response(status_code=204)


@app.post("/api/projects/{code}/approve")
def approve(code: str, body: Approve):
    reg = storage.approve(code, body.reviewer, body.major)
    return {"version": reg.version}


# --- follow-up changes ---------------------------------------------------------

@app.get("/api/projects/{code}/changes")
def get_changes(code: str):
    return storage.load_changes(code)


@app.post("/api/projects/{code}/changes/{change_id}")
def decide_change(code: str, change_id: str, body: Decision):
    if body.decision not in ("accepted", "rejected"):
        raise HTTPException(400, "decision must be 'accepted' or 'rejected'")
    with storage.draft_lock():
        changes = storage.load_changes(code)
        change = next((c for c in changes if c.id == change_id), None)
        if change is None:
            raise HTTPException(404, "Change not found")
        if change.decision != "pending":
            raise HTTPException(409, f"This change was already {change.decision}")
        if body.decision == "accepted":
            draft = storage.load_draft(code)
            if draft is None:
                raise HTTPException(404, "There is no open draft")
            try:
                apply_change(draft, change)
            except ValueError as e:
                raise HTTPException(400, str(e))
            storage.save_draft(code, draft)
        change.decision = body.decision
        storage.save_changes(code, changes)
        return changes


@app.post("/api/projects/{code}/changes-accept-safe")
def accept_safe(code: str):
    """Accept every pending change except conflicts, which always need a person's choice."""
    with storage.draft_lock():
        changes = storage.load_changes(code)
        draft = storage.load_draft(code)
        if draft is None:
            raise HTTPException(404, "There is no open draft")
        for c in changes:
            if c.decision == "pending" and c.type != "Conflict":
                try:
                    apply_change(draft, c)
                except ValueError:
                    continue
                c.decision = "accepted"
        storage.save_draft(code, draft)
        storage.save_changes(code, changes)
        return changes


# --- transcripts and export ----------------------------------------------------

@app.get("/api/projects/{code}/transcripts/{meeting_id}")
def get_transcript(code: str, meeting_id: str):
    text = storage.load_transcript(code, meeting_id)
    if text is None:
        raise HTTPException(404, "Transcript not found")
    return [{"timestamp": s.timestamp, "speaker": s.speaker, "text": s.text} for s in parse_lines(text.splitlines())]


@app.get("/api/projects/{code}/export.docx")
def export_docx(code: str, version: str = "latest", doc: str = "spec"):
    data, name = storage.export_docx(code, version, doc)
    return Response(data, media_type=DOCX_TYPE, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/api/diagram.svg")
def diagram_svg(body: DiagramRequest):
    """Stateless: the website sends the steps it is showing, so the picture follows unsaved edits."""
    if len(body.steps) > 200 or any(len(s) > 2000 for s in body.steps):
        raise HTTPException(422, "Too many or too long steps for a diagram")
    return Response(flowchart.to_svg(body.steps, max(1, min(body.cols, 6)), body.palette), media_type="image/svg+xml")


# --- the React app -------------------------------------------------------------

_dist = config.FRONTEND_DIST
if (_dist / "index.html").exists():
    if (_dist / "static").exists():
        app.mount("/static", StaticFiles(directory=_dist / "static"), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def no_frontend():
        return JSONResponse({"detail": "The web app is not built yet. Run setup.ps1 (needs Node.js), or see README."}, status_code=503)
