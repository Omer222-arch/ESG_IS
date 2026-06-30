export interface EvaluationScores {
  sql_confidence: number;
  vector_confidence: number;
  coverage: number;
  overall: number;
}

export interface SqlExecutionResult {
  sql: string;
  rows: Record<string, unknown>[];
  row_count: number;
  status: "success" | "rejected" | string;
  error?: string;
}

export interface SynthesisReport {
  query?: string;
  tasks_executed?: string[];
  sql_summary?: {
    status: string;
    row_count: number;
    sql: string;
  };
  esg_context_count?: number;
  esg_highlights?: string[];
  live_web_context?: string;
  evaluation?: EvaluationScores;
  recommendation?: string;
  routing_rationale?: string;
  routed_tasks?: string[];
}

export interface AnalyzeResponse {
  status: "completed" | "awaiting_human_review" | string;
  human_approved: boolean;
  evaluation_scores: EvaluationScores;
  final_synthesis_report: SynthesisReport;
  sql_execution_results: SqlExecutionResult[];
  vector_retrieved_context: string[];
  tasks_assigned: string[];
  thread_id: string;
  interrupts?: unknown[];
}

export interface ProgressEvent {
  event: "started" | "node_completed" | "human_review_required" | "completed" | "error" | string;
  thread_id: string;
  node?: string;
  output?: unknown;
  state?: unknown;
  result?: AnalyzeResponse;
  detail?: string;
}

export interface HistoryItem {
  thread_id: string;
  user_query: string;
  status: string;
  human_approved: boolean;
  created_at: number;
  updated_at: number;
}

export interface AnalyzeRequest {
  user_query: string;
  live_web_context?: string;
  thread_id?: string;
}

export interface ResumeRequest {
  thread_id: string;
  human_approved: boolean;
}

export interface HealthResponse {
  status: string;
}
