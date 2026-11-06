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

const isTime = (ts: string | null) => !!ts && /^\d{1,2}:\d{2}:\d{2}$/.test(ts);
const squash = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

const seconds = (ts: string | null) => {
  if (!isTime(ts)) return -1;
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

  // the line to highlight. Meetings: the last line that starts at or before the timestamp.
  // Documents: the line at that location (page, slide, heading) that holds the quote.
  let hitIndex = -1;
  if (evidence && lines) {
    if (isTime(evidence.timestamp)) {
      const target = seconds(evidence.timestamp);
      lines.forEach((l, i) => {
        if (seconds(l.timestamp) >= 0 && seconds(l.timestamp) <= target) hitIndex = i;
      });
    } else {
      const quote = squash(evidence.quote).slice(0, 40);
      const at = lines.map((l, i) => [l, i] as const).filter(([l]) => !evidence.timestamp || l.timestamp === evidence.timestamp);
      const withQuote = quote ? at.find(([l]) => squash(l.text).includes(quote)) : undefined;
      const anywhere = quote ? lines.findIndex((l) => squash(l.text).includes(quote)) : -1;
      hitIndex = withQuote ? withQuote[1] : at.length ? at[0][1] : anywhere;
    }
  }

  useEffect(() => {
    hit.current?.scrollIntoView({ block: 'center' });
  }, [lines, hitIndex]);

  return (
    <Drawer
      title={<span className="text-[17px] font-semibold">Where this came from</span>}
      width={520}
      open={!!evidence}
      onClose={onClose}
      destroyOnClose
      styles={{ body: { background: '#FFFFFF' } }}
    >
      {evidence && (
        <div data-testid="evidence">
          <p className="m-0 text-[15px] font-semibold leading-snug">{evidence.label}</p>
          {evidence.quote && (
            <blockquote className="m-0 mb-6 mt-4 text-[24px] font-semibold leading-snug tracking-[-0.015em]">
              “{evidence.quote}”
            </blockquote>
          )}
          {error && <Alert type="warning" showIcon message={error} />}
          {!lines && !error && <Spin />}
          <div className="text-[14px] leading-7">
            {lines?.map((l, i) => {
              const active = i === hitIndex;
              const located = !!l.timestamp && !isTime(l.timestamp);
              // documents: show the page / slide / section once, as a small heading, when it changes
              const newPlace = located && (i === 0 || lines[i - 1].timestamp !== l.timestamp);
              return (
                <div key={i}>
                  {newPlace && <div className="mb-1 mt-4 px-2 text-[12px] font-semibold text-grey first:mt-0">{l.timestamp}</div>}
                  <div
                    ref={active ? hit : undefined}
                    data-hit={active ? 'true' : undefined}
                    className={`rounded-lg px-2 ${active ? 'bg-blue-tint font-medium' : ''}`}
                  >
                    {l.timestamp && !located && <span className="tnum mr-2 text-[12px] text-muted">[{l.timestamp}]</span>}
                    {l.speaker && <b className="mr-1">{l.speaker}:</b>}
                    {l.text}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Drawer>
  );
}
