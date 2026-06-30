import "./Header.css";

interface HeaderProps {
  backendOnline: boolean | null;
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

export function Header({ backendOnline, theme, onToggleTheme }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo" aria-hidden>
          ESG
        </div>
        <div>
          <h1>Portfolio & ESG Intelligence</h1>
          <p>Multi-agent analysis · SQL · Compliance · Synthesis</p>
        </div>
      </div>
      <div className="header-actions">
        <button type="button" className="theme-toggle" onClick={onToggleTheme}>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
        <div className="header-status">
          <span
            className={`status-dot ${backendOnline === null ? "checking" : backendOnline ? "online" : "offline"}`}
          />
          <span className="status-label">
            {backendOnline === null
              ? "Checking API..."
              : backendOnline
                ? "Backend online"
                : "Backend offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
