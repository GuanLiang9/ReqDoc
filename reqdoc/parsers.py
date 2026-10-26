"""Transcript files (.vtt, .docx, .txt) -> list[Segment]."""
import re
from pathlib import Path

from .models import Segment

MAX_MERGED_CHARS = 600  # merge consecutive cues from one speaker up to this size


def norm_ts(value: str) -> str:
    """'0:12' -> '00:00:12'; '1:02:03.500' -> '01:02:03'. Two parts mean MM:SS."""
    parts = [int(float(p)) for p in value.strip().replace(",", ".").split(":")]
    if len(parts) == 2:
        parts = [0] + parts
    h, m, s = parts[-3:]
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_transcript(path: str | Path) -> list[Segment]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".vtt":
        segments = parse_vtt(path.read_text(encoding="utf-8-sig"))
    elif suffix == ".docx":
        segments = parse_docx(path)
    elif suffix in (".txt", ".md"):
        segments = parse_lines(path.read_text(encoding="utf-8-sig").splitlines())
    else:
        raise ValueError(f"Unsupported transcript type '{suffix}'. Use .vtt, .docx or .txt")
    if not segments:
        raise ValueError(f"No transcript text found in {path.name}")
    return segments


_CUE = re.compile(r"^(?:\d+:)?\d{2}:\d{2}[.,]\d{3}\s*-->")
_VOICE = re.compile(r"<v\s+([^>]+)>")
_TAG = re.compile(r"</?[^>]+>")


def parse_vtt(content: str) -> list[Segment]:
    segments: list[Segment] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if not _CUE.match(lines[i].strip()):
            i += 1
            continue
        start = lines[i].split("-->")[0].strip()
        i += 1
        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1
        raw = " ".join(block)
        voice = _VOICE.search(raw)
        speaker = voice.group(1).strip() if voice else ""
        text = _TAG.sub("", raw).strip()
        if text:
            segments.append(Segment(timestamp=norm_ts(start), speaker=speaker, text=text))
    return _merge_same_speaker(segments)


def _merge_same_speaker(segments: list[Segment]) -> list[Segment]:
    merged: list[Segment] = []
    for seg in segments:
        prev = merged[-1] if merged else None
        if prev and prev.speaker == seg.speaker and len(prev.text) + len(seg.text) < MAX_MERGED_CHARS:
            prev.text += " " + seg.text
        else:
            merged.append(seg.model_copy())
    return merged


_LINE = re.compile(
    r"^\[?(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–]?\s*(?:(?P<sp>[^:\n]{1,40}):\s+)?(?P<text>.*)$"
)
_SPEAKER_ONLY = re.compile(r"^(?P<sp>[^:\n]{1,40}):\s+(?P<text>.+)$")


def parse_lines(lines: list[str]) -> list[Segment]:
    """Plain text: '[00:12:30] Alice: text', '00:12 Alice: text', 'Alice: text' or bare lines."""
    segments = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = _LINE.match(line)
        if m and m.group("text").strip():
            segments.append(Segment(timestamp=norm_ts(m.group("ts")),
                                    speaker=(m.group("sp") or "").strip(),
                                    text=m.group("text").strip()))
            continue
        m = _SPEAKER_ONLY.match(line)
        if m:
            segments.append(Segment(speaker=m.group("sp").strip(), text=m.group("text").strip()))
        else:
            segments.append(Segment(text=line))
    return segments


_HEAD_A = re.compile(r"^(?P<sp>.+?)\s+(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)$")  # 'Alice Tan  0:12'
_HEAD_B = re.compile(r"^(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<sp>.+)$")  # '0:12  Alice Tan'


def parse_docx(path: Path) -> list[Segment]:
    """Teams .docx transcripts: a 'speaker + time' header paragraph followed by text paragraphs."""
    from docx import Document

    paragraphs = [p.text.strip() for p in Document(str(path)).paragraphs if p.text.strip()]
    segments: list[Segment] = []
    current: Segment | None = None
    for para in paragraphs:
        m = _HEAD_A.match(para) or _HEAD_B.match(para)
        if m and len(para) < 80:
            current = Segment(timestamp=norm_ts(m.group("ts")), speaker=m.group("sp").strip(), text="")
            segments.append(current)
        elif current is not None:
            current.text = f"{current.text} {para}".strip()
    segments = [s for s in segments if s.text]
    return segments or parse_lines(paragraphs)  # no headers found: treat as plain text
