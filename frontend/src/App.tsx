import { useCallback, useEffect, useMemo, useState } from "react";
import {
  analyzePortfolioStream,
  checkHealth,
  downloadExport,
  getHistoryRun,
  listHistory,
  resumeAnalysis,
} from "./api/client";
import type { AnalyzeResponse, HistoryItem, ProgressEvent } from "./types";
import { Header } from "./components/Header";
import { QueryForm } from "./components/QueryForm";
import { ResultsPanel } from "./components/ResultsPanel";
import "./App.css";

const LOCAL_HISTORY_KEY = "esg_analysis_history";
const THEME_KEY = "esg_theme";

function loadLocalHistory(): HistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_HISTORY_KEY) || "[]") as HistoryItem[];
  } catch {
    return [];
  }
}

function toHistoryItem(result: AnalyzeResponse): HistoryItem {
  const now = Date.now() / 1000;
  return {
    thread_id: result.thread_id,
    user_query: result.final_synthesis_report?.query || result.thread_id,
    status: result.status,
    human_approved: result.human_approved,
    created_at: now,
    updated_at: now,
  };
}

export default function App() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>(loadLocalHistory);
  const [theme, setTheme] = useState<"dark" | "light">(
    (localStorage.getItem(THEME_KEY) as "dark" | "light" | null) || "dark",
  );

  const mergedHistory = useMemo(() => {
    const byId = new Map<string, HistoryItem>();
    for (const item of history) byId.set(item.thread_id, item);
    return [...byId.values()].sort((a, b) => b.updated_at - a.updated_at).slice(0, 25);
  }, [history]);

  const persistHistory = useCallback((items: HistoryItem[]) => {
    setHistory(items);
    localStorage.setItem(LOCAL_HISTORY_KEY, JSON.stringify(items.slice(0, 25)));
  }, []);

  const rememberResult = useCallback(
    (next: AnalyzeResponse) => {
      setResult(next);
      const item = toHistoryItem(next);
      const withoutCurrent = history.filter((entry) => entry.thread_id !== item.thread_id);
      persistHistory([item, ...withoutCurrent]);
    },
    [history, persistHistory],
  );

  const pollHealth = useCallback(async () => {
    try {
      const health = await checkHealth();
      setBackendOnline(health.status === "ok");
    } catch {
      setBackendOnline(false);
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const response = await listHistory();
      persistHistory(response.items);
    } catch {
      persistHistory(loadLocalHistory());
    }
  }, [persistHistory]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    pollHealth();
    refreshHistory();
    const interval = setInterval(pollHealth, 15000);
    return () => clearInterval(interval);
  }, [pollHealth, refreshHistory]);

  const handleAnalyze = async (query: string, liveWebContext: string) => {
    setLoading(true);
    setProgress([]);
    setError(null);
    try {
      const response = await analyzePortfolioStream(
        { user_query: query, live_web_context: liveWebContext },
        (event) => setProgress((items) => [...items, event]),
      );
      rememberResult(response);
      refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async (approved: boolean) => {
    if (!result?.thread_id) return;
    setResumeLoading(true);
    setError(null);
    try {
      const response = await resumeAnalysis({
        thread_id: result.thread_id,
        human_approved: approved,
      });
      rememberResult(response);
      refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume failed");
    } finally {
      setResumeLoading(false);
    }
  };

  const handleLoadHistory = async (threadId: string) => {
    setError(null);
    try {
      const response = await getHistoryRun(threadId);
      setProgress([]);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load run");
    }
  };

  const handleExport = async (format: "json" | "pdf") => {
    if (!result?.thread_id) return;
    try {
      await downloadExport(result.thread_id, format);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <div className="app">
      <Header
        backendOnline={backendOnline}
        theme={theme}
        onToggleTheme={() => setTheme((value) => (value === "dark" ? "light" : "dark"))}
      />
      {error && <div className="error-banner">{error}</div>}
      <div className="layout">
        <aside className="sidebar-stack">
          <QueryForm loading={loading} onSubmit={handleAnalyze} />
          <div className="panel history-panel">
            <div className="panel-header">
              <h2>Analysis History</h2>
              <button type="button" className="btn btn-secondary" onClick={refreshHistory}>
                Sync
              </button>
            </div>
            <div className="panel-body history-list">
              {mergedHistory.length === 0 ? (
                <p className="history-empty">No previous runs yet.</p>
              ) : (
                mergedHistory.map((item) => (
                  <button
                    type="button"
                    key={item.thread_id}
                    className="history-item"
                    onClick={() => handleLoadHistory(item.thread_id)}
                  >
                    <span>{item.user_query}</span>
                    <small>{item.status.replaceAll("_", " ")}</small>
                  </button>
                ))
              )}
            </div>
          </div>
        </aside>
        <ResultsPanel
          result={result}
          loading={loading}
          resumeLoading={resumeLoading}
          progress={progress}
          onResume={handleResume}
          onExport={handleExport}
        />
      </div>
    </div>
  );
}
