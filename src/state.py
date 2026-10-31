"""Typed workflow state shared by the intelligence pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SqlExecutionResult(BaseModel):
    sql: str = ""
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(default=0, ge=0)
    status: Literal["success", "rejected", "empty", "error", "not_run"] = "not_run"
    error: str | None = None


class SourceMetadata(BaseModel):
    source: str
    standard: str
    document_id: str
    score: float = Field(ge=0, le=1)


class AgentMessage(BaseModel):
    agent: str
    message: str
    level: Literal["info", "warning", "error"] = "info"


class ExecutionMetadata(BaseModel):
    thread_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = Field(default=0, ge=0)


class GraphState(BaseModel):
    user_query: str = Field(min_length=1)
    tasks_assigned: list[str] = Field(default_factory=list)
    routing_decision: Literal["sql", "esg", "both", "unsupported"] = "unsupported"
    routing_rationale: str = ""
    sql_query: str | None = None
    sql_execution_results: list[SqlExecutionResult] = Field(default_factory=list)
    esg_query: str | None = None
    vector_retrieved_context: list[str] = Field(default_factory=list)
    source_metadata: list[SourceMetadata] = Field(default_factory=list)
    live_web_context: str = ""
    final_synthesis_report: dict[str, Any] = Field(default_factory=dict)
    evaluation_scores: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(default=0, ge=0, le=1)
    human_review_required: bool = False
    human_approved: bool = False
    errors: list[str] = Field(default_factory=list)
    execution_metadata: ExecutionMetadata
    agent_messages: list[AgentMessage] = Field(default_factory=list)

    @field_validator("tasks_assigned")
    @classmethod
    def unique_tasks(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))
