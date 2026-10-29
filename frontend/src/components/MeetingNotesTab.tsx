import { Input } from 'antd';
import { prettyDate, todaySgt } from '../dates';
import type { Action, Question, Register, Tracked } from '../types';
import Chip from './Chip';
import ItemTable from './ItemTable';
import Section from './Section';

const base = (status: string): Tracked => ({
  id: '',
  status,
  needs_confirmation: false,
  source_meeting: '',
  timestamp: '',
  quote: '',
});

interface Props {
  reg: Register;
  readOnly: boolean;
  onChange: (reg: Register) => void;
  onEvidence: (item: Tracked, label: string) => void;
}

/** What happened in the meetings: the summary, the action tracker and open questions.
 * The requirement specification itself stays on the Requirements tab. */
export default function MeetingNotesTab({ reg, readOnly, onChange, onEvidence }: Props) {
  const set = <K extends keyof Register>(key: K, value: Register[K]) => onChange({ ...reg, [key]: value });
  const names = Object.fromEntries(reg.meetings.map((m) => [m.id, `${prettyDate(m.date)} · ${m.title}`]));
  const latest = reg.meetings[reg.meetings.length - 1];
  const today = todaySgt();

  return (
    <div>
      <p className="m-0 mb-6 text-center text-[19px] leading-snug text-ink2">
        What was asked and who owns it. These go in the separate “Meeting notes &amp; action tracker” Word file, not in the requirement
        specification.
      </p>

      <Section title={latest ? `Summary of the latest meeting · ${names[latest.id]}` : 'Meeting summary'}>
        {readOnly ? (
          <p className="m-0 whitespace-pre-wrap text-[19px] leading-[1.45]">
            {reg.summary || <span className="text-muted">No summary yet</span>}
          </p>
        ) : (
          <Input.TextArea
            aria-label="Meeting summary"
            autoSize={{ minRows: 2, maxRows: 8 }}
            value={reg.summary}
            style={{ fontSize: 17, lineHeight: 1.45 }}
            onChange={(e) => set('summary', e.target.value)}
          />
        )}
      </Section>

      <Section title="Action tracker" count={reg.actions.length}>
        <ItemTable<Action>
          rows={reg.actions}
          readOnly={readOnly}
          addLabel="Add action"
          minWidth={1080}
          statuses={['Open', 'Done', 'Withdrawn']}
          blank={() => ({
            ...base('Open'),
            task: '',
            owner: '',
            due: '',
            due_date: '',
            raised_date: '',
            closed_meeting: '',
            closed_date: '',
            updates: [],
          })}
          cols={[
            { key: 'task', title: 'Task', area: true, width: 250 },
            { key: 'owner', title: 'Owner', width: 110 },
            {
              key: 'raised_date',
              title: 'Raised',
              width: 175,
              render: (a) => (
                <div className="text-[13px] leading-5">
                  <div>{names[a.source_meeting] ?? (prettyDate(a.raised_date) || '—')}</div>
                  {a.updates.map((u, i) => (
                    <div key={i} className="mt-1 text-[12px] text-muted">
                      ↳ {u}
                    </div>
                  ))}
                </div>
              ),
            },
            { key: 'due', title: 'Due (as said)', width: 100 },
            { key: 'due_date', title: 'Due date', width: 135, date: true },
          ]}
          rowFlag={(a) => (
            <>
              {a.status === 'Open' && a.due_date && a.due_date < today && (
                <Chip tone="danger" dot>
                  Overdue
                </Chip>
              )}
              {a.closed_date && (
                <span className="text-[12px] leading-4 text-muted">
                  Closed {prettyDate(a.closed_date)}
                  {names[a.closed_meeting] ? ` · ${names[a.closed_meeting].split(' · ')[1]}` : ''}
                </span>
              )}
            </>
          )}
          onChange={(v) => set('actions', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.task}`)}
        />
      </Section>

      <Section title="Open questions" count={reg.questions.length}>
        <ItemTable<Question>
          rows={reg.questions}
          readOnly={readOnly}
          addLabel="Add question"
          statuses={['Open', 'Answered', 'Withdrawn']}
          blank={() => ({ ...base('Open'), text: '', owner: '', answer: '' })}
          cols={[
            { key: 'text', title: 'Question', area: true },
            { key: 'owner', title: 'Owner', width: 140 },
            { key: 'answer', title: 'Answer', area: true, width: 200 },
          ]}
          onChange={(v) => set('questions', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.text}`)}
        />
      </Section>
    </div>
  );
}
