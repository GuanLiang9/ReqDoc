import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { App, Button, Form, Input, Modal, Skeleton } from 'antd';
import { AudioOutlined, FileWordOutlined, FolderAddOutlined, PlusOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { ProjectRow } from '../types';
import Chip from '../components/Chip';

const STEPS = [
  { icon: <FolderAddOutlined />, title: 'Create a project', text: 'A code and a name. One project for each piece of work.' },
  { icon: <AudioOutlined />, title: 'Upload a meeting', text: 'A recording or a Teams transcript. Recordings are turned into text on this computer.' },
  { icon: <FileWordOutlined />, title: 'Review and export', text: 'Fix anything the AI got wrong, approve it, and download the Word documents.' },
];

function ProjectTile({ p }: { p: ProjectRow }) {
  return (
    <Link to={`/projects/${p.code}`} className="tile tile-link flex min-h-[240px] flex-col p-7" aria-label={`${p.code} ${p.name}`}>
      <span className="text-[13px] font-semibold tracking-[0.04em] text-grey">{p.code}</span>
      <span className="mt-2 break-words text-[28px] font-semibold leading-[1.1] tracking-[-0.02em]">{p.name}</span>
      <span className="mt-4 flex flex-wrap gap-1.5">
        {p.version ? <Chip tone="approved" dot>v{p.version} approved</Chip> : <Chip tone="muted">Not approved yet</Chip>}
        {p.has_draft && <Chip tone="draft" dot>Draft to review</Chip>}
      </span>
      <span className="mt-auto flex items-end justify-between pt-6">
        <span className="text-[13px] text-grey">
          {p.meetings} meeting{p.meetings === 1 ? '' : 's'}
          {p.owner ? ` · ${p.owner}` : ''}
        </span>
        <span className="link-more text-[15px]" aria-hidden>
          Open
        </span>
      </span>
    </Link>
  );
}

export default function ProjectsPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<{ code: string; name: string; owner?: string }>();

  const load = useCallback(() => {
    api.projects().then(setRows).catch((e) => message.error(e.message));
  }, [message]);

  useEffect(load, [load]);

  const create = async () => {
    let values: { code: string; name: string; owner?: string };
    try {
      values = await form.validateFields();
    } catch {
      return; // the form already shows what to fix
    }
    setSaving(true);
    try {
      const p = await api.createProject({ ...values, owner: values.owner ?? '' });
      message.success(`Project ${p.code} created`);
      setCreating(false);
      form.resetFields();
      navigate(`/projects/${p.code}`);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const hasProjects = rows !== null && rows.length > 0;

  return (
    <div>
      {/* hero */}
      <section className="bg-white px-5 pb-16 pt-16 text-center sm:pb-24 sm:pt-24">
        <div className="fade-up mx-auto max-w-[900px]">
          <p className="m-0 text-[17px] font-semibold text-orange">New</p>
          <h1 className="hero-title mt-2">
            Meetings in.
            <br />
            Requirements out.
          </h1>
          <p className="subhead mx-auto mt-5 max-w-[640px]">
            Upload a recording. Get a requirement specification and an action tracker, ready for Word.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
            <Button type="primary" size="large" onClick={() => setCreating(true)}>
              {hasProjects ? 'New project' : 'Create your first project'}
            </Button>
            <button type="button" className="link-more" onClick={() => document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' })}>
              How it works
            </button>
          </div>
        </div>
      </section>

      {/* projects */}
      {(rows === null || hasProjects) && (
        <section className="bg-canvas px-5 py-16 sm:py-20">
          <div className="mx-auto w-full max-w-[1080px] sm:px-8">
            <h2 className="headline mb-8 text-[32px] sm:text-[40px]">Your projects</h2>
            {rows === null ? (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="tile min-h-[240px] p-7">
                    <Skeleton active paragraph={{ rows: 3 }} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {rows.map((p) => (
                  <ProjectTile key={p.code} p={p} />
                ))}
                <button
                  type="button"
                  onClick={() => setCreating(true)}
                  className="flex min-h-[240px] cursor-pointer flex-col items-center justify-center gap-3 rounded-[24px] border-2 border-dashed border-hair bg-transparent text-blue transition hover:border-blue hover:bg-blue-tint"
                  aria-label="Create a new project"
                >
                  <PlusOutlined className="text-[32px]" />
                  <span className="text-[17px]">New project</span>
                </button>
              </div>
            )}
          </div>
        </section>
      )}

      {/* how it works */}
      <section id="how" className={`px-5 py-16 sm:py-24 ${hasProjects || rows === null ? 'bg-white' : 'bg-canvas'}`}>
        <div className="mx-auto w-full max-w-[1080px] sm:px-8">
          <h2 className="headline mb-10 text-center">How it works</h2>
          <div className="grid gap-5 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <div key={s.title} className={`${hasProjects || rows === null ? 'bg-canvas' : 'bg-white'} rounded-[24px] p-8`}>
                <div className="text-[40px] leading-none text-blue" aria-hidden>
                  {s.icon}
                </div>
                <p className="m-0 mt-6 text-[13px] font-semibold text-grey">Step {i + 1}</p>
                <h3 className="m-0 mt-1 text-[24px] font-semibold leading-tight tracking-[-0.015em]">{s.title}</h3>
                <p className="m-0 mt-3 text-[17px] leading-[1.4] text-ink2">{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Modal
        title="New project"
        open={creating}
        onCancel={() => setCreating(false)}
        onOk={create}
        okText="Create project"
        confirmLoading={saving}
        destroyOnClose
        width={520}
      >
        <Form form={form} layout="vertical" requiredMark={false} className="pt-3">
          <Form.Item
            name="code"
            label="Project code"
            extra="Letters, numbers, - or _ (for example PRJ-0421)"
            rules={[
              { required: true, message: 'Enter a project code' },
              { pattern: /^[A-Za-z0-9][A-Za-z0-9_-]{1,29}$/, message: '2-30 letters, numbers, - or _' },
            ]}
          >
            <Input size="large" placeholder="PRJ-0421" autoFocus />
          </Form.Item>
          <Form.Item name="name" label="Project name" rules={[{ required: true, message: 'Enter a project name' }]}>
            <Input size="large" placeholder="Site Diary App" />
          </Form.Item>
          <Form.Item name="owner" label="Owner (optional)">
            <Input size="large" placeholder="Who is responsible for this project" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
