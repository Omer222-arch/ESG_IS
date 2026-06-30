import type { SqlExecutionResult } from "../types";
import "./SqlResultsTable.css";

interface SqlResultsTableProps {
  results: SqlExecutionResult[];
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    return String(value);
  }
  return String(value);
}

export function SqlResultsTable({ results }: SqlResultsTableProps) {
  if (!results.length) {
    return <p className="section-empty">No SQL results returned.</p>;
  }

  return (
    <div className="sql-blocks">
      {results.map((result, idx) => {
        const columns =
          result.rows.length > 0 ? Object.keys(result.rows[0]) : [];

        return (
          <div key={idx} className="sql-block">
            <div className="sql-meta">
              <span className={`sql-status sql-status-${result.status}`}>{result.status}</span>
              <span className="sql-count">{result.row_count} row(s)</span>
            </div>
            <pre className="sql-query mono">{result.sql}</pre>
            {result.error && <p className="sql-error">{result.error}</p>}
            {columns.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        {columns.map((col) => (
                          <td key={col}>{formatCell(row[col])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
