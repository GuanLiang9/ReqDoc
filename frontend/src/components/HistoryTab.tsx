import { Button, Table } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { api } from '../api';
import type { ProjectDetail } from '../types';
import Chip from './Chip';
import Section from './Section';

export default function HistoryTab({ detail, changeLog }: { detail: ProjectDetail; changeLog: string[] }) {
  const code = detail.project.code;
  return (
    <div>
      <Section title="Approved versions" count={detail.versions.length}>
        <Table
          size="small"
          pagination={false}
          rowKey={(v) => v}
          dataSource={[...detail.versions].reverse()}
          locale={{ emptyText: <span className="text-muted">Nothing approved yet. Review the draft, then approve it to create v1.0.</span> }}
          columns={[
            { title: 'Version', render: (_, v) => <b className="tracking-wide">v{v}</b> },
            { title: '', render: (_, v) => (v === detail.master_version ? <Chip tone="approved" dot>current</Chip> : null) },
            {
              title: '',
              align: 'right',
              render: (_, v) => (
                <span className="inline-flex gap-2">
                  <Button size="small" icon={<DownloadOutlined />} href={api.exportUrl(code, v)} aria-label={`Download version ${v} as Word`}>
                    Spec
                  </Button>
                  <Button size="small" icon={<DownloadOutlined />} href={api.exportUrl(code, v, 'notes')} aria-label={`Download version ${v} meeting notes as Word`}>
                    Notes
                  </Button>
                </span>
              ),
            },
          ]}
        />
      </Section>
      <Section title="Meetings" count={detail.meetings.length}>
        <Table
          size="small"
          pagination={false}
          rowKey="id"
          dataSource={[...detail.meetings].reverse()}
          locale={{ emptyText: <span className="text-muted">No meetings yet</span> }}
          columns={[
            { title: 'Date', dataIndex: 'date', width: 130, render: (v: string) => <span className="tnum">{v}</span> },
            { title: 'Meeting', dataIndex: 'title' },
            { title: 'File', dataIndex: 'source_file', responsive: ['md'], render: (v: string) => <span className="text-muted">{v || '—'}</span> },
          ]}
        />
      </Section>
      {changeLog.length > 0 && (
        <Section title="What changed in the current draft" count={changeLog.length}>
          <ul className="m-0 pl-5 leading-7">
            {changeLog.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
