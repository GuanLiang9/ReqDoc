"""Turn a due date as people say it ("Monday", "5 November", "end of the week") into a real date.

Deterministic, no AI: relative words are counted from the meeting date. Anything we can't pin down
("next meeting", "soon") gives "" and the spoken words are kept as they are.
"""
import re
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_FILLER = re.compile(r"\b(by|on|before|until|till|the|this|of|coming|latest|at|no later than|eod|cob)\b")


def _parse_iso(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip()[:10])
    except ValueError:
        return None


def _month(word: str) -> int | None:
    return _MONTHS.get(word[:3]) if len(word) >= 3 else None


def _day_month(day: int, month: int, year: int | None, base: date) -> date | None:
    """A day and month; without a year, the next one on or after the meeting."""
    try:
        if year:
            return date(year if year > 99 else 2000 + year, month, day)
        d = date(base.year, month, day)
        return d if d >= base else date(base.year + 1, month, day)
    except ValueError:
        return None


def resolve_due(text: str, meeting_date: str) -> str:
    """'' when the date can't be worked out. Returns YYYY-MM-DD."""
    base = _parse_iso(meeting_date or "")
    raw = (text or "").strip().lower()
    if not raw:
        return ""
    exact = _parse_iso(raw)
    if exact:
        return exact.isoformat()
    if base is None:
        return ""
    s = re.sub(r"[,.]", " ", raw)
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"\s+", " ", _FILLER.sub(" ", s)).strip()

    # 30/10, 30/10/2026, 30-10-26 (day first, as written in Singapore)
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", s)
    if m:
        d = _day_month(int(m[1]), int(m[2]), int(m[3]) if m[3] else None, base)
        return d.isoformat() if d else ""

    # 5 november (2026) / november 5 (2026)
    m = re.fullmatch(r"(\d{1,2}) ([a-z]+)(?: (\d{4}))?", s)
    if m and _month(m[2]):
        d = _day_month(int(m[1]), _month(m[2]), int(m[3]) if m[3] else None, base)
        return d.isoformat() if d else ""
    m = re.fullmatch(r"([a-z]+) (\d{1,2})(?: (\d{4}))?", s)
    if m and _month(m[1]):
        d = _day_month(int(m[2]), _month(m[1]), int(m[3]) if m[3] else None, base)
        return d.isoformat() if d else ""

    if s in ("today", "end day", "end today"):
        return base.isoformat()
    if s == "tomorrow":
        return (base + timedelta(days=1)).isoformat()

    # monday / next monday
    m = re.fullmatch(r"(?:next )?([a-z]+)", s)
    if m and m[1] in _WEEKDAYS:  # the coming one, never today
        return (base + timedelta(days=(_WEEKDAYS.index(m[1]) - base.weekday()) % 7 or 7)).isoformat()

    friday = base + timedelta(days=(4 - base.weekday()) % 7)
    if s in ("end week", "week", "eow", "end work week"):
        return friday.isoformat()
    if s in ("next week", "end next week"):
        return (friday + timedelta(days=7)).isoformat()
    if s in ("end month", "month end", "eom"):
        return base.replace(day=monthrange(base.year, base.month)[1]).isoformat()
    if s in ("next month", "end next month"):
        y, mo = (base.year + 1, 1) if base.month == 12 else (base.year, base.month + 1)
        return date(y, mo, monthrange(y, mo)[1]).isoformat()

    # in 3 days / in 2 weeks / within 2 weeks
    m = re.fullmatch(r"(?:in|within) (\d+|a|one|two|three|four) (day|days|week|weeks)", s)
    if m:
        n = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4}.get(m[1]) or int(m[1])
        return (base + timedelta(days=n * (7 if m[2].startswith("week") else 1))).isoformat()
    return ""


def today_sgt() -> str:
    """Today in Singapore (the team's timezone), YYYY-MM-DD."""
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def pretty(iso: str) -> str:
    """'2026-10-30' -> '30 Oct 2026' (or the input when it isn't a date)."""
    d = _parse_iso(iso or "")
    return f"{d.day} {d.strftime('%b %Y')}" if d else (iso or "")
