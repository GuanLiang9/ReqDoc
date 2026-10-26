"""Single schema shared by LLM output, storage and rendering.

Extracted* classes are what the LLM fills in (no IDs, no status).
*Record classes are what lives in the register (Python assigns id/status).
"""
from typing import Literal

from pydantic import BaseModel, field_validator

# small models write these instead of leaving a field empty
_NOT_A_NAME = {"unknown", "n/a", "na", "none", "null", "not stated", "not specified", "unspecified", "tbc", "tbd",
               "-", "—", "nobody", "no one", "unclear"}


def _blank_if_unknown(value):
    return "" if isinstance(value, str) and value.strip().lower().rstrip(".") in _NOT_A_NAME else value


class Segment(BaseModel):
    timestamp: str | None = None  # HH:MM:SS
    speaker: str = ""
    text: str


# --- LLM output --------------------------------------------------------------

class Quoted(BaseModel):
    text: str
    timestamp: str = ""  # HH:MM:SS from the transcript
    quote: str = ""  # short verbatim words from the transcript


class ExtractedRequirement(Quoted):
    kind: Literal["FR", "NFR"] = "FR"
    priority: Literal["Must", "Should", "Could", "Not stated"] = "Not stated"
    requested_by: str = ""

    _clean = field_validator("requested_by", mode="before")(_blank_if_unknown)


class ExtractedDecision(Quoted):
    decided_by: str = ""

    _clean = field_validator("decided_by", mode="before")(_blank_if_unknown)


class ExtractedQuestion(Quoted):
    owner: str = ""

    _clean = field_validator("owner", mode="before")(_blank_if_unknown)


class ExtractedAction(BaseModel):
    task: str
    owner: str = ""
    due: str = ""
    timestamp: str = ""
    quote: str = ""

    _clean = field_validator("owner", "due", mode="before")(_blank_if_unknown)


class GlossaryTerm(BaseModel):
    term: str
    meaning: str = ""


class Extraction(BaseModel):
    objectives: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []
    scope_deferred: list[str] = []
    stakeholders: list[str] = []
    requirements: list[ExtractedRequirement] = []
    asis_steps: list[str] = []
    tobe_steps: list[str] = []
    business_rules: list[Quoted] = []
    data_fields: list[str] = []
    assumptions: list[str] = []
    decisions: list[ExtractedDecision] = []
    questions: list[ExtractedQuestion] = []
    actions: list[ExtractedAction] = []
    risks: list[Quoted] = []
    glossary: list[GlossaryTerm] = []


# One focused schema per extraction pass (small models do better with one job per call).
class RequirementsPass(BaseModel):
    requirements: list[ExtractedRequirement] = []
    business_rules: list[Quoted] = []
    data_fields: list[str] = []
    objectives: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []
    scope_deferred: list[str] = []
    stakeholders: list[str] = []
    assumptions: list[str] = []


class ProcessPass(BaseModel):
    asis_steps: list[str] = []
    tobe_steps: list[str] = []


class DecisionsPass(BaseModel):
    decisions: list[ExtractedDecision] = []
    glossary: list[GlossaryTerm] = []


class ActionsPass(BaseModel):
    actions: list[ExtractedAction] = []


class IssuesPass(BaseModel):
    questions: list[ExtractedQuestion] = []
    risks: list[Quoted] = []


class Summary(BaseModel):
    summary: str


# --- Register (stored) -------------------------------------------------------

class Tracked(BaseModel):
    id: str = ""
    status: str = "Proposed"
    needs_confirmation: bool = False
    source_meeting: str = ""


class Requirement(ExtractedRequirement, Tracked):
    pass


class Decision(ExtractedDecision, Tracked):
    status: str = "Agreed"


class Question(ExtractedQuestion, Tracked):
    status: str = "Open"
    answer: str = ""


class Action(ExtractedAction, Tracked):
    status: str = "Open"
    raised_date: str = ""  # date of the meeting that gave the action (YYYY-MM-DD)
    due_date: str = ""  # `due` as a real date (YYYY-MM-DD), "" when it could not be worked out
    closed_meeting: str = ""  # meeting id in which it was marked done or withdrawn
    closed_date: str = ""
    updates: list[str] = []  # one line each time a later meeting moved the owner or due date


class Risk(Quoted, Tracked):
    status: str = "Open"


class Rule(Quoted, Tracked):
    status: str = "Proposed"


class MeetingInfo(BaseModel):
    id: str
    title: str
    date: str
    attendees: list[str] = []
    source_file: str = ""  # original upload name


class Register(BaseModel):
    schema_version: int = 2
    project_code: str
    project_name: str = ""
    version: str = "0.1"
    doc_status: Literal["DRAFT", "APPROVED"] = "DRAFT"
    reviewer: str = ""
    meetings: list[MeetingInfo] = []
    summary: str = ""
    objectives: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []
    scope_deferred: list[str] = []
    stakeholders: list[str] = []
    requirements: list[Requirement] = []
    asis_steps: list[str] = []
    tobe_steps: list[str] = []
    diagram_mermaid: str = ""
    business_rules: list[Rule] = []
    data_fields: list[str] = []
    assumptions: list[str] = []
    decisions: list[Decision] = []
    questions: list[Question] = []
    actions: list[Action] = []
    risks: list[Risk] = []
    glossary: list[GlossaryTerm] = []
    change_log: list[str] = []  # one line per applied follow-up change


class Project(BaseModel):
    code: str
    name: str
    owner: str = ""
    created: str = ""


ITEM_CATEGORIES = ["requirements", "business_rules", "decisions", "actions", "questions", "risks"]
LIST_CATEGORIES = ["objectives", "scope_in", "scope_out", "scope_deferred", "stakeholders", "asis_steps",
                   "tobe_steps", "data_fields", "assumptions", "glossary"]
Category = Literal["requirements", "business_rules", "decisions", "actions", "questions", "risks",
                   "objectives", "scope_in", "scope_out", "scope_deferred", "stakeholders", "asis_steps",
                   "tobe_steps", "data_fields", "assumptions", "glossary"]
ChangeType = Literal["New", "Changed", "Confirmed", "Withdrawn", "Conflict", "Answered", "ActionDone"]


# LLM output for the follow-up comparison
class DiffMatch(BaseModel):
    new_index: int  # which new item (0-based, as numbered in the prompt)
    type: Literal["New", "Same", "Changed", "Confirmed", "Withdrawn", "Conflict"]
    target_id: str  # id of the matching existing item ("" when type is New)


class DiffPass(BaseModel):
    matches: list[DiffMatch] = []


class AnsweredQuestion(BaseModel):
    question_id: str
    answer: str
    timestamp: str = ""
    quote: str = ""


class DoneAction(BaseModel):
    action_id: str
    timestamp: str = ""
    quote: str = ""


class ResolvePass(BaseModel):
    answered: list[AnsweredQuestion] = []
    done: list[DoneAction] = []


class Change(BaseModel):
    id: str = ""
    type: ChangeType
    category: Category
    target_id: str = ""  # existing item (all types except New)
    text: str = ""  # new wording / new item text
    old: str = ""  # existing wording at diff time
    timestamp: str = ""
    quote: str = ""
    item: dict = {}  # full new item for type New
    decision: Literal["pending", "accepted", "rejected"] = "pending"
