import { type FormEvent } from "react";
import "./QueryForm.css";

const EXAMPLE_QUERIES = [
  "Show portfolio allocations and SASB carbon compliance",
  "Compare revenue and capex across companies",
  "ESG governance and diversity disclosure requirements",
  "What are the portfolio weights for ESG Core?",
];

interface QueryFormProps {
  loading: boolean;
  onSubmit: (query: string, liveWebContext: string) => void;
}

export function QueryForm({ loading, onSubmit }: QueryFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const query = (form.elements.namedItem("query") as HTMLTextAreaElement).value.trim();
    const liveWeb = (form.elements.namedItem("liveWeb") as HTMLTextAreaElement).value.trim();
    if (query) onSubmit(query, liveWeb);
  };

  const fillExample = (text: string) => {
    const queryEl = document.querySelector<HTMLTextAreaElement>('textarea[name="query"]');
    if (queryEl) {
      queryEl.value = text;
      queryEl.focus();
    }
  };

  return (
    <div className="panel query-form">
      <div className="panel-header">
        <h2>New Analysis</h2>
      </div>
      <div className="panel-body">
        <form onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="query">
            Portfolio / ESG query
          </label>
          <textarea
            id="query"
            name="query"
            rows={4}
            placeholder="e.g. Show portfolio allocations and SASB carbon compliance for utilities sector"
            required
            disabled={loading}
          />

          <label className="field-label" htmlFor="liveWeb">
            Live web context (optional)
          </label>
          <textarea
            id="liveWeb"
            name="liveWeb"
            rows={2}
            placeholder="Optional external context to include in synthesis"
            disabled={loading}
          />

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Running agents..." : "Run analysis"}
          </button>
        </form>

        <div className="examples">
          <span className="examples-label">Quick examples</span>
          <div className="example-chips">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                type="button"
                className="chip"
                onClick={() => fillExample(q)}
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
