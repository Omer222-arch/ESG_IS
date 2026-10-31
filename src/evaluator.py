"""Evaluate the quality and completeness of ESG Intelligence results."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.state import GraphState


class Evaluator:
    def __init__(self, threshold: float | None = None) -> None:
        self.threshold = (
            settings.human_review_threshold
            if threshold is None
            else threshold
        )

    def evaluate(self, state: GraphState) -> dict[str, Any]:
        sql_score = self._evaluate_sql(state)
        esg_score = self._evaluate_esg(state)
        coverage_score = self._evaluate_coverage(state)

        routing = state.routing_decision

        if routing == "sql":
            overall = (
                sql_score * 0.70
                + coverage_score * 0.30
            )

        elif routing == "esg":
            overall = (
                esg_score * 0.70
                + coverage_score * 0.30
            )

        elif routing == "both":
            overall = (
                sql_score * 0.35
                + esg_score * 0.35
                + coverage_score * 0.30
            )

        else:
            overall = coverage_score

        overall = round(
            max(0.0, min(1.0, overall)),
            3,
        )

        requires_review = overall < self.threshold

        return {
            "evaluation_scores": {
                "sql": round(sql_score, 3),
                "esg": round(esg_score, 3),
                "coverage": round(coverage_score, 3),
                "overall": overall,
            },
            "confidence": overall,
            "human_review_required": requires_review,
            "agent_messages": [
                {
                    "agent": "evaluator",
                    "message": (
                        f"Evaluation completed with confidence "
                        f"{overall:.3f}."
                    ),
                    "level": (
                        "warning"
                        if requires_review
                        else "info"
                    ),
                }
            ],
        }

    @staticmethod
    def _evaluate_sql(state: GraphState) -> float:
        if state.routing_decision not in {"sql", "both"}:
            return 0.0

        if not state.sql_execution_results:
            return 0.0

        successful = [
            result
            for result in state.sql_execution_results
            if result.status == "success"
        ]

        if not successful:
            return 0.0

        execution_score = 1.0

        useful_results = [
            result
            for result in successful
            if result.row_count > 0
        ]

        result_score = (
            1.0
            if useful_results
            else 0.70
        )

        return (
            execution_score * 0.70
            + result_score * 0.30
        )

    @staticmethod
    def _evaluate_esg(state: GraphState) -> float:
        if state.routing_decision not in {"esg", "both"}:
            return 0.0

        if not state.vector_retrieved_context or not state.source_metadata:
            return 0.0

        return max(source.score for source in state.source_metadata)

    @staticmethod
    def _evaluate_coverage(state: GraphState) -> float:
        routing = state.routing_decision

        sql_success = any(
            result.status in {"success", "empty"}
            for result in state.sql_execution_results
        )

        esg_success = bool(
            state.vector_retrieved_context
            and state.source_metadata
        )

        if routing == "sql":
            return 1.0 if sql_success else 0.0

        if routing == "esg":
            return 1.0 if esg_success else 0.0

        if routing == "both":
            completed = int(sql_success) + int(esg_success)
            return completed / 2.0

        return 0.0