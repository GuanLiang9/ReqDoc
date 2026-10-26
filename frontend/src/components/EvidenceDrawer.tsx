import { useEffect, useRef, useState } from 'react';
import { Alert, Drawer, Spin } from 'antd';
import { api } from '../api';
import type { TranscriptLine } from '../types';

export interface Evidence {
  meetingId: string;
  timestamp: string;
  quote: string;
  label: string;
}

const seconds = (ts: string | null) => {
  if (!ts) return -1;
  const [h, m, s] = ts.split(':').map(Number);
  return h * 3600 + m * 60 + s;
};

/** Shows the transcript around the words an item came from, so a reviewer can check it. */
export default function EvidenceDrawer({ code, evidence, onClose }: { code: string; evidence: Evidence | null; onClose: () => void }) {
  const [lines, setLines] = useState<TranscriptLine[] | null>(null);
  const [error, setError] = useState('');
  const hit = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!evidence) return;
    setLines(null);
    setError('');
    api
      .transcript(code, evidence.meetingId)
      .then(setLines)
      .catch((e) => setError(e.message));
  }, [code, evidence]);

  // the line to highlight: the last line that starts at or before the timestamp
  const target = evidence ? seconds(evidence.timestamp) : -1;
  let hitIndex = -1;
  lines?.forEach((l, i) => {
    if (target >= 0 && seconds(l.timestamp) <= target) hitIndex = i;
  });

  useEffect(() => {
    hit.current?.scrollIntoView({ block: 'center' });
  }, [lines, hitIndex]);

  return (
    <Drawer
      title={<span className="eyebrow">Where this came from</span>}
      width={520}
      open={!!evidence}
      onClose={onClose}
      destroyOnClose
      styles={{ body: { background: '#FCFBF7' } }}
    >
      {evidence && (
        <div data-testid="evidence">
          <p className="m-0 text-[15px] font-semibold leading-snug">{evidence.label}</p>
          {evidence.quote && (
            <blockquote className="serif m-0 mb-6 mt-4 border-l-[3px] border-accent pl-4 text-[22px] leading-snug">
              “{evidence.quote}”
            </blockquote>
          )}
          {error && <Alert type="warning" showIcon message={error} />}
          {!lines && !error && <Spin />}
          <div className="text-[14px] leading-7">
            {lines?.map((l, i) => {
              const active = i === hitIndex;
              return (
                <div
                  key={i}
                  ref={active ? hit : undefined}
                  data-hit={active ? 'true' : undefined}
                  className={`rounded-md px-2 ${active ? 'bg-sand font-medium' : ''}`}
                >
                  {l.timestamp && <span className="tnum mr-2 text-[12px] text-muted">[{l.timestamp}]</span>}
                  {l.speaker && <b className="mr-1">{l.speaker}:</b>}
                  {l.text}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Drawer>
  );
}
