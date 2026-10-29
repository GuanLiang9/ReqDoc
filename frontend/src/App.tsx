import { useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes } from 'react-router-dom';
import { Tooltip } from 'antd';
import { api } from './api';
import type { Health } from './types';
import ProjectsPage from './pages/ProjectsPage';
import ProjectPage from './pages/ProjectPage';

/** What to tell the person when the AI is not ready yet (null = all good). */
function healthNotice(health: Health | null): { title: string; text: string } | null {
  if (!health) return null;
  if (!health.ollama || !health.model) return { title: 'The AI model is not ready.', text: health.detail };
  if (!health.whisper_ready) {
    return {
      title: 'First recording will be slower.',
      text: `The speech model "${health.whisper_model}" downloads once (about 500 MB for "small").`,
    };
  }
  return null;
}

function GlobalNav({ health, failed }: { health: Health | null; failed: boolean }) {
  const notice = healthNotice(health);
  const label = failed ? 'Cannot reach the ReqDoc server' : !health ? 'Checking the AI…' : notice ? notice.title : `AI ready (${health.model_name})`;
  const bad = failed || !!notice;
  return (
    <header className="glass sticky top-0 z-50">
      <nav className="mx-auto grid h-12 w-full max-w-[1080px] grid-cols-[1fr_auto_1fr] items-center px-5 sm:px-8" aria-label="Main">
        <Link to="/" className="justify-self-start text-[19px] font-semibold tracking-[-0.02em] text-ink hover:text-ink" aria-label="ReqDoc AI home">
          ReqDoc
        </Link>
        <NavLink
          to="/"
          end
          className={({ isActive }) => `text-[13px] tracking-[-0.005em] ${isActive ? 'text-ink' : 'text-ink2 hover:text-ink'}`}
        >
          Projects
        </NavLink>
        <Tooltip title={label} placement="bottomRight">
          <span className="flex items-center gap-2 justify-self-end text-[12px] text-ink2" role="status" aria-label={label}>
            <i className={`inline-block h-2 w-2 rounded-full ${failed ? 'bg-red' : !health ? 'bg-grey' : notice ? 'bg-orange' : 'bg-[#34C759]'}`} />
            <span className="hidden sm:inline">{failed ? 'Offline' : !health ? 'Checking' : bad ? 'Needs attention' : 'Ready'}</span>
          </span>
        </Tooltip>
      </nav>
    </header>
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setFailed(true));
  }, []);

  const notice = healthNotice(health);

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <GlobalNav health={health} failed={failed} />
      {notice && (
        <div role="alert" className="bg-orange-tint px-5 py-2.5 text-center text-[14px] text-orange">
          <b className="font-semibold">{notice.title}</b> {notice.text}
        </div>
      )}
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:code" element={<ProjectPage />} />
          <Route
            path="*"
            element={
              <div className="bg-white px-5 py-32 text-center">
                <p className="m-0 text-[14px] font-semibold text-orange">404</p>
                <h1 className="headline mt-2">Page not found</h1>
                <p className="subhead mt-3">The page you are looking for is not here.</p>
                <Link to="/" className="link-more mt-6 inline-block">
                  Back to projects
                </Link>
              </div>
            }
          />
        </Routes>
      </main>
      <footer className="border-t border-line-soft bg-canvas">
        <div className="mx-auto flex w-full max-w-[1080px] flex-wrap items-center justify-between gap-2 px-5 py-6 text-[12px] text-grey sm:px-8">
          <span>ReqDoc AI · Phase 1</span>
          <span>Runs on this computer. Nothing leaves it.</span>
        </div>
      </footer>
    </div>
  );
}
