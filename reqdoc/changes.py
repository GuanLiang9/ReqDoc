"""Follow-up meetings: compare a new meeting with the approved master, then apply reviewed changes.

Safeguards (from the proposal): nothing is ever deleted, conflicts are never resolved by the AI,
Python assigns IDs, and every change is applied only after a person accepts it.
"""
import re
from collections.abc import Callable
from difflib import SequenceMatcher
from itertools import chain

from . import config
from .dates import pretty
from .llm import LLMClient
from .models import (
    Action, Change, Decision, DiffPass, ITEM_CATEGORIES, LIST_CATEGORIES, Question, Register, Requirement,
    ResolvePass, Risk, Rule, Segment,
)
from .pipeline import chunk_segments, format_segment

Progress = Callable[[str, float], None]

ITEM_CLASSES = {"requirements": Requirement, "business_rules": Rule, "decisions": Decision,
                "actions": Action, "questions": Question, "risks": Risk}
PREFIX = {"business_rules": "BR", "decisions": "DEC", "actions": "ACT", "questions": "Q", "risks": "RSK"}
LABELS = {"requirements": "Requirement", "business_rules": "Business rule", "decisions": "Decision",
          "actions": "Action", "questions": "Question", "risks": "Risk", "objectives": "Objective",
          "scope_in": "In scope", "scope_out": "Out of scope", "scope_deferred": "Deferred",
          "stakeholders": "Stakeholder", "asis_steps": "As-is step", "tobe_steps": "To-be step",
          "data_fields": "Data field", "assumptions": "Assumption", "glossary": "Glossary term"}
# 'Confirmed' only means something for things that can be agreed
CONFIRMABLE = {"requirements", "business_rules", "decisions"}
BATCH = 10
TOP_CANDIDATES = 4
_STOP = {"the", "and", "for", "can", "will", "that", "with", "from", "this", "are", "must", "should", "need", "needs"}


def item_text(item) -> str:
    return getattr(item, "text", None) or getattr(item, "task", "")


def _set_text(item, text: str) -> None:
    if hasattr(item, "task"):
        item.task = text
    else:
        item.text = text


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return max(jaccard, 0.9 * SequenceMatcher(None, a.lower(), b.lower()).ratio())


# --- IDs -----------------------------------------------------------------------

def prefix_for(category: str, item: dict) -> str:
    return item.get("kind", "FR") if category == "requirements" else PREFIX[category]


def next_id(reg: Register, prefix: str) -> str:
    """One past the highest existing number with this prefix, withdrawn items included."""
    top = 0
    for it in chain(reg.requirements, reg.business_rules, reg.decisions, reg.actions, reg.questions, reg.risks):
        m = re.fullmatch(rf"{prefix}-(\d+)", it.id)
        if m:
            top = max(top, int(m.group(1)))
    return f"{prefix}-{top + 1:03d}"


# --- compare -------------------------------------------------------------------

def _diff_category(category: str, existing: list, new: list, llm: LLMClient) -> list[Change]:
    system = (config.PROMPTS_DIR / "diff.md").read_text(encoding="utf-8")
    by_id = {it.id: it for it in existing}
    changes: list[Change] = []
    to_ask: list[tuple[int, list[str]]] = []  # (index into new, candidate ids)

    for i, item in enumerate(new):
        ranked = sorted(existing, key=lambda e: similarity(item_text(item), item_text(e)), reverse=True)
        cands = [e.id for e in ranked[:TOP_CANDIDATES] if similarity(item_text(item), item_text(e)) >= 0.2]
        if cands:
            to_ask.append((i, cands))
        else:
            changes.append(_new_change(category, item))

    for start in range(0, len(to_ask), BATCH):
        batch = to_ask[start:start + BATCH]
        cand_ids = list(dict.fromkeys(c for _, cs in batch for c in cs))
        user = "EXISTING ITEMS\n" + "\n".join(f"{c} [{by_id[c].status}] {item_text(by_id[c])}" for c in cand_ids)
        user += "\n\nNEW ITEMS\n" + "\n".join(f"{n}. {item_text(new[i])}" for n, (i, _) in enumerate(batch))
        result = llm.generate_json(system, user, DiffPass)
        answers = {m.new_index: m for m in result.matches}
        for n, (i, cands) in enumerate(batch):
            m = answers.get(n)
            item = new[i]
            if m is None or m.type == "New" or m.target_id not in cands:
                changes.append(_new_change(category, item))  # when unsure, keep it as a new item: never lose one
                continue
            target = by_id[m.target_id]
            kind = m.type
            unchanged = kind == "Same" or (kind == "Confirmed" and category not in CONFIRMABLE) or (
                kind == "Changed" and item_text(item).strip().lower() == item_text(target).strip().lower())
            if unchanged:
                # same action, but this meeting may have moved the owner or the due date
                update = _action_update(target, item) if category == "actions" else None
                if update:
                    changes.append(update)
                continue
            changes.append(Change(type=kind, category=category, target_id=target.id, text=item_text(item),
                                  old=item_text(target), timestamp=getattr(item, "timestamp", ""),
                                  quote=getattr(item, "quote", ""), item=item.model_dump()))
    return changes


def _action_detail(task: str, owner: str, due: str, due_date: str) -> str:
    when = f"{due} ({pretty(due_date)})" if due and due_date and due.strip().lower() != due_date else (due or pretty(due_date))
    return f"{task} (owner: {owner or 'nobody'}, due: {when or 'no date'})"


def _action_update(target, item) -> Change | None:
    """The new meeting repeats an existing action with a different owner or due date."""
    new_owner, new_due = item.owner.strip(), item.due.strip()
    owner_moved = bool(new_owner) and new_owner.lower() != target.owner.strip().lower()
    due_moved = bool(new_due) and new_due.lower() != target.due.strip().lower() and not (
        item.due_date and item.due_date == target.due_date)
    if not (owner_moved or due_moved):
        return None
    return Change(type="Changed", category="actions", target_id=target.id,
                  text=_action_detail(target.task, new_owner if owner_moved else target.owner,
                                      new_due if due_moved else target.due,
                                      item.due_date if due_moved else target.due_date),
                  old=_action_detail(target.task, target.owner, target.due, target.due_date),
                  timestamp=item.timestamp, quote=item.quote, item=item.model_dump())


def _new_change(category: str, item) -> Change:
    return Change(type="New", category=category, text=item_text(item), timestamp=getattr(item, "timestamp", ""),
                  quote=getattr(item, "quote", ""), item=item.model_dump())


def _diff_lists(category: str, existing: list, new: list) -> list[Change]:
    """Plain lists (steps, scope, fields...): anything not already there is proposed as New."""
    out = []
    if category == "glossary":
        known = {g.term.strip().lower() for g in existing}
        for g in new:
            if g.term.strip().lower() not in known:
                out.append(Change(type="New", category=category, text=g.term, item=g.model_dump()))
        return out
    for s in new:
        if not any(similarity(s, e) >= 0.85 for e in existing):
            out.append(Change(type="New", category=category, text=s, item={"text": s}))
    return out


def _resolve_open(master: Register, segments: list[Segment], llm: LLMClient, progress: Progress | None) -> list[Change]:
    """Open questions answered and open actions finished in the new meeting."""
    open_q = {q.id: q for q in master.questions if q.status == "Open"}
    open_a = {a.id: a for a in master.actions if a.status == "Open"}
    if not open_q and not open_a:
        return []
    system = (config.PROMPTS_DIR / "resolve.md").read_text(encoding="utf-8")
    q_lines = "\n".join(f"{i} {q.text}" for i, q in open_q.items()) or "(none)"
    a_lines = "\n".join(f"{i} {a.task}" for i, a in open_a.items()) or "(none)"
    head = f"OPEN QUESTIONS\n{q_lines}\n\nOPEN ACTIONS\n{a_lines}\n\nTranscript:\n"
    changes, seen = [], set()
    chunks = chunk_segments(segments, config.CHUNK_TOKENS)
    for n, chunk in enumerate(chunks, 1):
        if progress:
            progress(f"Checking open questions and actions (part {n} of {len(chunks)})", n / (len(chunks) + 1))
        res = llm.generate_json(system, head + "\n".join(format_segment(s) for s in chunk), ResolvePass)
        for a in res.answered:
            if a.question_id in open_q and a.question_id not in seen and a.answer.strip():
                seen.add(a.question_id)
                changes.append(Change(type="Answered", category="questions", target_id=a.question_id, text=a.answer,
                                      old=open_q[a.question_id].text, timestamp=a.timestamp, quote=a.quote))
        for d in res.done:
            if d.action_id in open_a and d.action_id not in seen:
                seen.add(d.action_id)
                changes.append(Change(type="ActionDone", category="actions", target_id=d.action_id,
                                      text="Done", old=open_a[d.action_id].task, timestamp=d.timestamp, quote=d.quote))
    return changes


def compute_changes(master: Register, new: Register, segments: list[Segment], llm: LLMClient,
                    progress: Progress | None = None) -> list[Change]:
    changes: list[Change] = []
    steps = len(ITEM_CATEGORIES) + 1
    for n, cat in enumerate(ITEM_CATEGORIES):
        if progress:
            progress(f"Comparing {LABELS[cat].lower()}s with the master document", n / steps)
        changes += _diff_category(cat, getattr(master, cat), getattr(new, cat), llm)
    if progress:
        progress("Checking open questions and actions", len(ITEM_CATEGORIES) / steps)
    changes += _resolve_open(master, segments, llm, progress)
    for cat in LIST_CATEGORIES:
        changes += _diff_lists(cat, getattr(master, cat), getattr(new, cat))
    for n, c in enumerate(changes, 1):
        c.id = f"C{n:03d}"
    return changes


# --- apply ---------------------------------------------------------------------

def apply_change(reg: Register, change: Change) -> None:
    """Apply one accepted change to the draft register. Never deletes anything."""
    meeting = reg.meetings[-1] if reg.meetings else None
    when = meeting.date if meeting else ""
    ev = f" [{change.timestamp}]" if change.timestamp else ""
    cat = change.category

    if cat in LIST_CATEGORIES:
        if change.type != "New":
            raise ValueError(f"Unsupported change for {cat}")
        if cat == "glossary":
            from .models import GlossaryTerm
            reg.glossary.append(GlossaryTerm(**change.item))
        else:
            getattr(reg, cat).append(change.text)
        reg.change_log.append(f"{when} added {LABELS[cat].lower()}: {change.text}{ev}")
        return

    items = getattr(reg, cat)
    if change.type == "New":
        data = dict(change.item)
        data["id"] = next_id(reg, prefix_for(cat, data))
        data["source_meeting"] = meeting.id if meeting else ""
        if cat == "actions":
            data["raised_date"] = data.get("raised_date") or when
        new_item = ITEM_CLASSES[cat](**data)
        items.append(new_item)
        reg.change_log.append(f"{when} added {new_item.id}: {change.text}{ev}")
        return

    target = next((i for i in items if i.id == change.target_id), None)
    if target is None:
        raise ValueError(f"{change.target_id} not found in the draft")
    old = item_text(target)
    label = f"{pretty(when)} · {meeting.title}" if meeting else pretty(when)
    if change.type in ("Changed", "Conflict"):  # an accepted conflict means "use the new version"
        new_text = (change.item.get("task") if cat == "actions" else None) or change.text
        _set_text(target, new_text)
        if cat == "requirements" and change.item.get("priority", "Not stated") != "Not stated":
            target.priority = change.item["priority"]
        if cat == "actions":
            _update_action(target, change.item, label)
        target.timestamp = change.timestamp or target.timestamp
        target.quote = change.quote or target.quote
        reg.change_log.append(f'{when} {target.id} changed: "{old}" -> "{change.text}"{ev}')
    elif change.type == "Confirmed":
        target.status = "Agreed"
        reg.change_log.append(f"{when} {target.id} confirmed as agreed{ev}")
    elif change.type == "Withdrawn":
        target.status = "Withdrawn"
        if cat == "actions":
            _close_action(target, meeting, when, "withdrawn")
        reg.change_log.append(f"{when} {target.id} withdrawn: {old}{ev}")
    elif change.type == "Answered":
        target.status, target.answer = "Answered", change.text
        reg.change_log.append(f"{when} {target.id} answered: {change.text}{ev}")
    elif change.type == "ActionDone":
        target.status = "Done"
        _close_action(target, meeting, when, "done")
        reg.change_log.append(f"{when} {target.id} done: {old}{ev}")


def _update_action(target, item: dict, label: str) -> None:
    """Take a moved owner or due date from the meeting and keep a line saying so."""
    notes = []
    owner = (item.get("owner") or "").strip()
    if owner and owner.lower() != target.owner.strip().lower():
        notes.append(f"owner {target.owner or 'nobody'} -> {owner}")
        target.owner = owner
    due = (item.get("due") or "").strip()
    if due and due.lower() != target.due.strip().lower() and not (item.get("due_date") and item["due_date"] == target.due_date):
        notes.append(f"due {target.due or 'none'} -> {due}" + (f" ({pretty(item['due_date'])})" if item.get("due_date") else ""))
        target.due, target.due_date = due, item.get("due_date") or ""
    if notes:
        target.updates.append(f"{label}: " + "; ".join(notes))


def _close_action(target, meeting, when: str, how: str) -> None:
    target.closed_meeting = meeting.id if meeting else ""
    target.closed_date = when
    target.updates.append(f"{pretty(when)}{' · ' + meeting.title if meeting else ''}: {how}")
