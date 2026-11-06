import { useState } from 'react';
import { App, Button, DatePicker, Form, Input, Modal, Progress, Segmented, Upload } from 'antd';
import { CloseOutlined, FileTextOutlined, InboxOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { uploadDocuments, uploadMeeting } from '../api';
import Chip from './Chip';

interface Props {
  open: boolean;
  code: string;
  hasMaster: boolean;
  onClose: () => void;
  onStarted: () => void;
}

type Mode = 'meeting' | 'documents';

const AUDIO = ['MP3', 'M4A', 'WAV', 'MP4', 'WEBM', 'OGG', 'AAC', 'FLAC'];
const TEXT = ['VTT', 'DOCX', 'TXT'];
const DOCS = ['DOCX', 'PPTX', 'PDF', 'XLSX', 'TXT'];
const MAX_DOCS = 10;
const MAX_DOC_MB = 25;

const fileSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

const titleFrom = (name: string) => name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim().slice(0, 120);

/** One sheet for both kinds of source: a meeting (recording or transcript) or a pack of supporting documents. */
export default function UploadModal({ open, code, hasMaster, onClose, onStarted }: Props) {
  const { message } = App.useApp();
  const [mode, setMode] = useState<Mode>('meeting');
  const [file, setFile] = useState<File | null>(null);
  const [docs, setDocs] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(0);
  const [error, setError] = useState('');

  const reset = () => {
    setFile(null);
    setDocs([]);
    setTitle('');
    setDate(dayjs());
    setSent(0);
    setError('');
  };

  const switchMode = (m: Mode) => {
    reset();
    setMode(m);
  };

  const pickMeeting = (f: File) => {
    setFile(f);
    setError('');
    if (!title) setTitle(titleFrom(f.name));
    return false; // keep the file here; we upload on "Start"
  };

  const pickDocument = (f: File) => {
    setError('');
    if (f.size > MAX_DOC_MB * 1024 * 1024) {
      setError(`${f.name} is larger than ${MAX_DOC_MB} MB.`);
      return Upload.LIST_IGNORE;
    }
    setDocs((prev) => {
      if (prev.length >= MAX_DOCS) {
        setError(`Up to ${MAX_DOCS} documents per upload. Upload the rest afterwards.`);
        return prev;
      }
      if (prev.some((p) => p.name === f.name && p.size === f.size)) return prev;
      return [...prev, f];
    });
    // several files picked at once all arrive before a re-render, so read the latest title, not this render's
    setTitle((current) => current || titleFrom(f.name));
    return false;
  };

  const start = async () => {
    const day = date.format('YYYY-MM-DD');
    if (mode === 'meeting') {
      if (!file) return setError('Choose a recording or transcript first.');
      if (!title.trim()) return setError('Give the meeting a title.');
    } else {
      if (!docs.length) return setError('Add at least one document.');
      if (!title.trim()) return setError('Give these documents a title.');
    }
    setSending(true);
    setError('');
    try {
      if (mode === 'meeting') await uploadMeeting(code, { file: file!, title: title.trim(), date: day }, setSent);
      else await uploadDocuments(code, { files: docs, title: title.trim(), date: day }, setSent);
      message.success('Uploaded. Processing has started.');
      reset();
      onStarted();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  const isDocs = mode === 'documents';
  const stage = hasMaster ? 'Follow-up' : 'First upload';

  return (
    <Modal
      title={
        <div>
          <div className="mb-1 text-[14px] font-semibold text-blue">{stage}</div>
          <div className="headline text-[32px]">{isDocs ? 'Add documents' : 'Upload a meeting'}</div>
        </div>
      }
      open={open}
      onCancel={() => !sending && onClose()}
      onOk={start}
      okText="Start"
      cancelText="Cancel"
      confirmLoading={sending}
      maskClosable={false}
      width={620}
      destroyOnClose
    >
      <Segmented
        block
        className="mb-4 mt-3"
        value={mode}
        disabled={sending}
        onChange={(v) => switchMode(v as Mode)}
        options={[
          { value: 'meeting', label: 'Meeting' },
          { value: 'documents', label: 'Documents' },
        ]}
      />
      <Form layout="vertical" requiredMark={false}>
        {isDocs ? (
          <Upload.Dragger
            multiple
            beforeUpload={pickDocument}
            showUploadList={false}
            disabled={sending}
            accept=".docx,.pptx,.pdf,.xlsx,.txt,.md"
          >
            <p className="ant-upload-drag-icon">
              <FileTextOutlined />
            </p>
            <p className="ant-upload-text">Click or drag the documents here</p>
            <p className="m-0 px-6 text-[13px] text-grey">Scope documents, RFPs, slides, PDFs, field lists. Up to {MAX_DOCS} files.</p>
            <div className="mx-auto flex max-w-md flex-wrap justify-center gap-1.5 px-4 pb-1 pt-3">
              {DOCS.map((t) => <Chip key={t} tone="muted">{t}</Chip>)}
            </div>
          </Upload.Dragger>
        ) : (
          <Upload.Dragger
            multiple={false}
            maxCount={1}
            beforeUpload={pickMeeting}
            fileList={file ? [{ uid: '1', name: file.name, status: 'done' }] : []}
            onRemove={() => setFile(null)}
            disabled={sending}
            accept=".mp3,.m4a,.wav,.mp4,.webm,.ogg,.aac,.wma,.flac,.mkv,.mov,.vtt,.docx,.txt,.md"
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">Click or drag the meeting file here</p>
            <div className="mx-auto flex max-w-md flex-col items-center gap-2 px-4 pb-1 pt-2">
              <div className="flex flex-wrap justify-center gap-1.5">
                <span className="mr-1 self-center text-[13px] font-medium text-grey">Recording</span>
                {AUDIO.map((t) => <Chip key={t} tone="muted">{t}</Chip>)}
              </div>
              <div className="flex flex-wrap justify-center gap-1.5">
                <span className="mr-1 self-center text-[13px] font-medium text-grey">Transcript</span>
                {TEXT.map((t) => <Chip key={t} tone="muted">{t}</Chip>)}
              </div>
            </div>
          </Upload.Dragger>
        )}

        {isDocs && docs.length > 0 && (
          <ul className="m-0 mt-3 list-none p-0" aria-label="Documents to upload">
            {docs.map((d, i) => (
              <li key={`${i}-${d.name}`} className="flex items-center justify-between gap-3 rounded-xl px-3 py-1.5 hover:bg-canvas">
                <span className="flex min-w-0 items-center gap-2">
                  <FileTextOutlined className="text-blue" aria-hidden />
                  <span className="truncate text-[14px]">{d.name}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="tnum text-[12px] text-grey">{fileSize(d.size)}</span>
                  <Button
                    type="text"
                    size="small"
                    icon={<CloseOutlined />}
                    aria-label={`Remove ${d.name}`}
                    disabled={sending}
                    onClick={() => setDocs((prev) => prev.filter((_x, j) => j !== i))}
                  />
                </span>
              </li>
            ))}
          </ul>
        )}

        {isDocs ? (
          <>
            <Form.Item label="Title for these documents" htmlFor="doc-title" className="mt-5">
              <Input id="doc-title" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="For example: Vendor RFP pack" disabled={sending} />
            </Form.Item>
            <Form.Item label="Date received" htmlFor="doc-date">
              <DatePicker id="doc-date" value={date} onChange={(d) => d && setDate(d)} allowClear={false} disabled={sending} />
            </Form.Item>
          </>
        ) : (
          <>
            <Form.Item label="Meeting title" htmlFor="meeting-title" className="mt-5">
              <Input id="meeting-title" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="For example: Workflow review with site supervisors" disabled={sending} />
            </Form.Item>
            <Form.Item label="Meeting date" htmlFor="meeting-date">
              <DatePicker id="meeting-date" value={date} onChange={(d) => d && setDate(d)} allowClear={false} disabled={sending} />
            </Form.Item>
          </>
        )}
      </Form>

      {sending && <Progress percent={Math.round(sent * 100)} size="small" />}
      {error && (
        <div role="alert" className="mb-3 rounded-2xl bg-red-tint px-4 py-3 text-[14px] text-red">
          {error}
        </div>
      )}
      <p className="m-0 text-[15px] leading-snug text-ink2">
        {hasMaster
          ? 'This updates the existing document. You will review every change before it counts.'
          : 'This creates the first draft of the requirement document.'}{' '}
        {isDocs
          ? 'Only the text is read: pictures, charts and scanned PDFs are skipped. It takes about 30 seconds per page on this computer. The files are deleted after reading; only the text is kept.'
          : 'Recordings are turned into text on this computer and then deleted. Only the text is kept.'}
      </p>
    </Modal>
  );
}
