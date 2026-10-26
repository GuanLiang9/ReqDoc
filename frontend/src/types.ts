export interface Project {
  code: string;
  name: string;
  owner: string;
  created: string;
}

export interface ProjectRow extends Project {
  version: string | null;
  has_draft: boolean;
  meetings: number;
}

/** Fields every tracked item in the register has. */
export interface Tracked {
  id: string;
  status: string;
  needs_confirmation: boolean;
  source_meeting: string;
  timestamp: string;
  quote: string;
}

export interface Requirement extends Tracked {
  text: string;
  kind: 'FR' | 'NFR';
  priority: string;
  requested_by: string;
}
export interface Rule extends Tracked {
  text: string;
}
export interface Decision extends Tracked {
  text: string;
  decided_by: string;
}
export interface Question extends Tracked {
  text: string;
  owner: string;
  answer: string;
}
export interface Action extends Tracked {
  task: string;
  owner: string;
  /** the due date as it was said ("Friday") */
  due: string;
  /** the same, as a real date (YYYY-MM-DD); empty when it could not be worked out */
  due_date: string;
  /** date of the meeting that gave the action */
  raised_date: string;
  closed_meeting: string;
  closed_date: string;
  updates: string[];
}
export interface Risk extends Tracked {
  text: string;
}
export interface GlossaryTerm {
  term: string;
  meaning: string;
}
export interface MeetingInfo {
  id: string;
  title: string;
  date: string;
  attendees: string[];
  source_file: string;
}

export type StringListKey =
  | 'objectives'
  | 'scope_in'
  | 'scope_out'
  | 'scope_deferred'
  | 'stakeholders'
  | 'asis_steps'
  | 'tobe_steps'
  | 'data_fields'
  | 'assumptions';

export interface Register extends Record<StringListKey, string[]> {
  project_code: string;
  project_name: string;
  version: string;
  doc_status: 'DRAFT' | 'APPROVED';
  reviewer: string;
  meetings: MeetingInfo[];
  summary: string;
  diagram_mermaid: string;
  requirements: Requirement[];
  business_rules: Rule[];
  decisions: Decision[];
  questions: Question[];
  actions: Action[];
  risks: Risk[];
  glossary: GlossaryTerm[];
  change_log: string[];
}

export type JobStage = 'queued' | 'transcribing' | 'extracting' | 'comparing' | 'done' | 'error';

export interface Job {
  id: string;
  project: string;
  title: string;
  filename: string;
  is_recording: boolean;
  stage: JobStage;
  progress: number;
  message: string;
  error: string;
  result: string;
  draft_created: boolean;
  elapsed: number;
}

export interface ProjectDetail {
  project: Project;
  master_version: string | null;
  has_draft: boolean;
  draft_status: string | null;
  pending_changes: number;
  total_changes: number;
  versions: string[];
  meetings: MeetingInfo[];
  job: Job | null;
  accepted_files: string[];
}

export type ChangeType =
  | 'New'
  | 'Changed'
  | 'Confirmed'
  | 'Withdrawn'
  | 'Conflict'
  | 'Answered'
  | 'ActionDone';

export interface Change {
  id: string;
  type: ChangeType;
  category: string;
  target_id: string;
  text: string;
  old: string;
  timestamp: string;
  quote: string;
  decision: 'pending' | 'accepted' | 'rejected';
}

export interface Health {
  ollama: boolean;
  model: boolean;
  model_name: string;
  detail: string;
  whisper_model: string;
  whisper_ready: boolean;
}

export interface TranscriptLine {
  timestamp: string | null;
  speaker: string;
  text: string;
}
