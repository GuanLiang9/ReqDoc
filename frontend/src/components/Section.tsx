import type { ReactNode } from 'react';

/** A titled white tile inside a tab: sentence-case title, optional count or note on the right. */
export default function Section({ title, count, extra, children }: { title: string; count?: number; extra?: ReactNode; children: ReactNode }) {
  return (
    <section className="tile mb-5 px-5 py-6 sm:px-8">
      <header className="mb-4 flex items-baseline justify-between gap-3">
        <h3 className="m-0 text-[21px] font-semibold tracking-[-0.015em] text-ink">{title}</h3>
        {extra ?? (count !== undefined && <span className="tnum text-[14px] text-grey">{count}</span>)}
      </header>
      <div>{children}</div>
    </section>
  );
}
