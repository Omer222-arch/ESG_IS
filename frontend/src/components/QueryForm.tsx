import { type FormEvent } from "react";
import "./QueryForm.css";

const EXAMPLE_QUERIES = [
  "Explain this agreement in simple language.",
  "What are my main responsibilities under this document?",
  "Explain the termination clause and notice period.",
  "Are there any fees, penalties, or renewal conditions?",
];

interface QueryFormProps {
  loading: boolean;
  onSubmit: (query: string, liveWebContext: string) => void;
}

export function QueryForm({ loading, onSubmit }: QueryFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const query =
      (form.elements.namedItem("query") as HTMLTextAreaElement | null)?.value.trim() ?? "";
    const liveWeb =
      (form.elements.namedItem("liveWeb") as HTMLTextAreaElement | null)?.value.trim() ?? "";

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
            What would you like to understand?
          </label>
          <textarea
            id="query"
            name="query"
            rows={4}
            placeholder="Ask about a clause, obligation, deadline, fee, or condition..."
            required
            disabled={loading}
          />

          <label className="field-label" htmlFor="liveWeb">
            Additional context (optional)
          </label>
          <textarea
            id="liveWeb"
            name="liveWeb"
            rows={2}
            placeholder="Add context that may help explain your question..."
            disabled={loading}
          />

          <div className="example-queries">
            {EXAMPLE_QUERIES.map((example) => (
              <button
                key={example}
                type="button"
                className="example-query"
                onClick={() => fillExample(example)}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Preparing your explanation..." : "Explain in simple language"}
          </button>
        </form>
      </div>
    </div>
  );
}
