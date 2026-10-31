import { useState, type ChangeEvent } from "react";
import { assessESGDocument } from "../api/documentAssessment";
import type { DocumentAssessmentResponse, ESGFinding } from "../types/documentAssessment";
import "./DocumentAssessmentPanel.css";

const PILLARS = ["Environmental", "Social", "Governance"] as const;
type Pillar = (typeof PILLARS)[number];

function FindingCard({ finding }: { finding: ESGFinding }) {
  return (
    <article className="doc-finding">
      <div className="doc-finding-heading">
        <div><span className="doc-id">{finding.id}</span><strong>{finding.name}</strong></div>
        <span className={`doc-status status-${finding.status}`}>{finding.status.replaceAll("_", " ")}</span>
      </div>
      <p className="doc-note">{finding.assessment_note}</p>
      {finding.evidence.length > 0 ? (
        <div className="doc-evidence-list">
          {finding.evidence.map((item, i) => (
            <blockquote key={`${item.page}-${i}`} className="doc-evidence">
              <p>“{item.excerpt}”</p>
              <footer>Page {item.page} · Matched: {item.matched_terms.join(", ")}</footer>
            </blockquote>
          ))}
        </div>
      ) : <p className="doc-muted">No matching passage found in extracted text.</p>}
      {finding.related_references.length > 0 && (
        <details className="doc-references">
          <summary>Related ESG knowledge-base references ({finding.related_references.length})</summary>
          {finding.related_references.map((ref, i) => (
            <div key={`${ref.source}-${i}`} className="doc-reference">
              <strong>{ref.standard} · {ref.source}</strong>
              <p>{ref.reference_text}</p>
            </div>
          ))}
        </details>
      )}
    </article>
  );
}

export function DocumentAssessmentPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<DocumentAssessmentResponse | null>(null);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setReport(null);
    setError(null);
  };

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      setReport(await assessESGDocument(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to assess document");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel doc-assessment">
      <div className="panel-header"><h2>Company ESG Document Review</h2></div>
      <div className="panel-body">
        <p className="doc-intro">Upload a company PDF to identify ESG topics disclosed in the document, with page-level evidence and related knowledge-base references.</p>
        <label className="doc-upload" htmlFor="esg-company-pdf">
          <span className="doc-upload-icon">↑</span>
          <strong>{file ? file.name : "Choose a company PDF"}</strong>
          <small>PDF only · Maximum 20 MB</small>
          <input id="esg-company-pdf" type="file" accept="application/pdf,.pdf" onChange={onFileChange} disabled={busy} />
        </label>
        {file && <button type="button" className="btn btn-primary doc-submit" onClick={submit} disabled={busy}>
          {busy ? "Assessing document…" : "Assess ESG disclosures"}
        </button>}
        {error && <div className="error-banner doc-error" role="alert">{error}</div>}
        {busy && <div className="doc-loading"><span className="spinner" /> Extracting pages and reviewing ESG topics…</div>}

        {report && (
          <div className="doc-report">
            <div className="doc-report-top">
              <div><h3>{report.document.filename}</h3><p>{report.document.page_count} pages · {report.summary.topic_count} topics reviewed</p></div>
              <span className="doc-complete">Review complete</span>
            </div>
            <div className="doc-counts">
              <div><strong>{report.summary.counts.addressed}</strong><span>Multiple matches</span></div>
              <div><strong>{report.summary.counts.partial_evidence}</strong><span>Some evidence</span></div>
              <div><strong>{report.summary.counts.not_found}</strong><span>Not found</span></div>
            </div>
            {PILLARS.map((pillar: Pillar) => (
              <section className="doc-pillar" key={pillar}>
                <h3>{pillar}</h3>
                {report.pillars[pillar].map((finding) => <FindingCard key={finding.id} finding={finding} />)}
              </section>
            ))}
            <details className="doc-method">
              <summary>Methodology and limitations</summary>
              <p>{report.methodology}</p>
              <ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </details>
          </div>
        )}
      </div>
    </section>
  );
}
