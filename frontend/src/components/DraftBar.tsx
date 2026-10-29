import { Button, Popconfirm, Space, Tooltip } from 'antd';
import { InfoCircleFilled } from '@ant-design/icons';

interface Props {
  pending: number;
  isFirstDraft: boolean;
  dirty: boolean;
  busy: boolean;
  onReviewChanges: () => void;
  onDiscard: () => void;
  onUndo: () => void;
  onSave: () => void;
  onApprove: () => void;
}

/** The status and actions for the open draft: one calm tile, the primary action is the blue pill. */
export default function DraftBar({ pending, isFirstDraft, dirty, busy, onReviewChanges, onDiscard, onUndo, onSave, onApprove }: Props) {
  const message =
    pending > 0
      ? `${pending} change${pending > 1 ? 's' : ''} from the latest meeting need${pending > 1 ? '' : 's'} your decision.`
      : isFirstDraft
        ? 'This is an AI-generated draft. Check it against the transcript, fix anything wrong, then approve.'
        : 'Every change is decided. Review the document, then approve to create the next version.';

  return (
    <section data-testid="draft-bar" className="tile mb-6 flex flex-wrap items-center justify-between gap-4 px-6 py-5">
      <div className="flex min-w-[260px] flex-1 items-start gap-3">
        <InfoCircleFilled className="mt-[3px] text-[20px] text-blue" aria-hidden />
        <div>
          <div className="text-[17px] font-semibold tracking-[-0.01em]">{isFirstDraft ? 'Draft · AI-generated' : 'Draft · follow-up meeting'}</div>
          <div className="mt-0.5 text-[15px] leading-6 text-ink2">{message}</div>
        </div>
      </div>
      <Space wrap size={8}>
        {pending > 0 && <Button size="small" onClick={onReviewChanges}>Review changes</Button>}
        <Popconfirm
          title="Discard this draft?"
          description={isFirstDraft ? 'You will need to upload the meeting again.' : 'The changes from the latest meeting are dropped. The approved document is not touched.'}
          okText="Discard"
          okButtonProps={{ danger: true }}
          onConfirm={onDiscard}
        >
          <Button size="small" type="text" danger>Discard</Button>
        </Popconfirm>
        {dirty && <Button size="small" onClick={onUndo}>Undo my edits</Button>}
        <Button size="small" type={dirty ? 'primary' : 'default'} disabled={!dirty} loading={busy && dirty} onClick={onSave}>
          {dirty ? 'Save edits' : 'Saved'}
        </Button>
        <Tooltip title={pending > 0 ? 'Decide every change first' : ''}>
          <Button size="small" type="primary" disabled={pending > 0} onClick={onApprove}>
            Approve
          </Button>
        </Tooltip>
      </Space>
    </section>
  );
}
