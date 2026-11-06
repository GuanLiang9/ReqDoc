"""Supporting documents (.docx, .pptx, .pdf, .xlsx, .txt, .md) -> list[Segment].

Each segment's `timestamp` holds a location label instead of a time, for example "RFP · p.3",
"Kickoff deck · slide 4", "Fields · Sheet1 row 12" or "Scope · Security" (the nearest Word heading).
The rest of the pipeline treats it like a timestamp: the evidence check snaps every item to the
label of the line its quote came from. Only text is read; pictures and scanned pages are not.
"""
import re
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from .models import Segment

DOC_EXTENSIONS = {".docx", ".pptx", ".pdf", ".xlsx", ".txt", ".md"}
OLD_FORMATS = {".doc": ".docx", ".ppt": ".pptx", ".xls": ".xlsx"}
MAX_FILES = 10
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_CHARS = 400_000  # about 200 pages; more than that takes hours on a CPU-only laptop
MAX_ROWS = 3_000  # per spreadsheet
PARA_CHARS = 450  # PDF text is regrouped into paragraphs of about this size

Progress = Callable[[str, float], None]


def short_name(filename: str) -> str:
    stem = re.sub(r"[_\s]+", " ", Path(filename).stem).strip() or "Document"
    return stem if len(stem) <= 24 else stem[:23].rstrip() + "…"


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _clean(value)


def _rows_to_text(rows: list[list[str]]) -> list[str]:
    """Table rows -> 'Header: value; Header: value' lines (the first row gives the headers)."""
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return []
    if len(rows) == 1:
        return [" | ".join(c for c in rows[0] if c)]
    headers = [h or f"Column {i + 1}" for i, h in enumerate(rows[0])]
    out = []
    for r in rows[1:]:
        pairs = [f"{headers[i] if i < len(headers) else f'Column {i + 1}'}: {v}" for i, v in enumerate(r) if v]
        if pairs:
            out.append("; ".join(pairs))
    return out


def _dedupe_merged(cells: list[str]) -> list[str]:
    """Word and PowerPoint repeat the text of merged cells; keep it once."""
    out: list[str] = []
    for c in cells:
        if not out or c != out[-1]:
            out.append(c)
    return out


# --- readers ---------------------------------------------------------------------

def read_docx(path: Path, name: str) -> list[Segment]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    out: list[Segment] = []
    section, para_no = "", 0
    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            text = _clean(block.text)
            if not text:
                continue
            para_no += 1
            style = (block.style.name if block.style is not None else "") or ""
            if style.startswith(("Heading", "Title")):
                section = text if len(text) <= 40 else text[:39].rstrip() + "…"
            out.append(Segment(timestamp=f"{name} · {section or f'para {para_no}'}", text=text))
        elif isinstance(block, Table):
            rows = [_dedupe_merged([_clean(c.text) for c in row.cells]) for row in block.rows]
            for line in _rows_to_text(rows):
                out.append(Segment(timestamp=f"{name} · {section or 'table'}", text=line))
    return out


def _shape_texts(shape) -> list[str]:
    if shape.shape_type == 6:  # a group: look inside
        return [t for s in shape.shapes for t in _shape_texts(s)]
    texts: list[str] = []
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        texts += [_clean(p.text) for p in shape.text_frame.paragraphs if _clean(p.text)]
    if getattr(shape, "has_table", False) and shape.has_table:
        rows = [_dedupe_merged([_clean(c.text) for c in row.cells]) for row in shape.table.rows]
        texts += _rows_to_text(rows)
    return texts


def read_pptx(path: Path, name: str) -> list[Segment]:
    from pptx import Presentation

    out: list[Segment] = []
    for n, slide in enumerate(Presentation(str(path)).slides, 1):
        label = f"{name} · slide {n}"
        for shape in slide.shapes:
            out += [Segment(timestamp=label, text=t) for t in _shape_texts(shape)]
        if slide.has_notes_slide:
            notes = _clean(slide.notes_slide.notes_text_frame.text)
            if notes:
                out.append(Segment(timestamp=label, text=f"Speaker notes: {notes}"))
    return out


def _paragraphs(page_text: str) -> list[str]:
    """PDF text comes as broken lines: join them (and hyphenated words), then regroup into paragraphs."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", page_text or "")
    blocks = [_clean(b) for b in re.split(r"\n\s*\n", text) if _clean(b)]
    out: list[str] = []
    for block in blocks:
        current = ""
        for sentence in re.split(r"(?<=[.!?;:])\s+", block):
            if current and len(current) + len(sentence) > PARA_CHARS:
                out.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            out.append(current)
    return out


def read_pdf(path: Path, name: str) -> list[Segment]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError(f"{path.name} is password-protected. Remove the password and upload it again.")
    out: list[Segment] = []
    for n, page in enumerate(reader.pages, 1):
        out += [Segment(timestamp=f"{name} · p.{n}", text=p) for p in _paragraphs(page.extract_text() or "")]
    if not out and len(reader.pages):
        raise ValueError(f"{path.name} has no readable text. It looks like a scanned image, and this version "
                         "cannot read scans (no OCR yet). Upload the original Word or PowerPoint file if you have it.")
    return out


def read_xlsx(path: Path, name: str, warnings: list[str]) -> list[Segment]:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    out: list[Segment] = []
    rows_read = 0
    try:
        for ws in wb.worksheets:
            headers: list[str] | None = None
            for r, row in enumerate(ws.iter_rows(values_only=True), 1):
                cells = [_cell(v) for v in row]
                if not any(cells):
                    continue
                if headers is None:
                    headers = [c or f"Column {i + 1}" for i, c in enumerate(cells)]
                    out.append(Segment(timestamp=f"{name} · {ws.title} row {r}", text="Columns: " + ", ".join(h for h in headers if h)))
                    continue
                if rows_read >= MAX_ROWS:
                    warnings.append(f"Only the first {MAX_ROWS:,} rows of {path.name} were read.")
                    return out
                pairs = [f"{headers[i] if i < len(headers) else f'Column {i + 1}'}: {v}" for i, v in enumerate(cells) if v]
                out.append(Segment(timestamp=f"{name} · {ws.title} row {r}", text="; ".join(pairs)))
                rows_read += 1
    finally:
        wb.close()
    return out


def read_text(path: Path, name: str) -> list[Segment]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    return [Segment(timestamp=f"{name} · line {n}", text=_clean(l)) for n, l in enumerate(lines, 1) if _clean(l)]


# --- entry point -----------------------------------------------------------------

def check_filename(filename: str) -> None:
    """Raise ValueError with a helpful message when this file type can't be read."""
    ext = Path(filename).suffix.lower()
    if ext in OLD_FORMATS:
        raise ValueError(f"{filename} is an old Office format. Open it and save it as {OLD_FORMATS[ext]}, then upload that.")
    if ext not in DOC_EXTENSIONS:
        raise ValueError(f"{filename}: '{ext or 'this'}' files are not supported. Use {', '.join(sorted(DOC_EXTENSIONS))}.")


def read_one(path: Path, warnings: list[str], display_name: str | None = None) -> list[Segment]:
    check_filename(path.name)
    name = short_name(display_name or path.name)
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            segs = read_docx(path, name)
        elif ext == ".pptx":
            segs = read_pptx(path, name)
        elif ext == ".pdf":
            segs = read_pdf(path, name)
        elif ext == ".xlsx":
            segs = read_xlsx(path, name, warnings)
        else:
            segs = read_text(path, name)
    except ValueError:
        raise
    except Exception as e:  # damaged, password-protected (Office files become non-zip) or not really that type
        raise ValueError(f"{path.name} could not be read. It may be damaged or password-protected ({type(e).__name__}).") from e
    if not segs:
        warnings.append(f"No text found in {path.name}.")
    return segs


def read_documents(paths: list[Path], progress: Progress | None = None,
                   display_names: list[str] | None = None) -> tuple[list[Segment], list[str]]:
    """All files of one upload, in order. Returns (segments, warnings for the person)."""
    segments: list[Segment] = []
    warnings: list[str] = []
    for i, path in enumerate(paths):
        if progress:
            progress(f"Reading {Path(display_names[i] if display_names else path.name).name}", i / max(len(paths), 1))
        segments += read_one(Path(path), warnings, display_names[i] if display_names else None)
    if not segments:
        raise ValueError("No text was found in these documents.")
    chars = sum(len(s.text) for s in segments)
    if chars > MAX_CHARS:
        raise ValueError(f"These documents hold about {chars // 2000} pages of text, more than this computer can read in one go "
                         f"(about {MAX_CHARS // 2000}). Upload them in smaller groups.")
    return segments, warnings


def segments_to_located_text(segments: list[Segment]) -> str:
    """Saved next to the project so the evidence view can show the document text; parse_located_lines reads it back."""
    return "\n".join(f"[{s.timestamp}] {s.text}" for s in segments) + "\n"
