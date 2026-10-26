import type { MouseEventHandler, ReactNode } from 'react';

export type Tone = 'neutral' | 'approved' | 'draft' | 'info' | 'warn' | 'muted' | 'danger';

const CLASS: Record<Tone, string> = {
  neutral: '',
  approved: 'chip-approved',
  draft: 'chip-draft',
  info: 'chip-info',
  warn: 'chip-warn',
  muted: 'chip-muted',
  danger: 'chip-danger',
};

/** A small status pill in the app palette. Use this instead of Ant Design's preset-colour Tag. */
export default function Chip({
  tone = 'neutral',
  dot,
  children,
  onClick,
  title,
}: {
  tone?: Tone;
  dot?: boolean;
  children: ReactNode;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  title?: string;
}) {
  const cls = `chip ${CLASS[tone]} ${dot ? 'chip-dot' : ''}`;
  return onClick ? (
    <button type="button" className={cls} onClick={onClick} title={title}>
      {children}
    </button>
  ) : (
    <span className={cls} title={title}>
      {children}
    </span>
  );
}

/** Tone for a register item status. */
export function statusTone(status: string): Tone {
  if (status === 'Agreed' || status === 'Done' || status === 'Answered' || status === 'Closed') return 'approved';
  if (status === 'Withdrawn') return 'muted';
  return 'info';
}
