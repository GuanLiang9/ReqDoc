import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Alert, App, Badge, Button, Dropdown, Skeleton, Space, Tabs, Tooltip } from 'antd';
import { DownOutlined, UploadOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { Change, ProjectDetail, Register, Tracked } from '../types';
import ApproveModal from '../components/ApproveModal';
import ChangesTab from '../components/ChangesTab';
import Chip from '../components/Chip';
import DraftBar from '../components/DraftBar';
import EvidenceDrawer, { type Evidence } from '../components/EvidenceDrawer';
import HistoryTab from '../components/HistoryTab';
import MeetingNotesTab from '../components/MeetingNotesTab';
import JobBanner from '../components/JobBanner';
import ProcessTab from '../components/ProcessTab';
import RequirementsTab from '../components/RequirementsTab';
import UploadModal from '../components/UploadModal';

const jobActive = (d: ProjectDetail | null) => !!d?.job && d.job.stage !== 'done' && d.job.stage !== 'error';

function countFlagged(reg: Register | null) {
  if (!reg) return 0;
  const groups: Tracked[][] = [reg.requirements, reg.business_rules, reg.decisions, reg.questions, reg.actions, reg.risks];
  return groups.reduce((n, g) => n + g.filter((i) => i.needs_confirmation).length, 0);
}

function nextMinor(v: string | null) {
  if (!v) return '1.0';
  const [a, b] = v.split('.').map(Number);
  return `${a}.${b + 1}`;
}

export default function ProjectPage() {
  const { code = '' } = useParams();
  const { message } = App.useApp();

  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [draft, setDraft] = useState<Register | null>(null);
  const [saved, setSaved] = useState('');
  const [master, setMaster] = useState<Register | null>(null);
  const [changes, setChanges] = useState<Change[]>([]);
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get('tab') ?? 'requirements');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [busy, setBusy] = useState(false);
  const [dismissedJob, setDismissedJob] = useState('');
  const [error, setError] = useState('');

  const dirty = !!draft && JSON.stringify(draft) !== saved;
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty;
  const wasActive = useRef(false);

  /** Load everything. Unsaved edits are never overwritten unless `force` is set. */
  const loadAll = useCallback(
    async (force = false) => {
      try {
        const d = await api.project(code);
        setDetail(d);
        setError('');
        if (d.has_draft) {
          if (force || !dirtyRef.current) {
            const [r, c] = await Promise.all([api.draft(code), api.changes(code)]);
            setDraft(r);
            setSaved(JSON.stringify(r));
            setChanges(c);
          }
          setMaster(null);
        } else {
          setDraft(null);
          setSaved('');
          setChanges([]);
          setMaster(d.master_version ? await api.register(code, 'latest') : null);
        }
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [code],
  );

  useEffect(() => {
    setDetail(null);
    setDraft(null);
    setMaster(null);
    loadAll(true);
  }, [code, loadAll]);

  // while a meeting is being processed, poll its progress; reload everything when it finishes
  useEffect(() => {
    const active = jobActive(detail);
    if (!active) {
      if (wasActive.current) {
        wasActive.current = false;
        loadAll();
      }
      return;
    }
    wasActive.current = true;
    const t = setInterval(() => api.project(code).then(setDetail).catch(() => undefined), 2000);
    return () => clearInterval(t);
  }, [detail, code, loadAll]);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirtyRef.current) e.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  const save = useCallback(async (): Promise<boolean> => {
    if (!draft) return true;
    setBusy(true);
    try {
      const res = await api.saveDraft(code, draft);
      setDraft(res);
      setSaved(JSON.stringify(res));
      return true;
    } catch (e) {
      message.error((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }, [code, draft, message]);

  const run = async (fn: () => Promise<unknown>, okText?: string) => {
    setBusy(true);
    try {
      await fn();
      if (okText) message.success(okText);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const decide = (id: string, decision: 'accepted' | 'rejected') =>
    run(async () => {
      if (dirty && !(await save())) return;
      await api.decide(code, id, decision);
      await loadAll(true);
    });

  const acceptSafe = () =>
    run(async () => {
      if (dirty && !(await save())) return;
      await api.acceptSafe(code);
      await loadAll(true);
    }, 'Accepted. Conflicts are still waiting for you.');

  const approve = (reviewer: string, major: boolean) =>
    run(async () => {
      if (dirty && !(await save())) return;
      const { version } = await api.approve(code, reviewer, major);
      setApproveOpen(false);
      setTab('requirements');
      await loadAll(true);
      message.success(`Approved as version ${version}`);
    });

  const discard = () =>
    run(async () => {
      await api.discardDraft(code);
      await loadAll(true);
    }, 'Draft discarded');

  const download = async (version: string, doc: 'spec' | 'notes' = 'spec') => {
    if (version === 'draft' && dirty && !(await save())) return;
    window.location.href = api.exportUrl(code, version, doc);
  };

  const showEvidence = (meetingId: string, timestamp: string, quote: string, label: string) =>
    setEvidence({ meetingId, timestamp, quote, label });

  const flagged = useMemo(() => countFlagged(draft), [draft]);

  if (error && !detail) {
    return <Alert type="error" showIcon message={error} action={<Link to="/">Back to projects</Link>} />;
  }
  if (!detail) return <Skeleton active paragraph={{ rows: 8 }} />;

  const reg = draft ?? master;
  const hasMaster = !!detail.master_version;
  const active = jobActive(detail);
  // A finished job that opened a draft is announced by the draft bar, so only show
  // finished jobs that did not (for example "no new information"). Errors stay until dismissed.
  const job =
    detail.job && detail.job.id !== dismissedJob && !(detail.job.stage === 'done' && detail.job.draft_created)
      ? detail.job
      : null;
  const isFirstDraft = !!draft && !hasMaster;
  const pending = detail.pending_changes;
  const latestMeeting = draft?.meetings[draft.meetings.length - 1]?.id ?? '';

  const versionItems = (doc: 'spec' | 'notes') => [
    ...(detail.has_draft ? [{ key: `${doc}:draft`, label: 'Current draft (not approved yet)' }] : []),
    ...(hasMaster ? [{ key: `${doc}:latest`, label: `Approved version v${detail.master_version}` }] : []),
  ];
  const exportItems =
    detail.has_draft || hasMaster
      ? [
          { type: 'group' as const, label: 'Requirement specification', children: versionItems('spec') },
          { type: 'group' as const, label: 'Meeting notes & action tracker', children: versionItems('notes') },
        ]
      : [];

  const uploadBlockedReason = detail.has_draft
    ? 'Approve or discard the open draft before adding another meeting'
    : active
      ? 'A meeting is still being processed'
      : '';

  const tabs = [
    {
      key: 'requirements',
      label: 'Requirements',
      children: reg && (
        <RequirementsTab
          reg={reg}
          readOnly={!draft}
          onChange={setDraft}
          onEvidence={(item, label) => showEvidence(item.source_meeting, item.timestamp, item.quote, label)}
        />
      ),
    },
    ...(draft && detail.total_changes > 0
      ? [
          {
            key: 'changes',
            label: (
              <span>
                Changes to review {pending > 0 && <Badge count={pending} size="small" className="ml-1" />}
              </span>
            ),
            children: (
              <ChangesTab
                changes={changes}
                busy={busy}
                onDecide={decide}
                onAcceptSafe={acceptSafe}
                onEvidence={(c) => showEvidence(latestMeeting, c.timestamp, c.quote, `${c.target_id || 'New item'}: ${c.text}`)}
              />
            ),
          },
        ]
      : []),
    {
      key: 'process',
      label: 'Process and diagram',
      children: reg && <ProcessTab reg={reg} readOnly={!draft} onChange={setDraft} />,
    },
    {
      key: 'notes',
      label: 'Meeting notes and actions',
      children: reg && (
        <MeetingNotesTab
          reg={reg}
          readOnly={!draft}
          onChange={setDraft}
          onEvidence={(item, label) => showEvidence(item.source_meeting, item.timestamp, item.quote, label)}
        />
      ),
    },
    { key: 'history', label: 'Versions and meetings', children: <HistoryTab detail={detail} changeLog={draft?.change_log ?? []} /> },
  ];

  const exportButton = exportItems.length > 0 && (
    <Dropdown
      menu={{
        items: exportItems,
        onClick: ({ key }) => {
          const [doc, version] = key.split(':');
          download(version, doc as 'spec' | 'notes');
        },
      }}
      trigger={['click']}
    >
      <Button aria-label="Export Word documents">
        Export <DownOutlined className="text-[11px]" />
      </Button>
    </Dropdown>
  );
  const uploadButton = (
    <Tooltip title={uploadBlockedReason}>
      <Button type="primary" icon={<UploadOutlined />} aria-label="Upload meeting" disabled={!!uploadBlockedReason} onClick={() => setUploadOpen(true)}>
        <span className="hidden sm:inline">Upload meeting</span>
      </Button>
    </Tooltip>
  );

  return (
    <div>
      {/* local nav, like the sticky sub-navigation on apple.com product pages */}
      <div className="glass sticky top-12 z-40">
        <div className="mx-auto flex h-[56px] w-full max-w-[1080px] items-center justify-between gap-3 px-5 sm:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <Link to="/" className="hidden text-[13px] text-ink2 hover:text-ink sm:inline">
              Projects
            </Link>
            <span className="hidden text-[13px] text-grey sm:inline" aria-hidden>
              ›
            </span>
            <span className="truncate text-[17px] font-semibold tracking-[-0.01em]" data-testid="local-nav-title">
              {detail.project.name}
            </span>
          </div>
          <Space size={8} className="shrink-0">
            {exportButton}
            {uploadButton}
          </Space>
        </div>
      </div>

      <section className="bg-white px-5 pb-12 pt-12 text-center sm:pt-16">
        <div className="fade-up mx-auto max-w-[900px]">
          <p className="m-0 text-[13px] font-semibold tracking-[0.04em] text-grey">{detail.project.code}</p>
          <h1 className="headline mt-2 break-words">{detail.project.name}</h1>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
            {hasMaster ? <Chip tone="approved" dot>v{detail.master_version} approved</Chip> : <Chip tone="muted">Not approved yet</Chip>}
            {detail.has_draft && <Chip tone="draft" dot>Draft to review</Chip>}
            {detail.project.owner && <span className="ml-1 text-[14px] text-ink2">Owner: {detail.project.owner}</span>}
          </div>
        </div>
      </section>

      <div className="mx-auto w-full max-w-[1080px] px-5 pb-20 pt-8 sm:px-8">
        {error && <Alert type="warning" showIcon className="mb-6" message={error} />}
        {job && <JobBanner job={job} hasMaster={hasMaster} onDismiss={() => setDismissedJob(job.id)} />}

        {draft && (
          <DraftBar
            pending={pending}
            isFirstDraft={isFirstDraft}
            dirty={dirty}
            busy={busy}
            onReviewChanges={() => setTab('changes')}
            onDiscard={discard}
            onUndo={() => loadAll(true)}
            onSave={() => save().then((ok) => ok && message.success('Saved'))}
            onApprove={() => setApproveOpen(true)}
          />
        )}

        {!reg && !active ? (
          <div className="tile px-6 py-20 text-center sm:px-12">
            <h2 className="headline text-[32px]">{job?.stage === 'error' ? 'The last upload did not work.' : 'No meeting yet.'}</h2>
            <p className="subhead mx-auto mb-8 mt-3 max-w-lg">
              {job?.stage === 'error'
                ? 'Read the message above, fix the problem and try again.'
                : 'Upload a recording or a Teams transcript and the requirement document is written for you to review.'}
            </p>
            <Button type="primary" size="large" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
              Upload the first meeting
            </Button>
          </div>
        ) : (
          reg && <Tabs activeKey={tabs.some((t) => t.key === tab) ? tab : 'requirements'} onChange={setTab} items={tabs} />
        )}
      </div>

      <UploadModal
        open={uploadOpen}
        code={code}
        hasMaster={hasMaster}
        onClose={() => setUploadOpen(false)}
        onStarted={() => {
          setUploadOpen(false);
          setDismissedJob('');
          loadAll();
        }}
      />
      <ApproveModal
        open={approveOpen}
        isFirst={!hasMaster}
        nextVersion={nextMinor(detail.master_version)}
        flagged={flagged}
        loading={busy}
        onCancel={() => setApproveOpen(false)}
        onApprove={approve}
      />
      <EvidenceDrawer code={code} evidence={evidence} onClose={() => setEvidence(null)} />
    </div>
  );
}
