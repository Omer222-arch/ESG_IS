from typing import Any

from pydantic import BaseModel, Field


class GraphState(BaseModel):
    user_query: str = Field(default="")
    tasks_assigned: list[str] = Field(default_factory=list)
    sql_execution_results: list[dict[str, Any]] = Field(default_factory=list)
    vector_retrieved_context: list[str] = Field(default_factory=list)
    live_web_context: str = Field(default="")
    final_synthesis_report: dict[str, Any] = Field(default_factory=dict)
    evaluation_scores: dict[str, float] = Field(default_factory=dict)
    human_approved: bool = Field(default=True)
