"""Projects, drafts, versions on disk. Layout mirrors the proposal's SharePoint structure.

data/projects/<CODE> <Name>/
  project.json
  01_meeting_docs/<meeting>.register.json   what each meeting said
  02_master/register.json                    approved master (source of truth)
  02_master/versions/vX.Y/{register.json, master.docx}
  03_transcripts/<meeting>.txt
  _pending/{register.json, changes.json}     the one open draft
"""
import json
import re
import threading
from datetime import date
from pathlib import Path

from . import config
from .diagram import mermaid_from_steps
from .models import Change, Project, Register
from .render import render_docx

_lock = threading.RLock()
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,29}$")


class StorageError(ValueError):
    """A problem the user can fix (bad code, duplicate, nothing to approve...)."""


def _write(path: Path, text: str | bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            tmp.write_bytes(text)
        else:
            tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except FileNotFoundError as e:
        if len(str(tmp)) >= 250:  # Windows stops at 260 characters and reports it as "not found"
            raise StorageError(
                f"Cannot save: the folder path is too long for Windows ({len(str(tmp))} characters). "
                "Set REQDOC_DATA_DIR in .env to a shorter folder, for example C:\\ReqDocData."
            ) from e
        raise


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _-]+", "", text).strip()


def projects_dir() -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.DATA_DIR / "projects"


# --- projects ------------------------------------------------------------------

def project_dir(code: str) -> Path:
    if not CODE_RE.match(code or ""):
        raise StorageError("Project code must be 2-30 letters, numbers, - or _ (e.g. PRJ-0421)")
    root = projects_dir()
    if root.exists():
        for d in root.iterdir():
            if d.is_dir() and (d.name == code or d.name.startswith(code + " ")) and (d / "project.json").exists():
                return d
    raise StorageError(f"Project {code} not found")


def create_project(code: str, name: str, owner: str = "") -> Project:
    code = (code or "").strip().upper()
    if not CODE_RE.match(code):
        raise StorageError("Project code must be 2-30 letters, numbers, - or _ (e.g. PRJ-0421)")
    if not name.strip():
        raise StorageError("Project name is required")
    with _lock:
        try:
            project_dir(code)
        except StorageError:
            pass
        else:
            raise StorageError(f"Project {code} already exists")
        proj = Project(code=code, name=name.strip(), owner=owner.strip(), created=date.today().isoformat())
        folder = projects_dir() / f"{code} {_safe_name(name)}".strip()
        _write(folder / "project.json", proj.model_dump_json(indent=2))
        for sub in ("01_meeting_docs", "02_master", "03_transcripts", "_pending"):
            (folder / sub).mkdir(exist_ok=True)
        return proj


def get_project(code: str) -> Project:
    return Project.model_validate_json((project_dir(code) / "project.json").read_text(encoding="utf-8"))


def list_projects() -> list[dict]:
    out = []
    root = projects_dir()
    for d in sorted(root.iterdir()) if root.exists() else []:
        if (d / "project.json").exists():
            proj = Project.model_validate_json((d / "project.json").read_text(encoding="utf-8"))
            master = load_master(proj.code)
            out.append({**proj.model_dump(), "version": master.version if master else None,
                        "has_draft": has_draft(proj.code), "meetings": len(list((d / "01_meeting_docs").glob("*.json")))})
    return out


# --- registers -----------------------------------------------------------------

def _load_register(path: Path) -> Register | None:
    return Register.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def load_master(code: str) -> Register | None:
    return _load_register(project_dir(code) / "02_master" / "register.json")


def has_draft(code: str) -> bool:
    return (project_dir(code) / "_pending" / "register.json").exists()


def load_draft(code: str) -> Register | None:
    return _load_register(project_dir(code) / "_pending" / "register.json")


def save_draft(code: str, reg: Register) -> None:
    with _lock:
        folder = project_dir(code) / "_pending"
        if not (folder / "register.json").exists():
            raise StorageError("There is no open draft for this project")
        reg.diagram_mermaid = mermaid_from_steps(reg.tobe_steps)
        _write(folder / "register.json", reg.model_dump_json(indent=2))


def create_draft(code: str, reg: Register, changes: list[Change] | None = None) -> None:
    """Start the single open draft. Refuses if one is already open (unreviewed)."""
    with _lock:
        folder = project_dir(code) / "_pending"
        if (folder / "register.json").exists():
            raise StorageError("This project already has an unreviewed draft. Approve or discard it first.")
        _write(folder / "register.json", reg.model_dump_json(indent=2))
        _write(folder / "changes.json", json.dumps([c.model_dump() for c in changes or []], indent=2))


def discard_draft(code: str) -> None:
    with _lock:
        for name in ("register.json", "changes.json"):
            (project_dir(code) / "_pending" / name).unlink(missing_ok=True)


def load_changes(code: str) -> list[Change]:
    path = project_dir(code) / "_pending" / "changes.json"
    return [Change(**c) for c in json.loads(path.read_text(encoding="utf-8"))] if path.exists() else []


def save_changes(code: str, changes: list[Change]) -> None:
    with _lock:
        _write(project_dir(code) / "_pending" / "changes.json", json.dumps([c.model_dump() for c in changes], indent=2))


def draft_lock():
    """Held while a draft is read-modified-written (API edits, accepting changes)."""
    return _lock


# --- meetings and transcripts --------------------------------------------------

def save_transcript(code: str, meeting_id: str, text: str) -> None:
    _write(project_dir(code) / "03_transcripts" / f"{meeting_id}.txt", text)


def load_transcript(code: str, meeting_id: str) -> str | None:
    path = project_dir(code) / "03_transcripts" / f"{_safe_name(meeting_id)}.txt"
    return path.read_text(encoding="utf-8") if path.exists() else None


def save_meeting_doc(code: str, meeting_id: str, reg: Register) -> None:
    _write(project_dir(code) / "01_meeting_docs" / f"{meeting_id}.register.json", reg.model_dump_json(indent=2))


def new_meeting_id(code: str, meeting_date: str, title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:30].strip("-") or "meeting"
    base = f"{meeting_date}_{code}_{slug}"
    taken = {p.stem.removesuffix(".register") for p in (project_dir(code) / "01_meeting_docs").glob("*.json")}
    taken |= {p.stem for p in (project_dir(code) / "03_transcripts").glob("*.txt")}
    mid, n = base, 2
    while mid in taken:
        mid, n = f"{base}-{n}", n + 1
    return mid


def list_meetings(code: str) -> list[dict]:
    out = []
    for p in sorted((project_dir(code) / "01_meeting_docs").glob("*.register.json")):
        reg = Register.model_validate_json(p.read_text(encoding="utf-8"))
        if reg.meetings:
            out.append(reg.meetings[-1].model_dump())
    return out


# --- versions ------------------------------------------------------------------

def next_version(current: str | None, major: bool = False) -> str:
    if not current:
        return "1.0"
    a, b = (int(x) for x in current.split(".")[:2])
    return f"{a + 1}.0" if major else f"{a}.{b + 1}"


def list_versions(code: str) -> list[str]:
    root = project_dir(code) / "02_master" / "versions"
    if not root.exists():
        return []
    vs = [d.name.removeprefix("v") for d in root.iterdir() if d.is_dir()]
    return sorted(vs, key=lambda v: tuple(int(x) for x in v.split(".")))


def approve(code: str, reviewer: str, major: bool = False) -> Register:
    """Draft -> new approved master version. Blocked while changes are still pending."""
    if not reviewer.strip():
        raise StorageError("Reviewer name is required to approve")
    with _lock:
        draft = load_draft(code)
        if draft is None:
            raise StorageError("There is no draft to approve")
        pending = [c for c in load_changes(code) if c.decision == "pending"]
        if pending:
            raise StorageError(f"{len(pending)} change(s) still need a decision (accept or reject)")
        master = load_master(code)
        draft.version = next_version(master.version if master else None, major)
        draft.doc_status = "APPROVED"
        draft.reviewer = reviewer.strip()
        draft.diagram_mermaid = mermaid_from_steps(draft.tobe_steps)
        folder = project_dir(code) / "02_master"
        vdir = folder / "versions" / f"v{draft.version}"
        payload = draft.model_dump_json(indent=2)
        _write(vdir / "register.json", payload)
        _write(vdir / "master.docx", render_docx(draft))
        _write(folder / "register.json", payload)
        discard_draft(code)
        return draft


def get_register(code: str, version: str = "latest") -> Register:
    """version: 'draft', 'latest' (approved master, else the draft) or e.g. '1.1'."""
    if version == "draft":
        reg = load_draft(code)
        if reg is None:
            raise StorageError("There is no draft")
    elif version == "latest":
        reg = load_master(code) or load_draft(code)
        if reg is None:
            raise StorageError("Nothing to export yet. Upload a meeting first.")
    else:
        if not re.fullmatch(r"\d+\.\d+", version):
            raise StorageError("Invalid version")
        reg = _load_register(project_dir(code) / "02_master" / "versions" / f"v{version}" / "register.json")
        if reg is None:
            raise StorageError(f"Version {version} not found")
    return reg


def export_docx(code: str, version: str = "latest") -> tuple[bytes, str]:
    """(docx bytes, filename)."""
    proj = get_project(code)
    reg = get_register(code, version)
    suffix = "_DRAFT" if reg.doc_status == "DRAFT" else ""
    name = f"{proj.code}_{_safe_name(proj.name).replace(' ', '-')}_v{reg.version}{suffix}.docx"
    return render_docx(reg), name
