import { useState } from 'react';
import { App, DatePicker, Form, Input, Modal, Progress, Upload } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { uploadMeeting } from '../api';
import Chip from './Chip';

interface Props {
  open: boolean;
  code: string;
  hasMaster: boolean;
  onClose: () => void;
  onStarted: () => void;
}

const AUDIO = ['MP3', 'M4A', 'WAV', 'MP4', 'WEBM', 'OGG', 'AAC', 'FLAC'];
const TEXT = ['VTT', 'DOCX', 'TXT'];

export default function UploadModal({ open, code, hasMaster, onClose, onStarted }: Props) {
  const { message } = App.useApp();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(0);
  const [error, setError] = useState('');

  const reset = () => {
    setFile(null);
    setTitle('');
    setDate(dayjs());
    setSent(0);
    setError('');
  };

  const pick = (f: File) => {
    setFile(f);
    setError('');
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim().slice(0, 120));
    return false; // keep the file here; we upload on "Start"
  };

  const start = async () => {
    if (!file) return setError('Choose a recording or transcript first.');
    if (!title.trim()) return setError('Give the meeting a title.');
    setSending(true);
    setError('');
    try {
      await uploadMeeting(code, { file, title: title.trim(), date: date.format('YYYY-MM-DD') }, setSent);
      message.success('Uploaded. Processing has started.');
      reset();
      onStarted();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      title={
        <div>
          <div className="eyebrow mb-1">{hasMaster ? 'Follow-up meeting' : 'First meeting'}</div>
          <div className="display text-[26px]">Upload a meeting</div>
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
      <Form layout="vertical" requiredMark={false} className="pt-4">
        <Upload.Dragger
          multiple={false}
          maxCount={1}
          beforeUpload={pick}
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
              <span className="eyebrow mr-1 self-center">Recording</span>
              {AUDIO.map((t) => <Chip key={t} tone="muted">{t}</Chip>)}
            </div>
            <div className="flex flex-wrap justify-center gap-1.5">
              <span className="eyebrow mr-1 self-center">Transcript</span>
              {TEXT.map((t) => <Chip key={t} tone="muted">{t}</Chip>)}
            </div>
          </div>
        </Upload.Dragger>

        <Form.Item label="Meeting title" htmlFor="meeting-title" className="mt-5">
          <Input id="meeting-title" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="For example: Workflow review with site supervisors" disabled={sending} />
        </Form.Item>
        <Form.Item label="Meeting date" htmlFor="meeting-date">
          <DatePicker id="meeting-date" value={date} onChange={(d) => d && setDate(d)} allowClear={false} disabled={sending} />
        </Form.Item>
      </Form>

      {sending && <Progress percent={Math.round(sent * 100)} size="small" />}
      {error && (
        <div role="alert" className="mb-3 rounded-xl border border-[#E6BDB6] bg-rose px-4 py-3 text-[14px]" style={{ color: '#6E2A22' }}>
          {error}
        </div>
      )}
      <p className="serif m-0 text-[18px] leading-snug text-muted">
        {hasMaster
          ? 'This updates the existing document. You will review every change before it counts.'
          : 'This creates the first draft of the requirement document.'}{' '}
        Recordings are turned into text on this computer and then deleted. Only the text is kept.
      </p>
    </Modal>
  );
}
