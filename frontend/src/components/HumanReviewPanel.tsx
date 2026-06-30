import "./HumanReviewPanel.css";

interface HumanReviewPanelProps {
  threadId: string;
  actualScore: number;
  requiredScore: number;
  loading: boolean;
  onApprove: () => void;
  onReject: () => void;
}

export function HumanReviewPanel({
  threadId,
  actualScore,
  requiredScore,
  loading,
  onApprove,
  onReject,
}: HumanReviewPanelProps) {
  return (
    <div className="review-panel">
      <div className="review-icon" aria-hidden>
        !
      </div>
      <div className="review-content">
        <h3>Human review required</h3>
        <p>
          Evaluation score <strong>{(actualScore * 100).toFixed(1)}%</strong> is below the{" "}
          <strong>{(requiredScore * 100).toFixed(0)}%</strong> threshold. Approve to override
          and finalize, or reject to keep the report blocked.
        </p>
        <p className="review-thread mono">Thread: {threadId}</p>
        <div className="review-actions">
          <button
            type="button"
            className="btn btn-approve"
            onClick={onApprove}
            disabled={loading}
          >
            {loading ? "Processing..." : "Approve & finalize"}
          </button>
          <button
            type="button"
            className="btn btn-reject"
            onClick={onReject}
            disabled={loading}
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
