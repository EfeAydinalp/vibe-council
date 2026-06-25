import './DecisionRecord.css';

function download(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function List({ items }) {
  if (!items || items.length === 0) {
    return <p className="dr-empty">None</p>;
  }
  return (
    <ul className="dr-list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export default function DecisionRecord({ record, markdown }) {
  if (!record) {
    return null;
  }

  const slug = (record.timestamp || 'decision').replace(/[:+]/g, '-');

  return (
    <div className="stage decision-record">
      <div className="dr-header">
        <h3 className="stage-title">Decision Record</h3>
        <div className="dr-actions">
          <button
            onClick={() =>
              download(`${slug}.json`, JSON.stringify(record, null, 2), 'application/json')
            }
          >
            Download JSON
          </button>
          <button
            onClick={() =>
              download(`${slug}.md`, markdown || '', 'text/markdown')
            }
            disabled={!markdown}
          >
            Download Markdown
          </button>
        </div>
      </div>

      <div className="dr-field">
        <span className="dr-label">Decision</span>
        <p className="dr-decision">{record.decision || '—'}</p>
      </div>

      <div className="dr-field">
        <span className="dr-label">Rationale</span>
        <p>{record.rationale || '—'}</p>
      </div>

      <div className="dr-grid">
        <div className="dr-field">
          <span className="dr-label">Risks</span>
          <List items={record.risks} />
        </div>
        <div className="dr-field">
          <span className="dr-label">Open Questions</span>
          <List items={record.open_questions} />
        </div>
        <div className="dr-field">
          <span className="dr-label">Next Actions</span>
          <List items={record.next_actions} />
        </div>
      </div>

      <div className="dr-footer">
        <div className="dr-tags">
          {(record.tags || []).map((tag, i) => (
            <span key={i} className="dr-tag">
              {tag}
            </span>
          ))}
        </div>
        <span className="dr-timestamp">{record.timestamp}</span>
      </div>
    </div>
  );
}
