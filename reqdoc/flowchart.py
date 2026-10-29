"""To-be steps -> box-to-box flow diagram, laid out as a snake (left to right, then right to left).

Built by code, not by the AI. One layout feeds two painters: SVG for the website and PNG for Word,
so both always show the same picture with the full wording (no "..." cut-offs).
"""
import io
import re
from dataclasses import dataclass
from functools import lru_cache
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

MAX_NODES = 30

# palette (Woh Hup logo gold and grey, site ink)
INK = "#231F20"
GOLD = "#B68D29"
GOLD_TINT = "#F8F0DC"
GOLD_DEEP = "#7A5A12"
GREY = "#54555B"
LINE = "#C9C4B6"
WHITE = "#FFFFFF"

# Two looks for the same layout: "word" keeps the Woh Hup gold for the Word document,
# "web" follows the website (apple.com style: light grey boxes, blue numbers, orange decisions).
PALETTES = {
    "word": dict(text=INK, pill=INK, pill_text=WHITE, box_fill=WHITE, box_stroke=INK, box_sw=1.4,
                 dec_fill=GOLD_TINT, dec_stroke=GOLD, dec_sw=2, badge=INK, badge_text=WHITE,
                 dec_badge=GOLD, dec_badge_text=INK, label=GOLD_DEEP, muted=GREY, arrow=GREY,
                 font="'Segoe UI', Inter, system-ui, Arial, sans-serif"),
    "web": dict(text="#1D1D1F", pill="#1D1D1F", pill_text="#FFFFFF", box_fill="#F5F5F7", box_stroke="#E8E8ED", box_sw=1,
                dec_fill="#FFF1E6", dec_stroke="#FFD2AD", dec_sw=1.4, badge="#0071E3", badge_text="#FFFFFF",
                dec_badge="#B64400", dec_badge_text="#FFFFFF", label="#B64400", muted="#86868B", arrow="#86868B",
                font="-apple-system, BlinkMacSystemFont, 'SF Pro Text', Inter, 'Segoe UI', Arial, sans-serif"),
}

# geometry (logical px)
CELL_W = 224
GAP = 60
MARGIN = 20
PAD = 14
FONT = 14
LINE_H = 19
BADGE_R = 11
PILL_H = 38
PILL_W = 120
ROW_GAP = 46
TOP_STUB = 34
# browsers may draw the font slightly wider than the one we measure with
WRAP_SAFETY = 0.92

_DECISION = re.compile(r"^\s*(if|when|where)\b", re.I)

_FONT_FILES = {
    False: ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    True: ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
}


def is_decision(step: str) -> bool:
    return bool(_DECISION.match(step))


def clean_steps(steps: list[str]) -> list[str]:
    cleaned = [re.sub(r"\s+", " ", s).strip() for s in steps]
    return [s for s in cleaned if s][:MAX_NODES]


@lru_cache(maxsize=16)
def _font(size: float, bold: bool):
    for name in _FONT_FILES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _width(text: str, size: float = FONT, bold: bool = False) -> float:
    return _font(size, bold).getlength(text)


def _wrap(text: str, max_width: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        while _width(word) > max_width:  # a single very long word: break it
            cut = len(word)
            while cut > 1 and _width(word[:cut]) > max_width:
                cut -= 1
            if line:
                lines.append(line)
                line = ""
            lines.append(word[:cut])
            word = word[cut:]
        trial = f"{line} {word}".strip()
        if line and _width(trial) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines or [""]


# --- layout ----------------------------------------------------------------------

@dataclass
class Node:
    kind: str  # start | end | step | decision
    lines: list[str]
    number: int = 0
    row: int = 0
    col: int = 0
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


@dataclass
class Layout:
    nodes: list[Node]
    row_y: list[float]
    row_h: list[float]
    cols: int
    width: float
    height: float
    rtl_rows: set


def layout(steps: list[str], cols: int) -> Layout:
    steps = clean_steps(steps)
    nodes = [Node("start", ["Start"])]
    for n, step in enumerate(steps, 1):
        nodes.append(Node("decision" if is_decision(step) else "step", _wrap(step, (CELL_W - 2 * PAD) * WRAP_SAFETY), n))
    nodes.append(Node("end", ["End"]))

    cols = max(1, min(cols, len(nodes)))
    rows = [nodes[i:i + cols] for i in range(0, len(nodes), cols)]
    row_h = []
    for row in rows:
        tallest = max((PAD + 22 + 8 + len(n.lines) * LINE_H + PAD) if n.kind in ("step", "decision") else PILL_H for n in row)
        row_h.append(float(tallest))
    row_y, y = [], float(MARGIN)
    for h in row_h:
        row_y.append(y)
        y += h + ROW_GAP

    rtl = set()
    for r, row in enumerate(rows):
        right_to_left = r % 2 == 1
        if right_to_left:
            rtl.add(r)
        for i, node in enumerate(row):
            node.row = r
            node.col = cols - 1 - i if right_to_left else i
            cell_x = MARGIN + node.col * (CELL_W + GAP)
            if node.kind in ("start", "end"):
                node.w, node.h = PILL_W, PILL_H
                node.x = cell_x + (CELL_W - PILL_W) / 2
                node.y = row_y[r] + (row_h[r] - PILL_H) / 2
            else:
                node.w, node.h = CELL_W, row_h[r]
                node.x, node.y = cell_x, row_y[r]

    width = 2 * MARGIN + cols * CELL_W + (cols - 1) * GAP
    height = row_y[-1] + row_h[-1] + MARGIN
    return Layout(nodes, row_y, row_h, cols, width, height, rtl)


# --- drawing primitives (shared by both painters) ---------------------------------

def _prims(lay: Layout, r0: int, r1: int, pal: dict) -> tuple[list[tuple], float, float]:
    """Primitives for rows r0..r1 (inclusive), shifted so the slice starts near the top.
    Returns (primitives, width, height). A slice that does not start at row 0 or end at the last row
    gets a 'continued' stub so the reader knows the flow carries on."""
    first = r0 > 0
    last = r1 < len(lay.row_y) - 1
    top = TOP_STUB if first else 0
    dy = top - lay.row_y[r0] + MARGIN
    nodes = [n for n in lay.nodes if r0 <= n.row <= r1]
    out: list[tuple] = []

    def arrow(x1, y1, x2, y2):
        out.append(("arrow", x1, y1, x2, y2, pal["arrow"]))

    # edges first so boxes sit on top
    all_nodes = lay.nodes
    for a, b in zip(all_nodes, all_nodes[1:]):
        if a.row < r0 or a.row > r1:
            continue
        label = "Yes" if a.kind == "decision" else ""
        if a.row == b.row:
            y = a.y + a.h / 2 + dy
            if a.row in lay.rtl_rows:
                x1, x2 = a.x, b.x + b.w
            else:
                x1, x2 = a.x + a.w, b.x
            arrow(x1, y, x2, y)
            if label:
                out.append(("text", (x1 + x2) / 2, y - 7, label, 12, True, pal["label"], "middle"))
        else:
            x = a.x + a.w / 2
            y1, y2 = a.y + a.h + dy, b.y + dy
            if b.row > r1:  # slice ends here: stub going down
                y2 = y1 + ROW_GAP - 6
            arrow(x, y1, x, y2)
            if label:
                out.append(("text", x + 8, (y1 + y2) / 2 + 4, label, 12, True, pal["label"], "start"))
    if last:
        n = max((n for n in nodes if n.row == r1), key=lambda n: n.col if r1 % 2 == 0 else -n.col)
        out.append(("text", n.x + n.w / 2, n.y + n.h + dy + ROW_GAP + 4, "continued on the next part", 12, False, pal["muted"], "middle"))
    if first:
        n = min((n for n in nodes if n.row == r0), key=lambda n: n.col if r0 % 2 == 0 else -n.col)
        cx = n.x + n.w / 2
        out.append(("text", cx, MARGIN + 2, "continued from the previous part", 12, False, pal["muted"], "middle"))
        arrow(cx, MARGIN + 8, cx, n.y + dy)

    for n in nodes:
        x, y = n.x, n.y + dy
        if n.kind in ("start", "end"):
            out.append(("rect", x, y, n.w, n.h, n.h / 2, pal["pill"], pal["pill"], 1))
            out.append(("text", x + n.w / 2, y + n.h / 2 + 5, n.lines[0], FONT, True, pal["pill_text"], "middle"))
            continue
        decision = n.kind == "decision"
        out.append(("rect", x, y, n.w, n.h, 12 if pal is PALETTES["word"] else 16, pal["dec_fill"] if decision else pal["box_fill"],
                    pal["dec_stroke"] if decision else pal["box_stroke"], pal["dec_sw"] if decision else pal["box_sw"]))
        cx, cy = x + PAD + BADGE_R, y + PAD + BADGE_R
        out.append(("circle", cx, cy, BADGE_R, pal["dec_badge"] if decision else pal["badge"]))
        out.append(("text", cx, cy + 4.5, str(n.number), 12, True, pal["dec_badge_text"] if decision else pal["badge_text"], "middle"))
        if decision:
            out.append(("text", cx + BADGE_R + 8, cy + 4, "DECISION", 10.5, True, pal["label"], "start"))
        for i, line in enumerate(n.lines):
            out.append(("text", x + PAD, y + PAD + 22 + 8 + 14 + i * LINE_H - 3, line, FONT, False, pal["text"], "start"))
    return out, lay.width, (lay.row_y[r1] + lay.row_h[r1] + dy + MARGIN + (ROW_GAP if last else 0))


# --- painters ---------------------------------------------------------------------

ARROW_HEAD = 8


def _arrow_head(x1, y1, x2, y2) -> list[tuple[float, float]]:
    """Triangle at (x2, y2) pointing away from (x1, y1); the flow is always horizontal or vertical."""
    if y1 == y2:
        s = 1 if x2 > x1 else -1
        return [(x2, y2), (x2 - s * ARROW_HEAD, y2 - ARROW_HEAD / 2 - 1), (x2 - s * ARROW_HEAD, y2 + ARROW_HEAD / 2 + 1)]
    s = 1 if y2 > y1 else -1
    return [(x2, y2), (x2 - ARROW_HEAD / 2 - 1, y2 - s * ARROW_HEAD), (x2 + ARROW_HEAD / 2 + 1, y2 - s * ARROW_HEAD)]


def _svg(prims: list[tuple], width: float, height: float, font: str) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" '
        f'role="img" aria-label="Workflow diagram" font-family="{font}">'
    ]
    for p in prims:
        kind = p[0]
        if kind == "rect":
            _, x, y, w, h, r, fill, stroke, sw = p
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        elif kind == "circle":
            _, x, y, r, fill = p
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>')
        elif kind == "arrow":
            _, x1, y1, x2, y2, color = p
            head = " ".join(f"{px:.1f},{py:.1f}" for px, py in _arrow_head(x1, y1, x2, y2))
            parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.6"/>')
            parts.append(f'<polygon points="{head}" fill="{color}"/>')
        else:
            _, x, y, text, size, bold, color, anchor = p
            weight = ' font-weight="700"' if bold else ""
            parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}"{weight} fill="{color}" text-anchor="{anchor}">{escape(text)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _png(prims: list[tuple], width: float, height: float, scale: int = 2) -> bytes:
    img = Image.new("RGB", (round(width * scale), round(height * scale)), WHITE)
    d = ImageDraw.Draw(img)
    k = scale
    for p in prims:
        kind = p[0]
        if kind == "rect":
            _, x, y, w, h, r, fill, stroke, sw = p
            d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + h) * k], radius=r * k, fill=fill, outline=stroke, width=max(1, round(sw * k)))
        elif kind == "circle":
            _, x, y, r, fill = p
            d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=fill)
        elif kind == "arrow":
            _, x1, y1, x2, y2, color = p
            d.line([x1 * k, y1 * k, x2 * k, y2 * k], fill=color, width=round(1.6 * k))
            d.polygon([(px * k, py * k) for px, py in _arrow_head(x1, y1, x2, y2)], fill=color)
        else:
            _, x, y, text, size, bold, color, anchor = p
            d.text((x * k, y * k), text, font=_font(size * k, bold), fill=color, anchor="ms" if anchor == "middle" else "ls")
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(96 * scale, 96 * scale), optimize=True)
    return buf.getvalue()


def to_svg(steps: list[str], cols: int = 4, palette: str = "web") -> str:
    """The whole diagram as one SVG ('' when there are no steps). palette: "web" or "word"."""
    if not clean_steps(steps):
        return ""
    pal = PALETTES.get(palette, PALETTES["web"])
    lay = layout(steps, cols)
    return _svg(*_prims(lay, 0, len(lay.row_y) - 1, pal), pal["font"])


def to_png_parts(steps: list[str], cols: int = 3, max_height: float = 860) -> list[bytes]:
    """The diagram as one or more PNGs. A long flow is cut between rows so each part fits on a page."""
    if not clean_steps(steps):
        return []
    lay = layout(steps, cols)
    parts, start = [], 0
    for r in range(len(lay.row_y)):
        height = lay.row_y[r] + lay.row_h[r] - lay.row_y[start] + 2 * MARGIN + TOP_STUB + ROW_GAP
        if height > max_height and r > start:
            parts.append(_png(*_prims(lay, start, r - 1, PALETTES["word"])))
            start = r
    parts.append(_png(*_prims(lay, start, len(lay.row_y) - 1, PALETTES["word"])))
    return parts
