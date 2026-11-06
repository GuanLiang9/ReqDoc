import { useEffect, useState } from 'react';
import { Skeleton } from 'antd';
import { api } from '../api';
import { prettyDate } from '../dates';
import type { ReviewRecord } from '../types';
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

/** What was proposed for one version and what the reviewer decided, so a rejected item is never silently lost. */
export default function ReviewLog({ code, version }: { code: string; version: string }) {
  const [record, setRecord] = useState<ReviewRecord | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.review(code, version).then(setRecord).catch((e) => setError(e.message));
  }, [code, version]);

  if (error) return <span className="text-red">{error}</span>;
  if (!record) return <Skeleton active paragraph={{ rows: 2 }} title={false} />;
  if (record.recorded === false) {
    return <p className="m-0 text-ink2">No review record was kept for this version. Records are kept for versions approved from now on.</p>;
  }

  const accepted = record.changes.filter((c) => c.decision === 'accepted').length;
  const rejected = record.changes.filter((c) => c.decision === 'rejected').length;
  const src = record.source;
  return (
    <div data-testid="review-log">
      <p className="m-0 mb-3 text-[14px] text-ink2">
        {src ? `From ${prettyDate(src.date)} · ${src.kind === 'document' ? 'Documents' : 'Meeting'} · ${src.title}. ` : ''}
        {record.changes.length === 0
          ? 'This was the first version, so there was nothing to review.'
          : `${record.changes.length} proposed: ${accepted} accepted, ${rejected} rejected.`}
      </p>
      {record.changes.length > 0 && (
        <ul className="m-0 list-none p-0">
          {record.changes.map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-line-soft py-2 first:border-t-0">
              <Chip tone={c.decision === 'accepted' ? 'approved' : c.decision === 'rejected' ? 'danger' : 'muted'}>
                {c.decision === 'accepted' ? 'Accepted' : c.decision === 'rejected' ? 'Rejected' : 'Undecided'}
              </Chip>
              <span className="text-[13px] text-grey">
                {c.type === 'New' ? 'New' : c.type} · {CATEGORY[c.category] ?? c.category}
              </span>
              <span className="min-w-0 flex-1 text-[14px]">{c.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
