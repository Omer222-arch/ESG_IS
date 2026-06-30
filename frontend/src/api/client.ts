import type {
  AnalyzeRequest,
  AnalyzeResponse,
  HealthResponse,
  HistoryItem,
  ProgressEvent,
  ResumeRequest,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const API_KEY_STORAGE = "esg_api_key";
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY ?? "dev-local-key";

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE) || DEFAULT_API_KEY;
}

export function setApiKey(value: string): void {
  localStorage.setItem(API_KEY_STORAGE, value.trim());
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", "X-API-Key": getApiKey(), ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function analyzePortfolio(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/v1/analyze", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function resumeAnalysis(body: ResumeRequest): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/v1/resume", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function analyzePortfolioStream(
  body: AnalyzeRequest,
  onEvent: (event: ProgressEvent) => void,
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    throw new Error(response.statusText || "Streaming analysis failed");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: AnalyzeResponse | null = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      const event = JSON.parse(line.slice(6)) as ProgressEvent;
      onEvent(event);
      if (event.event === "completed" && event.result) finalResult = event.result;
      if (event.event === "error") throw new Error(event.detail || "Analysis failed");
    }
  }
  if (!finalResult) throw new Error("Analysis stream ended without a final result");
  return finalResult;
}

export function listHistory(): Promise<{ items: HistoryItem[] }> {
  return request<{ items: HistoryItem[] }>("/api/v1/history");
}

export function getHistoryRun(threadId: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>(`/api/v1/history/${encodeURIComponent(threadId)}`);
}

export async function downloadExport(threadId: string, format: "json" | "pdf"): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/export/${encodeURIComponent(threadId)}.${format}`,
    { headers: { "X-API-Key": getApiKey() } },
  );
  if (!response.ok) throw new Error(response.statusText || "Export failed");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `esg-report-${threadId}.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
