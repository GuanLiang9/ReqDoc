import { useEffect, useState } from 'react';
import { Input, Modal, Switch } from 'antd';

const KEY = 'reqdoc.reviewer';

interface Props {
  open: boolean;
  nextVersion: string;
  isFirst: boolean;
  flagged: number;
  loading: boolean;
  onCancel: () => void;
  onApprove: (reviewer: string, major: boolean) => void;
}

export default function ApproveModal({ open, nextVersion, isFirst, flagged, loading, onCancel, onApprove }: Props) {
  const [reviewer, setReviewer] = useState('');
  const [major, setMajor] = useState(false);

  useEffect(() => {
    if (!open) return;
    try {
      setReviewer(localStorage.getItem(KEY) ?? '');
    } catch {
      /* storage may be blocked */
    }
  }, [open]);

  const submit = () => {
    try {
      localStorage.setItem(KEY, reviewer.trim());
    } catch {
      /* storage may be blocked */
    }
    onApprove(reviewer.trim(), major);
  };

  const version = isFirst ? '1.0' : major ? `${parseInt(nextVersion, 10) + 1}.0` : nextVersion;

  return (
    <Modal
      title={
        <div>
          <div className="mb-1 text-[14px] font-semibold text-blue">Approve</div>
          <div className="headline text-[32px]">Version {version}</div>
        </div>
      }
      open={open}
      onCancel={onCancel}
      onOk={submit}
      okText="Approve"
      okButtonProps={{ disabled: !reviewer.trim() }}
      confirmLoading={loading}
      destroyOnClose
      width={520}
    >
      <p className="m-0 mb-5 mt-3 text-[17px] leading-snug text-ink2">
        Approving makes this the agreed document. The AI draft label is removed, your name is recorded as the reviewer, and earlier versions stay available.
      </p>
      {flagged > 0 && (
        <div className="mb-5 rounded-2xl bg-orange-tint px-4 py-3 text-[14px] text-orange">
          {flagged} item{flagged > 1 ? 's are' : ' is'} still marked “to confirm”. You can approve anyway, but check {flagged > 1 ? 'them' : 'it'} against the transcript first.
        </div>
      )}
      <label className="mb-2 block text-[14px] font-medium" htmlFor="reviewer">Reviewer name</label>
      <Input id="reviewer" size="large" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Your name" autoFocus onPressEnter={() => reviewer.trim() && submit()} />
      {!isFirst && (
        <div className="mt-5 flex items-center gap-3">
          <Switch checked={major} onChange={setMajor} aria-label="Major revision" />
          <span className="text-[14px]">Major revision (the version goes up to the next whole number)</span>
        </div>
      )}
    </Modal>
  );
}
