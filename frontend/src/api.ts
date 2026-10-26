import type {
  Change,
  Health,
  Project,
  ProjectDetail,
  ProjectRow,
  Register,
  TranscriptLine,
} from './types';

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError('Cannot reach the ReqDoc server. Is it running? (run.ps1)');
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join('; ');
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

const enc = encodeURIComponent;

/** The box-to-box workflow picture (SVG text) for the steps currently on screen. */
async function diagramSvg(steps: string[], cols: number, signal?: AbortSignal): Promise<string> {
  const res = await fetch('/api/diagram.svg', { ...json('POST', { steps, cols }), signal });
  if (!res.ok) throw new ApiError(`The diagram could not be drawn (${res.status})`);
  return res.text();
}

export const api = {
  diagramSvg,
  health: () => request<Health>('/health'),
  projects: () => request<ProjectRow[]>('/projects'),
  createProject: (p: { code: string; name: string; owner: string }) =>
    request<Project>('/projects', json('POST', p)),
  project: (code: string) => request<ProjectDetail>(`/projects/${enc(code)}`),
  register: (code: string, version: string) =>
    request<Register>(`/projects/${enc(code)}/register?version=${enc(version)}`),
  draft: (code: string) => request<Register>(`/projects/${enc(code)}/draft`),
  saveDraft: (code: string, reg: Register) =>
    request<Register>(`/projects/${enc(code)}/draft`, json('PUT', reg)),
  discardDraft: (code: string) => request<void>(`/projects/${enc(code)}/draft`, { method: 'DELETE' }),
  approve: (code: string, reviewer: string, major: boolean) =>
    request<{ version: string }>(`/projects/${enc(code)}/approve`, json('POST', { reviewer, major })),
  changes: (code: string) => request<Change[]>(`/projects/${enc(code)}/changes`),
  decide: (code: string, id: string, decision: 'accepted' | 'rejected') =>
    request<Change[]>(`/projects/${enc(code)}/changes/${enc(id)}`, json('POST', { decision })),
  acceptSafe: (code: string) =>
    request<Change[]>(`/projects/${enc(code)}/changes-accept-safe`, { method: 'POST' }),
  transcript: (code: string, meetingId: string) =>
    request<TranscriptLine[]>(`/projects/${enc(code)}/transcripts/${enc(meetingId)}`),
  /** doc: 'spec' = requirement specification, 'notes' = meeting notes and action tracker */
  exportUrl: (code: string, version: string, doc: 'spec' | 'notes' = 'spec') =>
    `/api/projects/${enc(code)}/export.docx?version=${enc(version)}&doc=${doc}`,
};

/** Upload a recording or transcript. XMLHttpRequest (not fetch) so large files show progress. */
export function uploadMeeting(
  code: string,
  form: { file: File; title: string; date: string },
  onProgress: (fraction: number) => void,
): Promise<{ job_id: string }> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append('file', form.file);
    body.append('title', form.title);
    body.append('date', form.date);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/projects/${enc(code)}/meetings`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onerror = () => reject(new ApiError('Upload failed. Is the ReqDoc server running?'));
    xhr.onload = () => {
      let parsed: { detail?: unknown; job_id?: string } = {};
      try {
        parsed = JSON.parse(xhr.responseText);
      } catch {
        /* not JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300 && parsed.job_id) resolve({ job_id: parsed.job_id });
      else reject(new ApiError(typeof parsed.detail === 'string' ? parsed.detail : `Upload failed (${xhr.status})`));
    };
    xhr.send(body);
  });
}
