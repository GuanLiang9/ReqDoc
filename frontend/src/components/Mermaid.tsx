import { useEffect, useRef, useState } from 'react';
import { Alert } from 'antd';

/** Draws a Mermaid flowchart. The library is loaded on demand so the rest of the app stays small. */
export default function Mermaid({ source }: { source: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          themeVariables: {
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '14px',
            primaryColor: '#FFFFFF',
            primaryBorderColor: '#231F20',
            primaryTextColor: '#231F20',
            secondaryColor: '#F6EADB',
            tertiaryColor: '#F2EFE6',
            lineColor: '#231F20',
            edgeLabelBackground: '#FCFBF7',
          },
        });
        const { svg } = await mermaid.render(`m${Math.random().toString(36).slice(2)}`, source);
        if (!cancelled && box.current) {
          box.current.innerHTML = svg;
          setError('');
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <>
      {error && <Alert type="warning" showIcon message="The diagram could not be drawn" description={error} className="mb-2" />}
      <div ref={box} className="overflow-auto" />
    </>
  );
}
