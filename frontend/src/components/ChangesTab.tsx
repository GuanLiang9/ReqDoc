import { useState, type ReactNode } from 'react';
import { Button, Segmented } from 'antd';
import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import type { Change, ChangeType } from '../types';
import Chip from './Chip';

const CATEGORY: Record<string, string> = {
  requirements: 'Requirement',
  business_rules: 'Business rule',
  decisions: 'Decision',
  actions: 'Action',
  questions: 'Question',
  risks: 'Risk',
  objectives: 'Objective',
  scope_in: 'In scope',
  scope_out: 'Out of scope',
  scope_deferred: 'Deferred',
  stakeholders: 'Stakeholder',
  asis_steps: 'Current process step',
  tobe_steps: 'Proposed process step',
  data_fields: 'Data field',
  assumptions: 'Assumption',
  glossary: 'Glossary term',
};

const TYPE: Record<ChangeType, { color: string; label: string; order: number }> = {
  Conflict: { color: '#A8362B', label: 'Conflict · needs your decision', order: 0 },
  Changed: { color: '#8F5A1E', label: 'Changed', order: 1 },
  New: { color: '#2F5D3A', label: 'New', order: 2 },
  Withdrawn: { color: '#6B6660', label: 'No longer needed', order: 3 },
  Confirmed: { color: '#2C4A63', label: 'Confirmed', order: 4 },
  Answered: { color: '#4B3F72', label: 'Question answered', order: 5 },
  ActionDone: { color: '#2C4A63', label: 'Action done', order: 6 },
};

interface Props {
  changes: Change[];
  busy: boolean;
  onDecide: (id: string, decision: 'accepted' | 'rejected') => void;
  onAcceptSafe: () => void;
  onEvidence: (c: Change) => void;
}

const Old = ({ children }: { children: string }) => (
  <div className="rounded-lg bg-rose px-3 py-2 text-[#6E2A22] line-through decoration-[#C98A82]">{children}</div>
);
const New = ({ children }: { children: string }) => (
  <div className="rounded-lg bg-sage px-3 py-2 text-[#24472D]">{children}</div>
);
const Label = ({ children }: { children: string }) => <div className="eyebrow mb-1.5">{children}</div>;

function Body({ c }: { c: Change }) {
  switch (c.type) {
    case 'Changed':
    case 'Conflict':
      return (
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>{`Now in the document · ${c.target_id}`}</Label>
            <Old>{c.old}</Old>
          </div>
          <div>
            <Label>Said in this meeting</Label>
            <New>{c.text}</New>
          </div>
        </div>
      );
    case 'Answered':
      return (
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>{`Open question · ${c.target_id}`}</Label>
            <div className="rounded-lg bg-stone px-3 py-2">{c.old}</div>
          </div>
          <div>
            <Label>Answer</Label>
            <New>{c.text}</New>
          </div>
        </div>
      );
    case 'ActionDone':
      return (
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-muted">{c.target_id}</span>
          <span>{c.old}</span>
          <Chip tone="approved">marked done</Chip>
        </div>
      );
    case 'Withdrawn':
      return (
        <div>
          <span className="mr-2 text-muted">{c.target_id}</span>
          <span className="line-through decoration-muted">{c.old}</span>
        </div>
      );
    case 'Confirmed':
      return (
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-muted">{c.target_id}</span>
          <span>{c.old}</span>
          <Chip tone="approved">will be marked Agreed</Chip>
        </div>
      );
    default:
      return <New>{c.text}</New>;
  }
}

export default function ChangesTab({ changes, busy, onDecide, onAcceptSafe, onEvidence }: Props) {
  const [filter, setFilter] = useState<'pending' | 'all'>('pending');
  const pending = changes.filter((c) => c.decision === 'pending');
  const shown = (filter === 'pending' ? pending : changes).slice().sort((a, b) => TYPE[a.type].order - TYPE[b.type].order);
  const safeCount = pending.filter((c) => c.type !== 'Conflict').length;

  if (!changes.length) {
    return (
      <div className="py-12 text-center">
        <p className="serif m-0 text-[24px]">No follow-up changes.</p>
        <p className="m-0 mt-1 text-muted">This draft is the first version of the document.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Segmented
          value={filter}
          onChange={(v) => setFilter(v as 'pending' | 'all')}
          options={[
            { value: 'pending', label: `Needs a decision (${pending.length})` },
            { value: 'all', label: `All (${changes.length})` },
          ]}
        />
        <Button disabled={!safeCount} loading={busy} onClick={onAcceptSafe}>
          Accept all except conflicts ({safeCount})
        </Button>
      </div>

      {pending.some((c) => c.type === 'Conflict') && (
        <p className="serif m-0 mb-5 text-[20px] leading-snug" style={{ color: '#8F5A1E' }}>
          Conflicts are never decided by the AI. Choose which version is right for each one.
        </p>
      )}

      {!shown.length && (
        <div className="py-12 text-center">
          <p className="serif m-0 text-[24px]">Every change is decided.</p>
          <p className="m-0 mt-1 text-muted">Review the Requirements tab, then approve.</p>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {shown.map((c) => (
          <article
            key={c.id}
            data-testid="change-card"
            data-type={c.type}
            className={`rounded-2xl border border-line bg-[#FCFBF7] p-5 ${c.type === 'Conflict' && c.decision === 'pending' ? 'rule-left' : ''}`}
          >
            <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
              <span className="eyebrow flex items-center gap-2" style={{ color: TYPE[c.type].color }}>
                <i className="inline-block h-2 w-2 rounded-full" style={{ background: TYPE[c.type].color }} />
                {TYPE[c.type].label}
              </span>
              <span className="text-[13px] text-muted">{CATEGORY[c.category] ?? c.category}</span>
              <span className="grow" />
              {c.decision === 'pending' ? (
                <Space2>
                  {c.type === 'Conflict' ? (
                    <>
                      <Button size="small" icon={<CloseOutlined />} disabled={busy} onClick={() => onDecide(c.id, 'rejected')}>Keep existing</Button>
                      <Button size="small" type="primary" icon={<CheckOutlined />} disabled={busy} onClick={() => onDecide(c.id, 'accepted')}>Use new wording</Button>
                    </>
                  ) : (
                    <>
                      <Button size="small" icon={<CloseOutlined />} disabled={busy} onClick={() => onDecide(c.id, 'rejected')}>Reject</Button>
                      <Button size="small" type="primary" icon={<CheckOutlined />} disabled={busy} onClick={() => onDecide(c.id, 'accepted')}>Accept</Button>
                    </>
                  )}
                </Space2>
              ) : (
                <Chip tone={c.decision === 'accepted' ? 'approved' : 'muted'}>{c.decision === 'accepted' ? 'Accepted' : 'Rejected'}</Chip>
              )}
            </div>
            <Body c={c} />
            {(c.timestamp || c.quote) && (
              <div className="mt-3 text-[13px] text-muted">
                {c.quote && <span className="serif text-[16px]">“{c.quote}” </span>}
                <Button type="link" size="small" className="px-1" onClick={() => onEvidence(c)}>
                  {c.timestamp ? `[${c.timestamp}] see transcript` : 'see transcript'}
                </Button>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

function Space2({ children }: { children: ReactNode }) {
  return <span className="flex flex-wrap gap-2">{children}</span>;
}
