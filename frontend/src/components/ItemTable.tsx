import type { ReactNode } from 'react';
import { Button, DatePicker, Input, Select, Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { prettyDate } from '../dates';
import type { Tracked } from '../types';
import Chip, { statusTone } from './Chip';

export interface Col<T> {
  key: keyof T & string;
  title: string;
  width?: number;
  /** a dropdown instead of free text */
  options?: string[];
  /** a growing multi-line box (use for the main sentence of an item) */
  area?: boolean;
  /** a calendar date, stored as YYYY-MM-DD */
  date?: boolean;
  /** a display computed from the whole row, read-only in every mode */
  render?: (row: T) => ReactNode;
}

interface Props<T extends Tracked> {
  rows: T[];
  cols: Col<T>[];
  statuses: string[];
  blank: () => T;
  readOnly: boolean;
  addLabel: string;
  onChange: (rows: T[]) => void;
  onEvidence: (row: T) => void;
  /** extra note shown under the status of a row (for example "Overdue") */
  rowFlag?: (row: T) => ReactNode;
  /** table width below which it scrolls sideways */
  minWidth?: number;
}

/** A spreadsheet-like table for one kind of register item. Rows are never deleted once saved: set Status to Withdrawn. */
export default function ItemTable<T extends Tracked>({
  rows,
  cols,
  statuses,
  blank,
  readOnly,
  addLabel,
  onChange,
  onEvidence,
  rowFlag,
  minWidth = 900,
}: Props<T>) {
  const patch = (index: number, change: Partial<T>) =>
    onChange(rows.map((r, i) => (i === index ? { ...r, ...change } : r)));

  const columns: ColumnsType<T> = [
    {
      title: 'ID',
      width: 84,
      render: (_, r) => (r.id ? <b className="tracking-wide">{r.id}</b> : <Chip tone="draft">new</Chip>),
    },
    ...cols.map((c) => ({
      title: c.title,
      width: c.width,
      render: (_: unknown, r: T, i: number) => {
        if (c.render) return c.render(r);
        const value = String(r[c.key] ?? '');
        if (c.date) {
          if (readOnly) return <span className="whitespace-nowrap">{prettyDate(value) || '—'}</span>;
          return (
            <DatePicker
              size="small"
              variant="borderless"
              className="w-full"
              format="D MMM YYYY"
              aria-label={`${c.title} ${r.id || 'new row'}`}
              value={value ? dayjs(value) : null}
              onChange={(d) => patch(i, { [c.key]: d ? d.format('YYYY-MM-DD') : '' } as Partial<T>)}
            />
          );
        }
        if (readOnly) return <span className="whitespace-pre-wrap">{value || '—'}</span>;
        if (c.options) {
          return (
            <Select
              size="small"
              variant="borderless"
              className="w-full"
              value={value}
              options={c.options.map((o) => ({ value: o, label: o }))}
              onChange={(v) => patch(i, { [c.key]: v } as Partial<T>)}
            />
          );
        }
        const Box = c.area ? Input.TextArea : Input;
        return (
          <Box
            aria-label={`${c.title} ${r.id || 'new row'}`}
            variant="borderless"
            className="cell-input"
            value={value}
            {...(c.area ? { autoSize: { minRows: 1, maxRows: 6 } } : {})}
            onChange={(e) => patch(i, { [c.key]: e.target.value } as Partial<T>)}
          />
        );
      },
    })),
    {
      title: 'Status',
      width: 120,
      render: (_, r, i) => (
        <span className="flex flex-col items-start gap-1">
          {readOnly ? (
            <Chip tone={statusTone(r.status)}>{r.status}</Chip>
          ) : (
            <Select
              size="small"
              variant="borderless"
              className="w-full"
              value={r.status}
              options={statuses.map((s) => ({ value: s, label: s }))}
              onChange={(v) => patch(i, { status: v } as Partial<T>)}
            />
          )}
          {rowFlag?.(r)}
        </span>
      ),
    },
    {
      title: 'Evidence',
      width: 118,
      render: (_, r) => (
        <span className="flex flex-col items-start gap-1">
          {r.timestamp || r.quote ? (
            <Button type="link" size="small" className="p-0" onClick={() => onEvidence(r)}>
              {r.timestamp ? `[${r.timestamp}]` : 'View'}
            </Button>
          ) : (
            <span className="text-muted">—</span>
          )}
          {r.needs_confirmation && (
            <Chip
              tone="warn"
              title={
                readOnly
                  ? 'The AI could not find these exact words in the transcript'
                  : 'The AI could not find these exact words in the transcript. Check it, then click to clear the flag.'
              }
              onClick={readOnly ? undefined : () => onChange(rows.map((x) => (x === r ? { ...x, needs_confirmation: false } : x)))}
            >
              ⚠ to confirm
            </Chip>
          )}
        </span>
      ),
    },
  ];

  if (!readOnly) {
    columns.push({
      title: '',
      width: 44,
      render: (_, r, i) =>
        r.id === '' ? (
          <Tooltip title="Remove this new row">
            <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => onChange(rows.filter((_x, j) => j !== i))} />
          </Tooltip>
        ) : null,
    });
  }

  return (
    <div>
      <Table<T>
        size="small"
        rowKey={(r, i) => r.id || `new-${i}`}
        columns={columns}
        dataSource={rows}
        pagination={false}
        scroll={{ x: minWidth }}
        locale={{ emptyText: <span className="text-muted">Not discussed in this meeting</span> }}
      />
      {!readOnly && (
        <Button type="dashed" size="small" icon={<PlusOutlined />} className="mt-2" onClick={() => onChange([...rows, blank()])}>
          {addLabel}
        </Button>
      )}
    </div>
  );
}
