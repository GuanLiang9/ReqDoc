import { Button, Popconfirm, Space, Tooltip } from 'antd';
import { CheckOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';

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

/** The status and actions for the open draft. One calm card instead of loud alerts. */
export default function DraftBar({ pending, isFirstDraft, dirty, busy, onReviewChanges, onDiscard, onUndo, onSave, onApprove }: Props) {
  const message =
    pending > 0
      ? `${pending} change${pending > 1 ? 's' : ''} from the latest meeting need${pending > 1 ? '' : 's'} your decision.`
      : isFirstDraft
        ? 'This is an AI-generated draft. Check it against the transcript, fix anything wrong, then approve.'
        : 'Every change is decided. Review the document, then approve to create the next version.';

  return (
    <section data-testid="draft-bar" className="rule-left mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-line bg-white px-6 py-4">
      <div className="min-w-[260px] flex-1">
        <div className="eyebrow" style={{ color: '#8F5A1E' }}>
          {isFirstDraft ? 'Draft · AI-generated' : 'Draft · follow-up meeting'}
        </div>
        <div className="mt-1 text-[15px] leading-6">{message}</div>
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
          <Button size="small" type="text" danger icon={<DeleteOutlined />}>Discard</Button>
        </Popconfirm>
        {dirty && <Button size="small" onClick={onUndo}>Undo my edits</Button>}
        <Button size="small" type={dirty ? 'primary' : 'default'} icon={<SaveOutlined />} disabled={!dirty} loading={busy && dirty} onClick={onSave}>
          {dirty ? 'Save edits' : 'Saved'}
        </Button>
        <Tooltip title={pending > 0 ? 'Decide every change first' : ''}>
          <Button size="small" type="primary" icon={<CheckOutlined />} disabled={pending > 0} onClick={onApprove}>
            Approve
          </Button>
        </Tooltip>
      </Space>
    </section>
  );
}
