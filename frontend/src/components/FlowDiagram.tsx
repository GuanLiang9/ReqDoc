import { useEffect, useRef, useState } from 'react';
import { Alert } from 'antd';
import { api } from '../api';

/** Boxes per row for the space we have: wide screens run across and down, phones go straight down. */
function columnsFor(width: number): number {
  if (width >= 1000) return 4;
  if (width >= 720) return 3;
  if (width >= 480) return 2;
  return 1;
}

/** Box-to-box workflow, drawn by the server from the to-be steps. Follows edits as they are typed. */
export default function FlowDiagram({ steps }: { steps: string[] }) {
  const box = useRef<HTMLDivElement>(null);
  const [cols, setCols] = useState(3);
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => setCols(columnsFor(el.clientWidth));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const key = JSON.stringify(steps);
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      api
        .diagramSvg(steps, cols, ctrl.signal)
        .then((s) => {
          setSvg(s);
          setError('');
        })
        .catch((e) => {
          if (e.name !== 'AbortError') setError(e.message);
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
    // `key` stands for the steps, so typing in one box does not refetch on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, cols]);

  return (
    <div ref={box}>
      {error && <Alert type="warning" showIcon message="The diagram could not be drawn" description={error} className="mb-2" />}
      <div className="flow-diagram" dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  );
}
