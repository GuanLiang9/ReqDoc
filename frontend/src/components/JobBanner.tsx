import { Button, Progress, Steps } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import type { Job } from '../types';

const LABEL: Record<string, string> = {
  transcribing: 'Transcribing the recording',
  extracting: 'Finding requirements',
  comparing: 'Comparing with the document',
};

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

function Dismiss({ onClick }: { onClick: () => void }) {
  return <Button type="text" size="small" aria-label="Dismiss" icon={<CloseOutlined />} onClick={onClick} />;
}

export default function JobBanner({ job, hasMaster, onDismiss }: { job: Job; hasMaster: boolean; onDismiss: () => void }) {
  if (job.stage === 'error') {
    return (
      <section data-testid="job-banner" role="alert" className="mb-6 rounded-[24px] bg-red-tint px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[14px] font-semibold text-red">Could not process</div>
            <div className="mt-1 text-[17px] font-semibold">{job.title}</div>
            <p className="m-0 mt-2 text-[#7A1014]">{job.error}</p>
          </div>
          <Dismiss onClick={onDismiss} />
        </div>
      </section>
    );
  }
  if (job.stage === 'done') {
    return (
      <section data-testid="job-banner" className="tile mb-6 px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[14px] font-semibold text-green">Finished</div>
            <div className="mt-1 text-[17px] font-semibold">{job.title}</div>
            <p className="m-0 mt-1 text-muted">{job.result}</p>
          </div>
          <Dismiss onClick={onDismiss} />
        </div>
      </section>
    );
  }

  const steps = [job.is_recording && 'transcribing', 'extracting', hasMaster && 'comparing'].filter(Boolean) as string[];
  const current = Math.max(steps.indexOf(job.stage), 0);
  return (
    <section data-testid="job-banner" aria-live="polite" className="tile mb-6 px-6 py-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-[14px] font-semibold text-blue">Processing</div>
          <div className="mt-1 text-[17px] font-semibold">{job.title}</div>
        </div>
        <span className="tnum text-[13px] text-muted">{clock(job.elapsed)} elapsed</span>
      </div>
      <div className="mt-5">
        <Steps size="small" current={current} items={steps.map((s) => ({ title: LABEL[s] }))} />
      </div>
      <div className="mt-4">
        <Progress percent={Math.round(job.progress * 100)} size="small" showInfo={false} />
        <div className="mt-1 text-[13px] text-muted">
          {job.stage === 'queued' ? 'Waiting for the previous meeting to finish' : job.message}
        </div>
      </div>
      <p className="m-0 mt-4 text-[14px] leading-snug text-ink2">
        This runs on your computer, so it takes a few minutes. A one hour meeting can take 15 to 30. You can leave this page open or come back later.
      </p>
    </section>
  );
}
