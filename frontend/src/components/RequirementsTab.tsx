import { Button, Input, Table } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { Action, Decision, Question, Register, Requirement, Risk, Rule, StringListKey, Tracked } from '../types';
import ItemTable from './ItemTable';
import Section from './Section';
import StringList from './StringList';

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

export default function RequirementsTab({ reg, readOnly, onChange, onEvidence }: Props) {
  const set = <K extends keyof Register>(key: K, value: Register[K]) => onChange({ ...reg, [key]: value });
  const list = (key: StringListKey, placeholder: string) => (
    <StringList items={reg[key]} readOnly={readOnly} placeholder={placeholder} onChange={(v) => set(key, v)} />
  );

  return (
    <div>
      <Section title="Meeting summary">
        {readOnly ? (
          <p className="serif m-0 whitespace-pre-wrap text-[22px] leading-snug">
            {reg.summary || <span className="text-muted">Not discussed in this meeting</span>}
          </p>
        ) : (
          <Input.TextArea
            aria-label="Meeting summary"
            autoSize={{ minRows: 2, maxRows: 8 }}
            value={reg.summary}
            style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontSize: 20, lineHeight: 1.35 }}
            onChange={(e) => set('summary', e.target.value)}
          />
        )}
      </Section>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Business objectives" count={reg.objectives.length}>
          {list('objectives', 'Why this is needed')}
        </Section>
        <Section title="Stakeholders and users" count={reg.stakeholders.length}>
          {list('stakeholders', 'Role: what they do')}
        </Section>
        <Section title="In scope" count={reg.scope_in.length}>
          {list('scope_in', 'Included')}
        </Section>
        <Section title="Out of scope" count={reg.scope_out.length}>
          {list('scope_out', 'Not included')}
        </Section>
      </div>
      <Section title="Deferred to a later phase" count={reg.scope_deferred.length}>
        {list('scope_deferred', 'Postponed item')}
      </Section>

      <Section title="Requirements (functional and non-functional)" count={reg.requirements.length}>
        <ItemTable<Requirement>
          rows={reg.requirements}
          readOnly={readOnly}
          addLabel="Add requirement"
          statuses={['Proposed', 'Agreed', 'Withdrawn']}
          blank={() => ({ ...base('Proposed'), text: '', kind: 'FR', priority: 'Not stated', requested_by: '' })}
          cols={[
            { key: 'text', title: 'Requirement', area: true },
            { key: 'kind', title: 'Type', width: 90, options: ['FR', 'NFR'] },
            { key: 'priority', title: 'Priority', width: 120, options: ['Must', 'Should', 'Could', 'Not stated'] },
            { key: 'requested_by', title: 'Requested by', width: 140 },
          ]}
          onChange={(v) => set('requirements', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.text}`)}
        />
      </Section>

      <Section title="Business rules" count={reg.business_rules.length}>
        <ItemTable<Rule>
          rows={reg.business_rules}
          readOnly={readOnly}
          addLabel="Add rule"
          statuses={['Proposed', 'Agreed', 'Withdrawn']}
          blank={() => ({ ...base('Proposed'), text: '' })}
          cols={[{ key: 'text', title: 'Rule', area: true }]}
          onChange={(v) => set('business_rules', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.text}`)}
        />
      </Section>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Data and fields" count={reg.data_fields.length}>
          {list('data_fields', 'Field, form or report')}
        </Section>
        <Section title="Assumptions and constraints" count={reg.assumptions.length}>
          {list('assumptions', 'Assumption or constraint')}
        </Section>
      </div>

      <Section title="Decisions made" count={reg.decisions.length}>
        <ItemTable<Decision>
          rows={reg.decisions}
          readOnly={readOnly}
          addLabel="Add decision"
          statuses={['Agreed', 'Proposed', 'Withdrawn']}
          blank={() => ({ ...base('Agreed'), text: '', decided_by: '' })}
          cols={[
            { key: 'text', title: 'Decision', area: true },
            { key: 'decided_by', title: 'Decided by', width: 140 },
          ]}
          onChange={(v) => set('decisions', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.text}`)}
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

      <Section title="Action items" count={reg.actions.length}>
        <ItemTable<Action>
          rows={reg.actions}
          readOnly={readOnly}
          addLabel="Add action"
          statuses={['Open', 'Done', 'Withdrawn']}
          blank={() => ({ ...base('Open'), task: '', owner: '', due: '' })}
          cols={[
            { key: 'task', title: 'Task', area: true },
            { key: 'owner', title: 'Owner', width: 140 },
            { key: 'due', title: 'Due', width: 120 },
          ]}
          onChange={(v) => set('actions', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.task}`)}
        />
      </Section>

      <Section title="Risks" count={reg.risks.length}>
        <ItemTable<Risk>
          rows={reg.risks}
          readOnly={readOnly}
          addLabel="Add risk"
          statuses={['Open', 'Closed', 'Withdrawn']}
          blank={() => ({ ...base('Open'), text: '' })}
          cols={[{ key: 'text', title: 'Risk', area: true }]}
          onChange={(v) => set('risks', v)}
          onEvidence={(r) => onEvidence(r, `${r.id}: ${r.text}`)}
        />
      </Section>

      <Section title="Glossary" count={reg.glossary.length}>
        <Table
          size="small"
          pagination={false}
          rowKey={(_r, i) => String(i)}
          dataSource={reg.glossary}
          locale={{ emptyText: <span className="text-muted">Not discussed in this meeting</span> }}
          columns={[
            {
              title: 'Term',
              width: 180,
              render: (_, g, i) =>
                readOnly ? g.term : (
                  <Input variant="borderless" value={g.term} onChange={(e) => set('glossary', reg.glossary.map((x, j) => (j === i ? { ...x, term: e.target.value } : x)))} />
                ),
            },
            {
              title: 'Meaning',
              render: (_, g, i) =>
                readOnly ? g.meaning : (
                  <Input variant="borderless" value={g.meaning} onChange={(e) => set('glossary', reg.glossary.map((x, j) => (j === i ? { ...x, meaning: e.target.value } : x)))} />
                ),
            },
            ...(readOnly
              ? []
              : [{ title: '', width: 44, render: (_: unknown, _g: unknown, i: number) => <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => set('glossary', reg.glossary.filter((_x, j) => j !== i))} /> }]),
          ]}
        />
        {!readOnly && (
          <Button type="dashed" size="small" icon={<PlusOutlined />} className="mt-2" onClick={() => set('glossary', [...reg.glossary, { term: '', meaning: '' }])}>
            Add term
          </Button>
        )}
      </Section>
    </div>
  );
}
