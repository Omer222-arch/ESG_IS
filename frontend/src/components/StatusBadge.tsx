import "./StatusBadge.css";

interface StatusBadgeProps {
  status: string;
  humanApproved: boolean;
}

export function StatusBadge({ status, humanApproved }: StatusBadgeProps) {
  const variant =
    status === "completed"
      ? "success"
      : status === "awaiting_human_review"
        ? "warn"
        : "neutral";

  return (
    <div className="badges">
      <span className={`badge badge-${variant}`}>{status.replaceAll("_", " ")}</span>
      <span className={`badge badge-${humanApproved ? "success" : "warn"}`}>
        {humanApproved ? "Approved" : "Pending review"}
      </span>
    </div>
  );
}
