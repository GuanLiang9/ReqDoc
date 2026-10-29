import { Button, Input } from 'antd';
import { ArrowDownOutlined, ArrowUpOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons';

interface Props {
  items: string[];
  onChange: (items: string[]) => void;
  readOnly: boolean;
  placeholder: string;
  /** show step numbers and up/down buttons */
  ordered?: boolean;
}

/** An editable list of short sentences (objectives, scope, process steps...). */
export default function StringList({ items, onChange, readOnly, placeholder, ordered }: Props) {
  const move = (i: number, by: number) => {
    const next = [...items];
    [next[i], next[i + by]] = [next[i + by], next[i]];
    onChange(next);
  };

  if (readOnly) {
    if (!items.length) return <span className="text-muted">Not discussed in this meeting</span>;
    const List = ordered ? 'ol' : 'ul';
    return (
      <List className="m-0 pl-5">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </List>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {items.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          {ordered && <span className="tnum w-6 text-right text-muted">{i + 1}.</span>}
          <Input
            aria-label={`${placeholder} ${i + 1}`}
            value={s}
            placeholder={placeholder}
            onChange={(e) => onChange(items.map((x, j) => (j === i ? e.target.value : x)))}
          />
          {ordered && (
            <>
              <Button type="text" size="small" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(i, -1)} />
              <Button type="text" size="small" icon={<ArrowDownOutlined />} disabled={i === items.length - 1} onClick={() => move(i, 1)} />
            </>
          )}
          <Button type="text" size="small" danger icon={<CloseOutlined />} onClick={() => onChange(items.filter((_x, j) => j !== i))} />
        </div>
      ))}
      <div>
        <Button type="text" size="small" icon={<PlusOutlined />} className="!text-blue" onClick={() => onChange([...items, ''])}>
          Add
        </Button>
      </div>
    </div>
  );
}
