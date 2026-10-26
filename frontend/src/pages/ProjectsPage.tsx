import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App, Button, Form, Input, Modal, Table } from 'antd';
import { ArrowRightOutlined, PlusOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { ProjectRow } from '../types';
import Chip from '../components/Chip';

const STEPS = [
  { n: '01', title: 'Create a project', text: 'A code and a name. One project per piece of work.' },
  { n: '02', title: 'Upload a meeting', text: 'A recording, or a Teams transcript. It is turned into text on this computer.' },
  { n: '03', title: 'Review and export', text: 'Fix anything the AI got wrong, approve it, and download the Word document.' },
];

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="px-6 py-14 text-center sm:px-12">
      <p className="serif m-0 text-[28px] leading-tight text-ink">Nothing here yet.</p>
      <p className="mx-auto mb-10 mt-2 max-w-md text-muted">Start with a project, then give it a meeting.</p>
      <div className="mx-auto mb-10 grid max-w-3xl gap-6 text-left sm:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="border-t border-ink pt-3">
            <div className="eyebrow">{s.n}</div>
            <div className="mt-1 text-[15px] font-semibold">{s.title}</div>
            <div className="mt-1 text-[13px] leading-5 text-muted">{s.text}</div>
          </div>
        ))}
      </div>
      <Button type="primary" size="large" icon={<PlusOutlined />} onClick={onCreate}>
        Create your first project
      </Button>
    </div>
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

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-6">
        <div className="max-w-2xl">
          <div className="eyebrow mb-3">Workspace</div>
          <h1 className="display m-0 text-[40px] sm:text-[48px]">Projects</h1>
          <p className="serif m-0 mt-3 text-[22px] leading-snug text-muted">
            Each project keeps a single requirement document, up to date across every meeting.
          </p>
        </div>
        <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
          New project
        </Button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-line bg-white">
        {rows !== null && rows.length === 0 ? (
          <EmptyState onCreate={() => setCreating(true)} />
        ) : (
          <Table<ProjectRow>
            className="row-clickable"
            rowKey="code"
            loading={rows === null}
            dataSource={rows ?? []}
            pagination={false}
            scroll={{ x: 640 }}
            onRow={(r) => ({
              onClick: () => navigate(`/projects/${r.code}`),
              onKeyDown: (e) => e.key === 'Enter' && navigate(`/projects/${r.code}`),
              tabIndex: 0,
            })}
            columns={[
              { title: 'Code', dataIndex: 'code', width: 150, render: (v: string) => <b className="tracking-wide">{v}</b> },
              { title: 'Project', dataIndex: 'name', render: (v: string) => <span className="text-[15px] font-medium">{v}</span> },
              { title: 'Owner', dataIndex: 'owner', width: 160, render: (v: string) => v || <span className="text-muted">—</span> },
              { title: 'Meetings', dataIndex: 'meetings', width: 100, align: 'center', render: (v: number) => <span className="tnum">{v}</span> },
              {
                title: 'Document',
                width: 260,
                render: (_, r) => (
                  <span className="flex flex-wrap gap-1.5">
                    {r.version ? <Chip tone="approved" dot>v{r.version} approved</Chip> : <Chip tone="muted">Not approved yet</Chip>}
                    {r.has_draft && <Chip tone="draft" dot>Draft to review</Chip>}
                  </span>
                ),
              },
              { title: '', width: 48, align: 'right', render: () => <ArrowRightOutlined className="row-arrow" /> },
            ]}
          />
        )}
      </div>

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
            <Input placeholder="PRJ-0421" autoFocus />
          </Form.Item>
          <Form.Item name="name" label="Project name" rules={[{ required: true, message: 'Enter a project name' }]}>
            <Input placeholder="Site Diary App" />
          </Form.Item>
          <Form.Item name="owner" label="Owner (optional)">
            <Input placeholder="Who is responsible for this project" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
