import { useEffect, useState } from 'react';
import { Link, Route, Routes } from 'react-router-dom';
import { api } from './api';
import type { Health } from './types';
import ProjectsPage from './pages/ProjectsPage';
import ProjectPage from './pages/ProjectPage';

function HealthBanner() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  if (!health) return null;
  let text: string | null = null;
  let title = '';
  if (!health.ollama || !health.model) {
    title = 'The AI model is not ready.';
    text = health.detail;
  } else if (!health.whisper_ready) {
    title = 'First recording will be slower.';
    text = `The speech model "${health.whisper_model}" downloads once (about 500 MB for "small").`;
  }
  if (!text) return null;
  return (
    <div role="status" className="border-b border-line bg-sand px-4 py-2 text-center text-[13px]" style={{ color: '#7A4A12' }}>
      <b>{title}</b> {text}
    </div>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-4 py-5 sm:px-12">
          <Link to="/" className="flex items-center gap-3 text-ink" aria-label="ReqDoc AI home">
            <span className="text-[18px] font-black tracking-[0.06em]">REQDOC</span>
            <span className="inline-block h-[7px] w-[7px] rounded-full bg-accent" />
          </Link>
          <span className="eyebrow hidden sm:inline">Meeting recordings to requirement documents</span>
        </div>
      </header>
      <HealthBanner />
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 pb-16 pt-10 sm:px-12">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:code" element={<ProjectPage />} />
          <Route
            path="*"
            element={
              <div className="py-24 text-center">
                <div className="eyebrow">404</div>
                <h1 className="display m-0 mt-2 text-4xl">Page not found</h1>
                <Link to="/" className="mt-4 inline-block">Back to projects</Link>
              </div>
            }
          />
        </Routes>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-4 py-5 sm:px-12">
          <span className="eyebrow">ReqDoc AI · Phase 1</span>
          <span className="eyebrow">Runs on this computer. Nothing leaves it.</span>
        </div>
      </footer>
    </div>
  );
}
