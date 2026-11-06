"""One background worker runs meeting jobs one at a time (Whisper and Ollama both saturate the CPU)."""
import queue
import re
import shutil
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config, storage
from .changes import compute_changes
from .documents import read_documents, segments_to_located_text
from .llm import LLMError, OllamaClient
from .parsers import parse_transcript
from .pipeline import generate_register
from .transcribe import is_recording, segments_to_text, transcribe

STAGES = ["queued", "transcribing", "extracting", "comparing", "done", "error"]


@dataclass
class Job:
    id: str
    project: str
    title: str
    meeting_date: str
    filename: str
    path: str
    is_recording: bool
    kind: str = "meeting"  # "meeting" (recording or transcript) or "document" (a pack of supporting files)
    paths: list[str] = field(default_factory=list)  # every file of a document pack
    stage: str = "queued"
    progress: float = 0.0  # 0..1 inside the current stage
    message: str = "Waiting in the queue"
    error: str = ""
    result: str = ""  # human summary when done
    draft_created: bool = False  # the UI hides the "ready" banner once that draft is approved or discarded
    created: float = field(default_factory=time.time)
    started: float = 0.0
    finished: float = 0.0

    def public(self) -> dict:
        d = asdict(self)
        d.pop("path")
        d.pop("paths")
        d["elapsed"] = round((self.finished or time.time()) - (self.started or self.created))
        return d


class JobRunner:
    def __init__(self, llm_factory=OllamaClient, transcribe_fn=transcribe):
        self.llm_factory = llm_factory
        self.transcribe_fn = transcribe_fn
        self.jobs: dict[str, Job] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # --- public ---

    def active_for(self, project: str) -> bool:
        with self._lock:
            return any(j.project == project and j.stage not in ("done", "error") for j in self.jobs.values())

    def _check_can_take(self, project: str) -> None:
        storage.project_dir(project)  # validates the code
        if storage.has_draft(project):
            raise storage.StorageError("This project has an unreviewed draft. Approve or discard it before adding another meeting or documents.")
        if self.active_for(project):
            raise storage.StorageError("Something for this project is already being processed.")

    @staticmethod
    def _save(folder: Path, filename: str, data_stream, n: int = 0) -> Path:
        safe = "".join(c for c in Path(filename).name if c.isalnum() or c in "._- ") or "upload"
        path = folder / (f"{n:02d}_{safe}" if n else safe)
        with open(path, "wb") as out:
            shutil.copyfileobj(data_stream, out)
        return path

    def submit(self, project: str, title: str, meeting_date: str, filename: str, data_stream) -> Job:
        """Save the upload to disk and queue it. Raises StorageError if the project can't take a meeting now."""
        self._check_can_take(project)
        job_id = uuid.uuid4().hex[:12]
        folder = config.DATA_DIR / "_uploads" / job_id
        folder.mkdir(parents=True, exist_ok=True)
        path = self._save(folder, filename, data_stream)
        return self._queue_job(Job(job_id, project, title, meeting_date, path.name, str(path), is_recording(path)))

    def submit_documents(self, project: str, title: str, received: str, files: list[tuple[str, object]]) -> Job:
        """A pack of supporting documents read together as one source (one review)."""
        self._check_can_take(project)
        job_id = uuid.uuid4().hex[:12]
        folder = config.DATA_DIR / "_uploads" / job_id
        folder.mkdir(parents=True, exist_ok=True)
        paths = [self._save(folder, name, stream, n) for n, (name, stream) in enumerate(files, 1)]
        names = ", ".join(Path(name).name for name, _ in files)
        job = Job(job_id, project, title, received, names, str(paths[0]), False, kind="document", paths=[str(p) for p in paths])
        return self._queue_job(job)

    def _queue_job(self, job: Job) -> Job:
        job_id = job.id
        with self._lock:
            self.jobs[job_id] = job
            for old in sorted(self.jobs.values(), key=lambda j: j.created)[:-50]:
                if old.stage in ("done", "error"):
                    del self.jobs[old.id]
        self._queue.put(job_id)
        self._ensure_worker()
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def latest_for(self, project: str) -> Job | None:
        with self._lock:
            mine = [j for j in self.jobs.values() if j.project == project]
        return max(mine, key=lambda j: j.created, default=None)

    # --- worker ---

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, name="reqdoc-worker", daemon=True)
                self._thread.start()

    def _loop(self) -> None:
        while True:
            job = self.jobs.get(self._queue.get())
            if job is not None:
                self.run(job)

    def _set(self, job: Job, stage: str | None = None, message: str | None = None, progress: float | None = None) -> None:
        if stage:
            job.stage = stage
        if message is not None:
            job.message = message
        if progress is not None:
            job.progress = round(progress, 3)

    def run(self, job: Job) -> None:
        job.started = time.time()
        try:
            self._process(job)
        except (LLMError, storage.StorageError, ValueError) as e:
            self._fail(job, str(e))
        except Exception as e:  # unexpected: keep the traceback in the console for the developer
            traceback.print_exc()
            self._fail(job, f"Unexpected error: {e}")
        finally:
            job.finished = time.time()
            shutil.rmtree(Path(job.path).parent, ignore_errors=True)  # recordings are never kept

    def _fail(self, job: Job, message: str) -> None:
        job.stage, job.error, job.message = "error", message, "Failed"

    def _process(self, job: Job) -> None:
        code = job.project
        proj = storage.get_project(code)
        meeting_id = storage.new_meeting_id(code, job.meeting_date, job.title)
        progress = lambda stage: (lambda msg, frac: self._set(job, stage, msg, frac))  # noqa: E731

        # 1. text
        warnings: list[str] = []
        if job.kind == "document":
            self._set(job, "extracting", f"Reading {len(job.paths)} document{'s' if len(job.paths) > 1 else ''}", 0.0)
            # the saved names start with a counter (01_); show people the name they uploaded
            originals = [Path(p).name.split("_", 1)[1] if re.match(r"^\d{2}_", Path(p).name) else Path(p).name for p in job.paths]
            segments, warnings = read_documents([Path(p) for p in job.paths], progress("extracting"), originals)
            storage.save_transcript(code, meeting_id, segments_to_located_text(segments))
        elif job.is_recording:
            self._set(job, "transcribing", "Loading the speech model (first time only)", 0.0)
            segments = self.transcribe_fn(job.path, progress("transcribing"))
            storage.save_transcript(code, meeting_id, segments_to_text(segments))
        else:
            self._set(job, "extracting", "Reading the transcript", 0.0)
            segments = parse_transcript(job.path)
            storage.save_transcript(code, meeting_id, segments_to_text(segments))

        # 2. requirements
        self._set(job, "extracting", "Finding requirements", 0.0)
        llm = self.llm_factory()
        reg = generate_register(segments, llm, code, proj.name, job.title, job.meeting_date, progress("extracting"),
                                source=job.kind)
        reg.meetings[-1].id = meeting_id
        reg.meetings[-1].source_file = job.filename
        for group in (reg.requirements, reg.business_rules, reg.decisions, reg.actions, reg.questions, reg.risks):
            for item in group:
                item.source_meeting = meeting_id
        storage.save_meeting_doc(code, meeting_id, reg)

        # 3. first meeting -> draft; later meeting -> change list against the master
        master = storage.load_master(code)
        if master is None:
            storage.create_draft(code, reg)
            job.draft_created = True
            job.result = (f"{len(reg.requirements)} requirements, {len(reg.decisions)} decisions, "
                          f"{len(reg.actions)} actions, {len(reg.questions)} open questions")
        else:
            self._set(job, "comparing", "Comparing with the master document", 0.0)
            changes = compute_changes(master, reg, segments, llm, progress("comparing"))
            if changes:
                draft = master.model_copy(deep=True)
                draft.meetings.append(reg.meetings[-1])
                draft.doc_status, draft.reviewer = "DRAFT", ""
                storage.create_draft(code, draft, changes)
                job.draft_created = True
                kinds = {}
                for c in changes:
                    kinds[c.type] = kinds.get(c.type, 0) + 1
                words = lambda k: re.sub(r"(?<!^)(?=[A-Z])", " ", k).lower()  # noqa: E731  ActionDone -> action done
                job.result = f"{len(changes)} changes to review: " + ", ".join(f"{n} {words(k)}" for k, n in kinds.items())
            else:
                job.result = "No new information compared with the master document. Nothing to review."
        if warnings:
            job.result += " Note: " + " ".join(warnings)
        self._set(job, "done", "Done", 1.0)


runner = JobRunner()
