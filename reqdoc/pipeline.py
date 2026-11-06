"""chunk -> extract -> merge -> evidence check -> register."""
import re
from bisect import bisect_right
from collections.abc import Callable
from difflib import SequenceMatcher

from . import config
from .dates import resolve_due
from .diagram import mermaid_from_steps
from .llm import LLMClient
from .models import (
    Action, ActionsPass, Decision, DecisionsPass, ExtractedRequirement, Extraction, IssuesPass, MeetingInfo, ProcessPass,
    Question, Register, Requirement, RequirementsPass, Risk, Rule, Segment, Summary,
)

Progress = Callable[[str, float], None]  # (message, 0..1)


def _prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def format_segment(seg: Segment) -> str:
    ts = f"[{seg.timestamp}] " if seg.timestamp else ""
    who = f"{seg.speaker}: " if seg.speaker else ""
    return f"{ts}{who}{seg.text}"


def _tokens(text: str) -> int:
    return len(text) // 4 + 1


# --- chunking ------------------------------------------------------------------

def chunk_segments(segments: list[Segment], max_tokens: int = 6000, overlap: float = 0.1) -> list[list[Segment]]:
    """Split on speaker turns (never mid-sentence). Each chunk repeats the last ~10% of the previous one."""
    chunks: list[list[Segment]] = []
    current: list[Segment] = []
    size = 0
    for seg in segments:
        t = _tokens(format_segment(seg))
        if current and size + t > max_tokens:
            chunks.append(current)
            tail: list[Segment] = []
            tail_size = 0
            for prev in reversed(current):
                pt = _tokens(format_segment(prev))
                if tail_size + pt > max_tokens * overlap:
                    break
                tail.insert(0, prev)
                tail_size += pt
            current, size = tail, tail_size
        current.append(seg)
        size += t
    if current:
        chunks.append(current)
    return chunks


# --- extraction ----------------------------------------------------------------

# Small models miss things when asked for everything at once, so each chunk gets one focused call per pass.
PASSES = [
    ("requirements", RequirementsPass, "requirements, rules and scope"),
    ("process", ProcessPass, "as-is and to-be process"),
    ("decisions", DecisionsPass, "decisions and terms"),
    ("actions", ActionsPass, "action items"),
    ("issues", IssuesPass, "open questions and risks"),
]


def extract(segments: list[Segment], llm: LLMClient, glossary: str = "",
            chunk_tokens: int | None = None, progress: Progress | None = None, source: str = "meeting") -> Extraction:
    """source: "meeting" (transcript lines with [HH:MM:SS]) or "document" (lines with [file · p.3] locations)."""
    common = _prompt("extract_common_document" if source == "document" else "extract_common")
    common = common.replace("{glossary}", glossary or "(none)")
    part = "DOCUMENT TEXT" if source == "document" else "TRANSCRIPT"
    chunks = chunk_segments(segments, chunk_tokens or config.CHUNK_TOKENS)
    total_calls = len(chunks) * len(PASSES)
    results = []
    for i, chunk in enumerate(chunks, 1):
        text = "\n".join(format_segment(s) for s in chunk)
        user = f"{part} PART {i} OF {len(chunks)}\n\n{text}"
        for j, (name, schema, label) in enumerate(PASSES):
            if progress:
                done = (i - 1) * len(PASSES) + j
                progress(f"Part {i} of {len(chunks)}: finding {label}", done / (total_calls + 1))
            system = common + "\n\n" + _prompt(f"extract_{name}")
            results.append(Extraction(**llm.generate_json(system, user, schema).model_dump()))
    merged = merge(results)
    return tidy_document(merged) if source == "document" else merged


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _label(item) -> str:
    return item if isinstance(item, str) else (getattr(item, "text", None) or getattr(item, "task", "") or getattr(item, "term", ""))


def _dedupe(items: list, threshold: float = 0.85) -> list:
    """Drop near-duplicates (from chunk overlap), keeping the first (earliest) one."""
    kept: list = []
    kept_norm: list[str] = []
    for item in items:
        n = _norm(_label(item))
        if not n or any(SequenceMatcher(None, n, k).ratio() >= threshold for k in kept_norm):
            continue
        kept.append(item)
        kept_norm.append(n)
    return kept


def merge(results: list[Extraction]) -> Extraction:
    merged = Extraction()
    for field in Extraction.model_fields:
        combined = [item for r in results for item in getattr(r, field)]
        setattr(merged, field, _dedupe(combined))
    return merged


# --- documents: requests, duplicates and who asked ------------------------------------

_ASKED = r"(?:has |have |had |is |are )?(?:asked|requested|requesting|requires?|wants?|wanted|would like|expects?|asking)"
_REQUEST = re.compile(rf"\b{_ASKED}\b", re.I)
_DECIDED = re.compile(r"\b(decided|agreed|approved|confirmed|chosen|resolved|endorsed|signed off|ratified)\b", re.I)
_WHO = re.compile(rf"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)?)\s+{_ASKED}\b")
_NOT_NAMES = {"he", "she", "they", "we", "it", "this", "that", "the", "a", "an", "all", "there", "i", "you", "users", "management"}
_NON_FUNCTIONAL = re.compile(
    r"user[- ]friendly|easy to (?:use|navigate|learn)|usab|accessib|performance|response time|fast|secur|encrypt|available|"
    r"uptime|reliab|scalab|backup|retention|within \d+ ?(?:s|sec|seconds|min|minutes|hours)|\d+(?:\.\d+)?%", re.I)
SAME_STATEMENT = 0.8


def requester_in(text: str) -> str:
    """'Quyet has asked for ...' -> 'Quyet'. '' when no person is named as the one asking."""
    for m in _WHO.finditer(text or ""):
        name = m.group(1).strip()
        if name.split()[0].lower() not in _NOT_NAMES:
            return name
    return ""


def _is_request(item) -> bool:
    evidence = f"{getattr(item, 'quote', '')} {item.text}"
    return bool(_REQUEST.search(evidence)) and not _DECIDED.search(evidence)


def _same(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    return bool(na and nb) and SequenceMatcher(None, na, nb).ratio() >= SAME_STATEMENT


def _overlap(a: str, b: str) -> float:
    """Share of words two sentences have in common (0 to 1)."""
    wa, wb = {w for w in _norm(a).split() if len(w) > 2}, {w for w in _norm(b).split() if len(w) > 2}
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def tidy_document(ext: Extraction) -> Extraction:
    """A document is written for the team that reads it, so small models file things differently from a meeting:
    - "X has asked for Y" is a request (a requirement), not a decision. Real decisions say agreed, approved ...
    - the same statement must not appear three times (as a decision, an assumption and a requirement)
    - the person who asked is not the person who does the work (an action's owner)
    Actions are never dropped: a request the team has to work on is exactly what the reader needs to see."""
    kept_decisions = []
    for d in ext.decisions:
        if _is_request(d):
            who = d.decided_by or requester_in(f"{d.quote} {d.text}")
            kind = "NFR" if _NON_FUNCTIONAL.search(d.text) else "FR"
            ext.requirements.append(ExtractedRequirement(text=d.text, timestamp=d.timestamp, quote=d.quote, kind=kind,
                                                         requested_by=who))
        else:
            kept_decisions.append(d)
    ext.decisions = kept_decisions
    ext.requirements = _dedupe(ext.requirements)
    for r in ext.requirements:
        if not r.requested_by:
            r.requested_by = requester_in(f"{r.quote} {r.text}")
    # the same sentence again as a decision, rule, assumption or scope line adds nothing
    ext.decisions = [d for d in ext.decisions if not any(_same(d.text, r.text) for r in ext.requirements)]
    firm = [r.text for r in ext.requirements] + [d.text for d in ext.decisions] + [b.text for b in ext.business_rules]
    for field in ("assumptions", "scope_in", "scope_out", "scope_deferred"):
        setattr(ext, field, [t for t in getattr(ext, field) if not any(_same(t, f) for f in firm)])
    for a in ext.actions:
        asked_by = requester_in(f"{a.quote} {a.task}")
        if asked_by and a.owner and _norm(a.owner) == _norm(asked_by):
            a.owner = ""  # Quyet asked for it; the owner is whoever does the work
        if asked_by and not any(_overlap(a.task, r.text) >= 0.5 for r in ext.requirements):
            # a request the team must act on is also something the finished system must meet: keep both
            kind = "NFR" if _NON_FUNCTIONAL.search(a.task) else "FR"
            ext.requirements.append(ExtractedRequirement(text=a.task, timestamp=a.timestamp, quote=a.quote, kind=kind,
                                                         requested_by=asked_by))
    return ext


# --- evidence check ------------------------------------------------------------

class TranscriptIndex:
    """Finds where a quote appears in the transcript (exact or close match)."""

    def __init__(self, segments: list[Segment]):
        norms = [_norm(s.text) for s in segments]
        self.stamps = [s.timestamp for s in segments]
        self.joined = " ".join(norms)
        self.starts: list[int] = []  # offset of each segment inside self.joined
        pos = 0
        for n in norms:
            self.starts.append(pos)
            pos += len(n) + 1
        # (normalised text, timestamp of first segment) for 1-3 consecutive segments
        self.windows = [(" ".join(norms[i:i + w]), self.stamps[i])
                        for i in range(len(norms)) for w in (1, 2, 3) if i + w <= len(norms)]

    def find(self, quote: str) -> tuple[bool, str | None]:
        """(found, timestamp of the segment where the quote starts)."""
        q = _norm(quote)
        if len(q) < 8:
            return False, None
        at = self.joined.find(q)
        if at >= 0:
            return True, self.stamps[bisect_right(self.starts, at) - 1]
        best_cover, best_ts = 0.0, None  # fuzzy: share of the quote's characters found in order
        for text, ts in self.windows:
            if len(text) < len(q) * 0.5:
                continue
            blocks = SequenceMatcher(None, text, q, autojunk=False).get_matching_blocks()
            cover = sum(b.size for b in blocks) / len(q)
            if cover > best_cover:
                best_cover, best_ts = cover, ts
        return (True, best_ts) if best_cover >= 0.8 else (False, None)


def _verify(item, index: TranscriptIndex) -> None:
    """Set needs_confirmation, and snap the timestamp to where the quote really is."""
    found, ts = index.find(item.quote)
    item.needs_confirmation = not found
    if found and ts:
        item.timestamp = ts


# --- register ------------------------------------------------------------------

def build_register(ext: Extraction, segments: list[Segment], project_code: str, project_name: str,
                   meeting_title: str, meeting_date: str, summary: str = "", kind: str = "meeting") -> Register:
    index = TranscriptIndex(segments)
    meeting_id = f"{meeting_date}_{project_code}"
    attendees = sorted({s.speaker for s in segments if s.speaker})

    def number(prefix: str, n: int) -> str:
        return f"{prefix}-{n:03d}"

    def track(records: list, prefix: str) -> list:
        for n, rec in enumerate(records, 1):
            rec.id = number(prefix, n)
            rec.source_meeting = meeting_id
            _verify(rec, index)
        return records

    actions = track([Action(**a.model_dump()) for a in ext.actions], "ACT")
    for a in actions:  # when it was given, the due date as a real date, and who asked for it
        a.raised_date = meeting_date
        a.due_date = resolve_due(a.due, meeting_date)
        if kind == "document":
            a.requested_by = requester_in(f"{a.quote} {a.task}")

    reqs = [Requirement(**r.model_dump()) for r in ext.requirements]
    fr = track([r for r in reqs if r.kind == "FR"], "FR")
    nfr = track([r for r in reqs if r.kind == "NFR"], "NFR")

    return Register(
        project_code=project_code,
        project_name=project_name,
        meetings=[MeetingInfo(id=meeting_id, title=meeting_title, date=meeting_date, attendees=attendees, kind=kind)],
        summary=summary,
        objectives=ext.objectives,
        scope_in=ext.scope_in,
        scope_out=ext.scope_out,
        scope_deferred=ext.scope_deferred,
        stakeholders=ext.stakeholders,
        requirements=fr + nfr,
        asis_steps=ext.asis_steps,
        tobe_steps=ext.tobe_steps,
        diagram_mermaid=mermaid_from_steps(ext.tobe_steps),
        business_rules=track([Rule(**r.model_dump()) for r in ext.business_rules], "BR"),
        data_fields=ext.data_fields,
        assumptions=ext.assumptions,
        decisions=track([Decision(**d.model_dump()) for d in ext.decisions], "DEC"),
        questions=track([Question(**q.model_dump()) for q in ext.questions], "Q"),
        actions=actions,
        risks=track([Risk(**r.model_dump()) for r in ext.risks], "RSK"),
        glossary=ext.glossary,
    )


def summarise(ext: Extraction, llm: LLMClient, source: str = "meeting") -> str:
    if not (ext.requirements or ext.decisions or ext.actions or ext.questions):
        return ""
    items = ext.model_dump(include={"objectives", "requirements", "decisions", "actions", "questions", "risks"})
    prompt = _prompt("summary_document" if source == "document" else "summary")
    return llm.generate_json(prompt, str(items), Summary).summary


def generate_register(segments: list[Segment], llm: LLMClient, project_code: str, project_name: str,
                      meeting_title: str, meeting_date: str, progress: Progress | None = None,
                      source: str = "meeting") -> Register:
    ext = extract(segments, llm, config.load_glossary(), progress=progress, source=source)
    if progress:
        progress("Writing the summary", 0.9)
    summary = summarise(ext, llm, source)
    register = build_register(ext, segments, project_code, project_name, meeting_title, meeting_date, summary, source)
    if progress:
        progress("Done", 1.0)
    return register
