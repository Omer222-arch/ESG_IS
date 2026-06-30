import type { AnalyzeResponse, ProgressEvent } from "../types";
import { EsgContextList } from "./EsgContextList";
import { HumanReviewPanel } from "./HumanReviewPanel";
import { ScoreCard } from "./ScoreCard";
import { SqlResultsTable } from "./SqlResultsTable";
import { StatusBadge } from "./StatusBadge";
import "./ResultsPanel.css";

interface ResultsPanelProps {
  result: AnalyzeResponse | null;
  loading: boolean;
  resumeLoading: boolean;
  progress: ProgressEvent[];
  onResume: (approved: boolean) => void;
  onExport: (format: "json" | "pdf") => void;
}

function ProgressList({ items }: { items: ProgressEvent[] }) {
  if (!items.length) return null;
  return (
    <section className="result-section progress-section">
      <h3>Live progress</h3>
      <ol className="progress-list">
        {items.slice(-8).map((item, index) => (
          <li key={`${item.event}-${item.node ?? "pipeline"}-${index}`}>
            <span>{item.node ? item.node.replaceAll("_", " ") : item.event.replaceAll("_", " ")}</span>
            <small>{item.event.replaceAll("_", " ")}</small>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function ResultsPanel({
  result,
  loading,
  resumeLoading,
  progress,
  onResume,
  onExport,
}: ResultsPanelProps) {
  if (loading && !result) {
    return (
      <div className="panel results-panel">
        <div className="panel-header">
          <h2>Analysis Results</h2>
        </div>
        <div className="panel-body">
          <div className="loading-state">
            <div className="spinner" />
            <p>Supervisor routing agents...</p>
          </div>
          <ProgressList items={progress} />
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="panel results-panel">
        <div className="panel-header">
          <h2>Analysis Results</h2>
        </div>
        <div className="panel-body empty-state">
          <p>Submit a query to run the multi-agent pipeline.</p>
          <p>SQL Analyst, ESG Compliance, and Synthesis agents will process your request.</p>
        </div>
      </div>
    );
  }

  const report = result.final_synthesis_report;
  const needsReview = result.status === "awaiting_human_review";
  const actualScore = result.evaluation_scores?.overall ?? 0;

  return (
    <div className="panel results-panel">
      <div className="panel-header">
        <h2>Analysis Results</h2>
        <div className="result-actions">
          <button type="button" className="btn btn-secondary" onClick={() => onExport("json")}>
            JSON
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => onExport("pdf")}>
            PDF
          </button>
          <StatusBadge status={result.status} humanApproved={result.human_approved} />
        </div>
      </div>
      <div className="panel-body">
        <ProgressList items={progress} />

        {needsReview && (
          <HumanReviewPanel
            threadId={result.thread_id}
            actualScore={actualScore}
            requiredScore={0.82}
            loading={resumeLoading}
            onApprove={() => onResume(true)}
            onReject={() => onResume(false)}
          />
        )}

        {result.evaluation_scores && Object.keys(result.evaluation_scores).length > 0 && (
          <section className="result-section">
            <h3>Evaluation scores</h3>
            <ScoreCard scores={result.evaluation_scores} />
          </section>
        )}

        {report?.recommendation && (
          <section className="result-section">
            <h3>Recommendation</h3>
            <p className="recommendation">{report.recommendation}</p>
          </section>
        )}

        {result.tasks_assigned?.length > 0 && (
          <section className="result-section">
            <h3>Agent routing</h3>
            <div className="task-tags">
              {result.tasks_assigned.map((task) => (
                <span key={task} className="task-tag">
                  {task.replaceAll("_", " ")}
                </span>
              ))}
            </div>
            {report?.routing_rationale && (
              <p className="routing-rationale">{report.routing_rationale}</p>
            )}
          </section>
        )}

        <section className="result-section">
          <h3>SQL execution</h3>
          <SqlResultsTable results={result.sql_execution_results} />
        </section>

        <section className="result-section">
          <h3>ESG vector context</h3>
          <EsgContextList items={result.vector_retrieved_context} />
        </section>

        {report?.live_web_context && report.live_web_context !== "not_fetched" && (
          <section className="result-section">
            <h3>Live web context</h3>
            <p className="web-context">{report.live_web_context}</p>
          </section>
        )}
      </div>
    </div>
  );
}
