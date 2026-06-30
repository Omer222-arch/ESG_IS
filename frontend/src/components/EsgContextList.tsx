import "./EsgContextList.css";

interface EsgContextListProps {
  items: string[];
}

export function EsgContextList({ items }: EsgContextListProps) {
  if (!items.length) {
    return <p className="section-empty">No ESG context retrieved.</p>;
  }

  return (
    <ul className="esg-list">
      {items.map((item, idx) => (
        <li key={idx}>
          <span className="esg-index">{idx + 1}</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
