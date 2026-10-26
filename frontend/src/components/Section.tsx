import type { ReactNode } from 'react';

/** A titled block inside a tab: eyebrow title, optional count, hairline under the header. */
export default function Section({ title, count, extra, children }: { title: string; count?: number; extra?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-5 rounded-2xl border border-line bg-[#FCFBF7]">
      <header className="flex items-baseline justify-between gap-3 border-b border-line-soft px-5 py-3">
        <h3 className="eyebrow m-0" style={{ color: '#231F20' }}>{title}</h3>
        {extra ?? (count !== undefined && <span className="tnum text-[12px] text-muted">{count}</span>)}
      </header>
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}
