"""Register -> Markdown and Word. Both are built from the same section data so they never differ."""
import io
import re
from datetime import datetime, timedelta, timezone

from . import config, flowchart, word_fields
from .dates import pretty, today_sgt
from .models import Register

EMPTY = "None recorded yet"
WARN = "⚠ to confirm"
TEMPLATE = config.ROOT / "templates" / "requirement_template.docx"
LOGO = config.ROOT / "reqdoc" / "assets" / "wohhup_logo.png"

# Woh Hup brand colours (sampled from the logo) plus neutrals
GOLD = "B68D29"
GOLD_DEEP = "7A5A12"
GOLD_TINT = "F8F0DC"
GREY = "54555B"
INK = "231F20"
CHARCOAL = "2B2B2E"
HAIRLINE = "DDD9CE"
BAND = "FAF7EF"
GREEN = "2E6B3A"
GREEN_TINT = "E7EEE3"
AMBER = "9A5B00"

# A block is one of:
#   ("empty",) ("text", str) ("sub", str) ("bullets", [str]) ("numbered", [str])
#   ("table", [headers], [[cells]]) ("diagram", mermaid_text, [steps])
Block = tuple


def _flag(item) -> str:
    return f" {WARN}" if item.needs_confirmation else ""


def _ts(item) -> str:
    return f"[{item.timestamp}]" if item.timestamp else ""


def _bullets(items: list[str]) -> Block:
    return ("bullets", items) if items else ("empty",)


def _numbered(items: list[str]) -> Block:
    return ("numbered", items) if items else ("empty",)


def _table(headers: list[str], rows: list[list[str]]) -> Block:
    return ("table", headers, rows) if rows else ("empty",)


def _live(items):
    """Withdrawn items stay in the change log but are not part of what was agreed."""
    return [i for i in items if i.status != "Withdrawn"]


def _meeting_names(reg: Register) -> dict[str, str]:
    """meeting id -> '30 Oct 2026 · Kickoff'."""
    return {m.id: f"{pretty(m.date)} · {m.title}" for m in reg.meetings}


def _overview(reg: Register) -> str:
    dates = sorted(m.date for m in reg.meetings if m.date)
    if not dates:
        return f"This document sets out what has been agreed to build for {reg.project_name or reg.project_code}."
    span = pretty(dates[0]) if dates[0] == dates[-1] else f"{pretty(dates[0])} and {pretty(dates[-1])}"
    n = len(dates)
    return (f"This document sets out what has been agreed to build for {reg.project_name or reg.project_code}. "
            f"It reflects {n} meeting{'s' if n != 1 else ''} held {'on' if n == 1 else 'between'} {span}. "
            "Meeting minutes and the action tracker are kept in a separate document.")


def spec_sections(reg: Register) -> list[tuple[str, list[Block]]]:
    """The requirement specification: only what is to be built and how. Meeting minutes live in notes_sections."""
    fr = _live([r for r in reg.requirements if r.kind == "FR"])
    nfr = _live([r for r in reg.requirements if r.kind == "NFR"])
    req_headers = ["ID", "Requirement", "Priority", "Status"]

    def req_rows(items):
        return [[r.id, r.text + _flag(r), r.priority, r.status] for r in items]

    when = _meeting_dates(reg)
    last = max((m.date for m in reg.meetings if m.date), default="")
    process: list[Block] = []
    if flowchart.clean_steps(reg.tobe_steps):
        process = [_numbered(reg.tobe_steps), ("diagram", reg.diagram_mermaid, reg.tobe_steps)]
    else:
        process = [("empty",)]

    return [
        ("Document control", [_table(["Field", "Value"], [
            ["Project", f"{reg.project_code} {reg.project_name}".strip()],
            ["Version", reg.version],
            ["Status", reg.doc_status],
            ["Reviewer", reg.reviewer or "TBC"],
            ["Last updated", pretty(last) if last else ""],
        ])]),
        ("Overview and objectives", [("text", _overview(reg)), _bullets(reg.objectives)]),
        ("Scope", [("sub", "In scope"), _bullets(reg.scope_in), ("sub", "Out of scope"), _bullets(reg.scope_out),
                   ("sub", "Deferred to a later phase"), _bullets(reg.scope_deferred)]),
        ("Users and stakeholders", [_bullets(reg.stakeholders)]),
        ("Functional requirements", [_table(req_headers, req_rows(fr))]),
        ("Non-functional requirements", [_table(req_headers, req_rows(nfr))]),
        ("Business rules", [_table(["ID", "Rule", "Status"], [[r.id, r.text + _flag(r), r.status] for r in _live(reg.business_rules)])]),
        ("Process and workflow", process),
        ("Data and fields", [_bullets(reg.data_fields)]),
        ("Assumptions and constraints", [_bullets(reg.assumptions)]),
        ("Agreed decisions", [_table(["ID", "Decision", "Date agreed"],
                                     [[d.id, d.text + _flag(d), pretty(when.get(d.source_meeting, ""))] for d in _live(reg.decisions)])]),
        ("Risks", [_table(["ID", "Risk", "Status"], [[r.id, r.text + _flag(r), r.status] for r in _live(reg.risks)])]),
        ("Glossary", [_table(["Term", "Meaning"], [[g.term, g.meaning] for g in reg.glossary])]),
    ]


def _meeting_dates(reg: Register) -> dict[str, str]:
    return {m.id: m.date for m in reg.meetings}


def _action_sort_key(a) -> tuple:
    done = a.status in ("Done", "Withdrawn")
    return (done, a.due_date or "9999-99-99", a.id)


def is_overdue(a, today: str) -> bool:
    return a.status == "Open" and bool(a.due_date) and a.due_date < today


def notes_sections(reg: Register, summaries: dict[str, str] | None = None) -> list[tuple[str, list[Block]]]:
    """Meeting notes and the action tracker: what was asked, by whom, when, and what is still open."""
    summaries = summaries or {}
    names = _meeting_names(reg)
    today = today_sgt()

    def due_cell(a) -> str:
        if a.due_date:
            said = f"\n“{a.due}”" if a.due and a.due.strip().lower() != a.due_date else ""
            return pretty(a.due_date) + said
        return a.due

    def closed_cell(a) -> str:
        if not a.closed_date:
            return ""
        return pretty(a.closed_date) + (f"\n{names[a.closed_meeting].split(' · ', 1)[1]}" if a.closed_meeting in names else "")

    actions = sorted(reg.actions, key=_action_sort_key)
    tracker = _table(["ID", "Action", "Owner", "Raised", "Due", "Status", "Closed"], [
        [a.id, a.task + _flag(a), a.owner, names.get(a.source_meeting, pretty(a.raised_date)).replace(" · ", "\n"),
         due_cell(a), "Overdue" if is_overdue(a, today) else a.status, closed_cell(a)]
        for a in actions])
    updates = [f"{a.id}: {u}" for a in actions for u in a.updates]
    action_blocks = [tracker] + ([("sub", "Changes since first raised"), _bullets(updates)] if updates else [])

    questions = _table(["ID", "Question", "Owner", "Raised", "Status", "Answer"], [
        [q.id, q.text + _flag(q), q.owner, names.get(q.source_meeting, "").replace(" · ", "\n"), q.status, q.answer]
        for q in reg.questions])

    meeting_blocks: list[Block] = []
    for m in sorted(reg.meetings, key=lambda x: x.date):
        meeting_blocks.append(("sub", f"{pretty(m.date)} · {m.title}"))
        if m.attendees:
            meeting_blocks.append(("text", "Attendees: " + ", ".join(m.attendees)))
        text = summaries.get(m.id) or (reg.summary if m is reg.meetings[-1] else "")
        meeting_blocks.append(("text", text) if text else ("empty",))
    return [
        ("Action tracker", action_blocks),
        ("Open questions", [questions]),
        ("Meetings", meeting_blocks or [("empty",)]),
        ("Current process (as-is)", [_numbered(reg.asis_steps)]),
    ]


def status_line(reg: Register) -> str:
    return "DRAFT — AI-generated, pending human review" if reg.doc_status == "DRAFT" else f"APPROVED by {reg.reviewer or 'reviewer'}"


def doc_title(reg: Register) -> str:
    return f"{reg.project_code} {reg.project_name} — Requirements".replace("  ", " ")


def appendix_lines(reg: Register) -> tuple[list[str], list[str]]:
    meetings = [f"{m.date} — {m.title}" + (f" ({m.source_file})" if m.source_file else "") for m in reg.meetings]
    return meetings, reg.change_log


# --- Markdown ------------------------------------------------------------------

def _md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip() or "—"


def _md_block(block: Block) -> str:
    kind = block[0]
    if kind == "empty":
        return f"_{EMPTY}_"
    if kind == "text":
        return block[1]
    if kind == "sub":
        return f"**{block[1]}**"
    if kind == "bullets":
        return "\n".join(f"- {i}" for i in block[1])
    if kind == "numbered":
        return "\n".join(f"{n}. {i}" for n, i in enumerate(block[1], 1))
    if kind == "diagram":
        return f"```mermaid\n{block[1]}\n```"
    headers, rows = block[1], block[2]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(_md_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render_markdown(reg: Register) -> str:
    out = [f"# {doc_title(reg)}", "", f"**Status: {status_line(reg)}**", ""]
    for n, (heading, blocks) in enumerate(spec_sections(reg), 1):
        out += [f"## {n}. {heading}", ""]
        for b in blocks:
            out += [_md_block(b), ""]
    meetings, log = appendix_lines(reg)
    out += ["## Appendix", "", "**Source meetings**", ""]
    out += [f"- {m}" for m in meetings] or ["—"]
    if log:
        out += ["", "**Change log**", ""] + [f"- {line}" for line in log]
    return "\n".join(out) + "\n"


# --- Word ----------------------------------------------------------------------

_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SGT = timezone(timedelta(hours=8))
_PAGE_W_CM = 17.0  # A4 with 2 cm margins

# column widths in cm for known headers; the remaining width is shared by the text columns
_COL_CM = {"ID": 1.6, "Priority": 1.8, "Status": 1.9, "Owner": 2.1, "Raised": 2.6, "Due": 2.4, "Closed": 2.4,
           "Date agreed": 2.5, "Field": 3.5, "Term": 4.0}

OVERDUE = "B3261E"
_STATUS_COLOR = {"open": AMBER, "proposed": AMBER, "done": GREEN, "answered": GREEN, "confirmed": GREEN,
                 "approved": GREEN, "agreed": GREEN, "withdrawn": GREY, "overdue": OVERDUE}


def _clean(text: str) -> str:
    return _BAD_XML.sub("", text or "")


def _rgb(hex_: str):
    from docx.shared import RGBColor
    return RGBColor.from_string(hex_)


def _el(tag: str, **attrs):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    el = OxmlElement(tag)
    for k, v in attrs.items():
        el.set(qn(f"w:{k}"), str(v))
    return el


_PPR_AFTER_BDR = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                  "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
                  "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                  "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
                  "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")
_RPR_AFTER_SPACING = ("w:w", "w:kern", "w:position", "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr",
                      "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang", "w:eastAsianLayout",
                      "w:specVanish", "w:oMath")


def _border(ppr, side: str, color: str, size: int = 8, space: int = 4) -> None:
    """Add a single line on one side of a paragraph (ppr = paragraph or style pPr element)."""
    bdr = ppr.find(_qn("w:pBdr"))
    if bdr is None:
        bdr = _el("w:pBdr")
        ppr.insert_element_before(bdr, *_PPR_AFTER_BDR)
    bdr.append(_el(f"w:{side}", val="single", sz=size, space=space, color=color))


def _qn(tag: str):
    from docx.oxml.ns import qn
    return qn(tag)


def _letter_space(run, twentieths: int) -> None:
    rpr = run._r.get_or_add_rPr()
    rpr.insert_element_before(_el("w:spacing", val=twentieths), *_RPR_AFTER_SPACING)


def _run_shade(run, fill: str) -> None:
    run._r.get_or_add_rPr().append(_el("w:shd", val="clear", color="auto", fill=fill))


def _font(style_or_run, name: str | None = None, size: float | None = None, bold: bool | None = None,
          color: str | None = None) -> None:
    from docx.shared import Pt
    f = style_or_run.font
    if name:
        f.name = name
        rpr = (style_or_run.element if hasattr(style_or_run, "element") else style_or_run._r).get_or_add_rPr()
        fonts = rpr.find(_qn("w:rFonts"))
        if fonts is not None:  # drop theme fonts, which would override the name
            for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
                key = _qn(f"w:{attr}")
                if key in fonts.attrib:
                    del fonts.attrib[key]
            fonts.set(_qn("w:eastAsia"), name)
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if color:
        f.color.rgb = _rgb(color)


def _add_field(paragraph, instr: str, placeholder: str = "1", size: float | None = None, color: str | None = None) -> None:
    """A Word field (PAGE, NUMPAGES ...). Word fills in the real value."""
    from docx.shared import Pt

    def part(child):
        run = paragraph.add_run()
        if size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = _rgb(color)
        run._r.append(child)
        return run

    part(_el("w:fldChar", fldCharType="begin"))
    instr_el = _el("w:instrText")
    instr_el.set(_qn("xml:space"), "preserve")
    instr_el.text = f" {instr} "
    part(instr_el)
    part(_el("w:fldChar", fldCharType="separate"))
    run = paragraph.add_run(placeholder)
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = _rgb(color)
    part(_el("w:fldChar", fldCharType="end"))


def _shade_cell(cell, fill: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    tcpr.insert_element_before(_el("w:shd", val="clear", color="auto", fill=fill),
                               "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark")


def _table_frame(table, hairline: bool = True) -> None:
    """Horizontal hairlines only, comfortable padding, fixed layout."""
    table.autofit = False
    tblpr = table._tbl.tblPr
    borders = _el("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        horizontal = side in ("top", "bottom", "insideH") and hairline
        borders.append(_el(f"w:{side}", val="single" if horizontal else "nil", sz=4, space=0, color=HAIRLINE))
    tblpr.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")
    margins = _el("w:tblCellMar")
    for side, w in (("top", 70), ("left", 110), ("bottom", 70), ("right", 110)):
        margins.append(_el(f"w:{side}", w=w, type="dxa"))
    tblpr.insert_element_before(margins, "w:tblLook")


def _widths_cm(headers: list[str]) -> list[float]:
    fixed = sum(_COL_CM.get(h, 0) for h in headers)
    flexible = [h for h in headers if h not in _COL_CM]
    share = max(3.0, (_PAGE_W_CM - fixed) / max(1, len(flexible)))
    return [_COL_CM.get(h, share) for h in headers]


def _set_cell_text(cell, text: str, header: str, size: float = 9) -> None:
    """Cell text with the 'to confirm' flag in amber, statuses coloured, empty values greyed."""
    from docx.shared import Pt
    text = _clean(text)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    if not text.strip():
        r = p.add_run("—")
        r.font.size = Pt(size)
        r.font.color.rgb = _rgb(GREY)
        return
    flagged = text.endswith(WARN)
    body = text[: -len(WARN)].rstrip() if flagged else text
    r = p.add_run(body)
    r.font.size = Pt(size)
    if header == "ID":
        r.bold = True
    elif header == "Status" and body.lower() in _STATUS_COLOR:
        r.bold = True
        r.font.color.rgb = _rgb(_STATUS_COLOR[body.lower()])
    elif header == "Priority" and body.lower() in ("must", "high"):
        r.bold = True
    elif header in ("Raised", "Due", "Closed", "Date agreed"):
        r.font.color.rgb = _rgb(GREY)
    if flagged:
        w = p.add_run(f" {WARN}")
        w.font.size = Pt(size - 0.5)
        w.bold = True
        w.font.color.rgb = _rgb(AMBER)


def _no_split(row) -> None:
    row._tr.get_or_add_trPr().append(_el("w:cantSplit"))


def _repeat_header(row) -> None:
    row._tr.get_or_add_trPr().append(_el("w:tblHeader"))


def _add_table(doc, headers: list[str], rows: list[list[str]], key_value: bool = False) -> None:
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    from docx.shared import Cm, Pt

    widths = _widths_cm(headers)
    table = doc.add_table(rows=0 if key_value else 1, cols=len(headers))
    _table_frame(table)
    if not key_value:
        head = table.rows[0]
        _repeat_header(head)
        _no_split(head)
        for cell, h, w in zip(head.cells, headers, widths):
            cell.width = Cm(w)
            _shade_cell(cell, CHARCOAL)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True  # never leave the header row alone at the bottom of a page
            r = p.add_run(_clean(h).upper())
            r.bold = True
            r.font.size = Pt(8)
            r.font.color.rgb = _rgb("FFFFFF")
            _letter_space(r, 12)
    for n, row in enumerate(rows):
        tr = table.add_row()
        _no_split(tr)
        for cell, header, value, w in zip(tr.cells, headers, row, widths):
            cell.width = Cm(w)
            if key_value and header == "Field":
                _shade_cell(cell, GOLD_TINT)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(_clean(value))
                r.bold = True
                r.font.size = Pt(9)
                r.font.color.rgb = _rgb(GOLD_DEEP)
                continue
            if not key_value and n % 2 == 1:
                _shade_cell(cell, BAND)
            _set_cell_text(cell, value, header)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def _setup_styles(doc) -> None:
    from docx.shared import Pt

    normal = doc.styles["Normal"]
    _font(normal, "Calibri", 10.5, color=INK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12

    h1 = doc.styles["Heading 1"]
    _font(h1, "Calibri", 17, True, INK)
    h1.paragraph_format.space_before = Pt(20)
    h1.paragraph_format.space_after = Pt(8)
    h1.paragraph_format.keep_with_next = True
    _border(h1.element.get_or_add_pPr(), "bottom", GOLD, size=12, space=3)

    h2 = doc.styles["Heading 2"]
    _font(h2, "Calibri", 11.5, True, GOLD_DEEP)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(3)
    h2.paragraph_format.keep_with_next = True

    for name in ("List Bullet",):
        if name in {s.name for s in doc.styles}:
            doc.styles[name].paragraph_format.space_after = Pt(3)


def _setup_page(doc, reg: Register) -> None:
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2.0)
    sec.header_distance = sec.footer_distance = Cm(1.0)
    sec.different_first_page_header_footer = True  # the cover page stays clean

    # header: logo on the left, document title on the right, hairline below
    header = sec.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    table = header.add_table(1, 2, Cm(_PAGE_W_CM))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _table_frame(table, hairline=False)
    left, right = table.rows[0].cells
    left.width, right.width = Cm(6), Cm(_PAGE_W_CM - 6)
    lp = left.paragraphs[0]
    lp.paragraph_format.space_after = Pt(0)
    if LOGO.exists():
        lp.add_run().add_picture(str(LOGO), height=Cm(0.95))
    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rp.paragraph_format.space_after = Pt(0)
    r = rp.add_run(_clean(f"{reg.project_code} {reg.project_name}".strip()))
    r.font.size = Pt(8.5)
    r.font.color.rgb = _rgb(GREY)
    _border(hp._p.get_or_add_pPr(), "bottom", GOLD, size=8, space=1)
    hp.paragraph_format.space_after = Pt(0)
    hp.paragraph_format.line_spacing = Pt(2)
    header._element.remove(hp._p)
    header._element.append(hp._p)  # the rule goes under the logo row

    # footer: version and status, confidentiality, page x of y
    foot = sec.footer
    foot.is_linked_to_previous = False
    fp = foot.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _border(fp._p.get_or_add_pPr(), "top", HAIRLINE, size=4, space=6)
    r = fp.add_run(_clean(f"v{reg.version}  ·  {reg.doc_status}  ·  Confidential, for internal use  ·  Page "))
    r.font.size = Pt(8)
    r.font.color.rgb = _rgb(GREY)
    _add_field(fp, "PAGE", "1", size=8, color=GREY)
    r = fp.add_run(" of ")
    r.font.size = Pt(8)
    r.font.color.rgb = _rgb(GREY)
    _add_field(fp, "NUMPAGES", "1", size=8, color=GREY)


def _cover(doc, reg: Register, label: str = "REQUIREMENT SPECIFICATION") -> None:
    from docx.enum.text import WD_BREAK
    from docx.shared import Cm, Pt

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(70)
    if LOGO.exists():
        p.add_run().add_picture(str(LOGO), width=Cm(7.2))

    rule = doc.add_paragraph()
    _border(rule._p.get_or_add_pPr(), "top", GOLD, size=24, space=1)
    rule.paragraph_format.space_after = Pt(10)

    eyebrow = doc.add_paragraph()
    r = eyebrow.add_run(label)
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = _rgb(GREY)
    _letter_space(r, 50)
    eyebrow.paragraph_format.space_after = Pt(6)

    title = doc.add_paragraph()
    r = title.add_run(_clean(reg.project_name or reg.project_code))
    r.bold = True
    r.font.size = Pt(30)
    r.font.color.rgb = _rgb(INK)
    title.paragraph_format.space_after = Pt(4)
    title.paragraph_format.line_spacing = 1.0

    code = doc.add_paragraph()
    r = code.add_run(_clean(reg.project_code))
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = _rgb(GOLD)
    code.paragraph_format.space_after = Pt(28)

    draft = reg.doc_status == "DRAFT"
    pill = doc.add_paragraph()
    r = pill.add_run(f"  {_clean(status_line(reg)).upper()}  ")
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = _rgb(GOLD_DEEP if draft else GREEN)
    _letter_space(r, 20)
    _run_shade(r, GOLD_TINT if draft else GREEN_TINT)
    pill.paragraph_format.space_after = Pt(18)

    meeting = reg.meetings[-1] if reg.meetings else None
    generated = datetime.now(_SGT).strftime("%d %b %Y, %H:%M") + " (SGT)"
    for label, value in (("Version", reg.version), ("Latest meeting", f"{meeting.title} ({meeting.date})" if meeting else "—"),
                         ("Reviewer", reg.reviewer or "To be confirmed"), ("Generated", generated)):
        line = doc.add_paragraph()
        line.paragraph_format.space_after = Pt(3)
        a = line.add_run(f"{label}   ")
        a.font.size = Pt(9.5)
        a.font.color.rgb = _rgb(GREY)
        b = line.add_run(_clean(str(value)))
        b.font.size = Pt(9.5)
        b.bold = True
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _contents(doc, headings: list[str]) -> None:
    """A real Word table of contents. The entries below are placeholders; Word replaces them with
    page numbers when it updates fields (it asks once when the file is opened)."""
    from docx.enum.text import WD_BREAK
    from docx.shared import Pt

    title = doc.add_paragraph()
    r = title.add_run("Contents")
    r.bold = True
    r.font.size = Pt(20)
    _border(title._p.get_or_add_pPr(), "bottom", GOLD, size=12, space=3)
    title.paragraph_format.space_after = Pt(12)

    first = doc.add_paragraph()
    first.paragraph_format.space_after = Pt(4)
    for child in (_el("w:fldChar", fldCharType="begin"),):
        first.add_run()._r.append(child)
    instr = _el("w:instrText")
    instr.set(_qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    first.add_run()._r.append(instr)
    first.add_run()._r.append(_el("w:fldChar", fldCharType="separate"))
    last = first
    for n, text in enumerate(headings):
        p = first if n == 0 else doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(_clean(text))
        run.font.size = Pt(11)
        last = p
    last.add_run()._r.append(_el("w:fldChar", fldCharType="end"))
    note = doc.add_paragraph()
    r = note.add_run("If page numbers are missing, click in the list and press F9 (Update field).")
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = _rgb(GREY)
    note.add_run().add_break(WD_BREAK.PAGE)


def _numbered_steps(doc, items: list[str]) -> None:
    """Numbered steps that restart at 1 in every list (Word's List Number style would carry on counting)."""
    from docx.shared import Cm, Pt

    for n, item in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(0.9), Cm(-0.9)
        pf.space_after = Pt(3)
        pf.tab_stops.add_tab_stop(Cm(0.9))
        num = p.add_run(f"{n}.\t")
        num.bold = True
        num.font.color.rgb = _rgb(GOLD)
        p.add_run(_clean(item))


def _diagram(doc, steps: list[str]) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    for png in flowchart.to_png_parts(steps, cols=3):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = False
        p.add_run().add_picture(io.BytesIO(png), width=Cm(_PAGE_W_CM))
    cap = doc.add_paragraph()
    r = cap.add_run("Proposed workflow, drawn from the to-be process steps. Numbers match the steps in the previous section.")
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = _rgb(GREY)


DOC_KINDS = {
    "spec": ("REQUIREMENT SPECIFICATION", "Requirement specification"),
    "notes": ("MEETING NOTES & ACTION TRACKER", "Meeting notes and action tracker"),
}


def render_docx(reg: Register, kind: str = "spec", summaries: dict[str, str] | None = None) -> bytes:
    """kind 'spec': the lean requirement specification. kind 'notes': meeting notes and the action tracker.
    The table of contents is filled in by Word when it is available (REQDOC_WORD_TOC), otherwise Word is
    asked to fill it in when the file is opened."""
    raw = _build_docx(reg, kind, summaries, ask_word_to_update=not config.WORD_TOC)
    if config.WORD_TOC:
        refreshed = word_fields.refresh_fields(raw)
        return refreshed if refreshed is not None else _build_docx(reg, kind, summaries, ask_word_to_update=True)
    return raw


def _build_docx(reg: Register, kind: str, summaries: dict[str, str] | None, ask_word_to_update: bool) -> bytes:
    from docx import Document

    cover_label, subject = DOC_KINDS[kind]
    doc = Document(str(TEMPLATE)) if TEMPLATE.exists() else Document()
    _setup_styles(doc)
    _setup_page(doc, reg)
    cp = doc.core_properties
    cp.title, cp.author, cp.subject = _clean(doc_title(reg)), "ReqDoc AI", subject

    secs = spec_sections(reg) if kind == "spec" else notes_sections(reg, summaries)
    _cover(doc, reg, cover_label)
    appendix = kind == "spec"
    _contents(doc, [f"{n}. {h}" for n, (h, _) in enumerate(secs, 1)] + (["Appendix"] if appendix else []))

    def add_empty():
        p = doc.add_paragraph()
        r = p.add_run(EMPTY)
        r.italic = True
        r.font.color.rgb = _rgb(GREY)

    for n, (heading, blocks) in enumerate(secs, 1):
        doc.add_heading(_clean(f"{n}. {heading}"), level=1)
        for b in blocks:
            kind = b[0]
            if kind == "empty":
                add_empty()
            elif kind == "text":
                doc.add_paragraph(_clean(b[1]))
            elif kind == "sub":
                doc.add_heading(_clean(b[1]), level=2)
            elif kind == "bullets":
                for i in b[1]:
                    doc.add_paragraph(_clean(i), style="List Bullet")
            elif kind == "numbered":
                _numbered_steps(doc, b[1])
            elif kind == "diagram":
                _diagram(doc, b[2])
            else:
                _add_table(doc, b[1], b[2], key_value=b[1] == ["Field", "Value"])

    if appendix:
        meetings, log = appendix_lines(reg)
        doc.add_heading("Appendix", level=1)
        doc.add_heading("Source meetings", level=2)
        for m in meetings or ["—"]:
            doc.add_paragraph(_clean(m), style="List Bullet")
        if log:
            doc.add_heading("Change log", level=2)
            for line in log:
                doc.add_paragraph(_clean(line), style="List Bullet")

    if ask_word_to_update:  # fallback: Word fills in the table of contents page numbers when the file opens
        doc.settings.element.append(_el("w:updateFields", val="true"))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
