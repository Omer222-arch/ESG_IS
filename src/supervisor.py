"""Supervisor routing for the ESG intelligence pipeline."""

from __future__ import annotations

import re
from typing import Any

from src.state import GraphState


SQL_PATTERNS = (
    r"\bportfolio\b",
    r"\bcompany\b",
    r"\bcompanies\b",
    r"\bholdings?\b",
    r"\brevenue\b",
    r"\bprofit\b",
    r"\bprofits\b",
    r"\bfinancial\b",
    r"\bfinancials\b",
    r"\bsector\b",
    r"\bsectors\b",
    r"\bstock\b",
    r"\binvestment\b",
    r"\binvestments\b",
    r"\brisk score\b",
    r"\bmarket value\b",
)

ESG_PATTERNS = (
    r"\besg\b",
    r"\bsustainability\b",
    r"\bcompliance\b",
    r"\bregulation\b",
    r"\bregulations\b",
    r"\bstandard\b",
    r"\bstandards\b",
    r"\bsasb\b",
    r"\bsfdr\b",
    r"\beu taxonomy\b",
    r"\btaxonomy\b",
    r"\biss\b",
    r"\bgreen\b",
    r"\bsocial\b",
    r"\bgovernance\b",
    r"\bscope 1\b",
    r"\bscope 2\b",
    r"\bscope 3\b",
    r"\bghg\b",
    r"\bcarbon\b",
    r"\bemissions?\b",
)


class Supervisor:
    """Determine which specialist agents should process a query."""

    def route(self, query: str) -> dict[str, Any]:
        query = query.strip()

        if not query:
            return {
                "routing_decision": "unsupported",
                "routing_rationale": "No query was provided.",
                "tasks_assigned": [],
            }

        normalized = query.lower()

        sql_matches = self._matches(normalized, SQL_PATTERNS)
        esg_matches = self._matches(normalized, ESG_PATTERNS)

        if sql_matches and esg_matches:
            decision = "both"
            tasks = ["sql_analyst", "esg_compliance"]
            rationale = (
                "The query requires both portfolio/database analysis "
                "and ESG compliance context."
            )

        elif sql_matches:
            decision = "sql"
            tasks = ["sql_analyst"]
            rationale = (
                "The query contains portfolio or database-analysis intent."
            )

        elif esg_matches:
            decision = "esg"
            tasks = ["esg_compliance"]
            rationale = (
                "The query contains ESG, sustainability, regulatory, "
                "or compliance intent."
            )

        else:
            decision = "unsupported"
            tasks = []
            rationale = (
                "The query does not match the supported SQL or ESG "
                "analysis capabilities."
            )

        return {
            "routing_decision": decision,
            "routing_rationale": rationale,
            "tasks_assigned": tasks,
        }

    @staticmethod
    def _matches(query: str, patterns: tuple[str, ...]) -> list[str]:
        return [
            pattern
            for pattern in patterns
            if re.search(pattern, query)
        ]


def supervise(state: GraphState) -> dict[str, Any]:
    """Route an existing GraphState query."""

    result = Supervisor().route(state.user_query)

    return {
        "routing_decision": result["routing_decision"],
        "routing_rationale": result["routing_rationale"],
        "tasks_assigned": result["tasks_assigned"],
    }