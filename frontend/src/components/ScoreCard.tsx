import type { EvaluationScores } from "../types";
import "./ScoreCard.css";

interface ScoreCardProps {
  scores: EvaluationScores;
}

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function barClass(value: number) {
  if (value > 0.82) return "high";
  if (value >= 0.55) return "mid";
  return "low";
}

export function ScoreCard({ scores }: ScoreCardProps) {
  const items = [
    { label: "Overall", value: scores.overall, highlight: true },
    { label: "SQL confidence", value: scores.sql_confidence },
    { label: "Vector confidence", value: scores.vector_confidence },
    { label: "Coverage", value: scores.coverage },
  ];

  return (
    <div className="score-grid">
      {items.map(({ label, value, highlight }) => (
        <div key={label} className={`score-card ${highlight ? "score-card-highlight" : ""}`}>
          <span className="score-label">{label}</span>
          <span className="score-value">{pct(value)}</span>
          <div className="score-bar">
            <div className={`score-fill ${barClass(value)}`} style={{ width: pct(value) }} />
          </div>
        </div>
      ))}
    </div>
  );
}
