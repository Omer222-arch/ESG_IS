"""Human-in-the-loop review logic."""

from __future__ import annotations

from typing import Any

from src.state import GraphState


class HumanReviewManager:
    """Determine and apply human approval decisions."""

    def __init__(self, review_threshold: float = 0.82) -> None:
        self.review_threshold = review_threshold

    def requires_review(self, state: GraphState) -> bool:
        return state.confidence < self.review_threshold

    def request_review(self, state: GraphState) -> dict[str, Any]:
        required = self.requires_review(state)

        return {
            "human_review_required": required,
            "human_approved": not required,
        }

    def approve(self, state: GraphState) -> dict[str, Any]:
        return {
            "human_review_required": False,
            "human_approved": True,
        }

    def reject(self, state: GraphState) -> dict[str, Any]:
        return {
            "human_review_required": True,
            "human_approved": False,
        }


def request_human_review(state: GraphState) -> dict[str, Any]:
    return HumanReviewManager().request_review(state)