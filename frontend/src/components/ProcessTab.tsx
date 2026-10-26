import type { Register } from '../types';
import Mermaid from './Mermaid';
import Section from './Section';
import StringList from './StringList';

interface Props {
  reg: Register;
  readOnly: boolean;
  onChange: (reg: Register) => void;
}

export default function ProcessTab({ reg, readOnly, onChange }: Props) {
  return (
    <div>
      <div className="grid gap-5 md:grid-cols-2">
        <Section title="Current process (as-is)" count={reg.asis_steps.length}>
          <StringList
            ordered
            items={reg.asis_steps}
            readOnly={readOnly}
            placeholder="A step, or a pain point"
            onChange={(v) => onChange({ ...reg, asis_steps: v })}
          />
        </Section>
        <Section title="Proposed process (to-be)" count={reg.tobe_steps.length}>
          <StringList
            ordered
            items={reg.tobe_steps}
            readOnly={readOnly}
            placeholder="Who does what"
            onChange={(v) => onChange({ ...reg, tobe_steps: v })}
          />
        </Section>
      </div>
      <Section
        title="Workflow diagram"
        extra={!readOnly && <span className="text-[12px] text-muted">Drawn from the to-be steps. Save to refresh.</span>}
      >
        {reg.diagram_mermaid ? (
          <Mermaid source={reg.diagram_mermaid} />
        ) : (
          <span className="text-muted">No to-be process was described, so there is no diagram.</span>
        )}
      </Section>
    </div>
  );
}
