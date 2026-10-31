
"""LangGraph workflow for the ESG Intelligence System."""

from __future__ import annotations

from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from src.esg_compliance import EsgComplianceAgent
from src.evaluator import Evaluator
from src.state import (
    AgentMessage,
    GraphState,
    SourceMetadata,
)
from src.supervisor import Supervisor
from src.synthesis import SynthesisAgent


SQLRunner = Callable[[GraphState], dict[str, Any]]


class ESGGraph:
    """Build and execute the ESG intelligence LangGraph."""

    def __init__(
        self,
        sql_runner: SQLRunner | None = None,
        checkpointer: Any | None = None,
    ) -> None:
        self.sql_runner = sql_runner
        self.checkpointer = checkpointer or MemorySaver()

        self.supervisor = Supervisor()
        self.esg_agent = EsgComplianceAgent()
        self.synthesis_agent = SynthesisAgent()
        self.evaluator = Evaluator()

        self.graph = self._build()

    def _build(self):
        workflow = StateGraph(GraphState)

        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("sql_analyst", self.sql_node)
        workflow.add_node("esg_compliance", self.esg_node)
        workflow.add_node("synthesis", self.synthesis_node)
        workflow.add_node("evaluator", self.evaluator_node)
        workflow.add_node("human_review", self.human_review_node)

        workflow.add_edge(START, "supervisor")

        workflow.add_conditional_edges(
            "supervisor",
            self.route_after_supervisor,
            {
                "sql": "sql_analyst",
                "esg": "esg_compliance",
                "both": "sql_analyst",
                "unsupported": "synthesis",
            },
        )

        workflow.add_conditional_edges(
            "sql_analyst",
            self.route_after_sql,
            {
                "esg": "esg_compliance",
                "synthesis": "synthesis",
            },
        )

        workflow.add_edge("esg_compliance", "synthesis")
        workflow.add_edge("synthesis", "evaluator")

        workflow.add_conditional_edges(
            "evaluator",
            self.route_after_evaluator,
            {
                "review": "human_review",
                "complete": END,
            },
        )

        workflow.add_edge("human_review", END)

        return workflow.compile(
            checkpointer=self.checkpointer
        )

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

    def supervisor_node(
        self,
        state: GraphState,
    ) -> dict[str, Any]:
        result = self.supervisor.route(state.user_query)

        return {
            "routing_decision": result["routing_decision"],
            "routing_rationale": result["routing_rationale"],
            "tasks_assigned": result["tasks_assigned"],
            "agent_messages": [
                AgentMessage(
                    agent="supervisor",
                    message=result["routing_rationale"],
                )
            ],
        }

    def sql_node(
        self,
        state: GraphState,
    ) -> dict[str, Any]:
        if self.sql_runner is None:
            message = "SQL analysis was requested but no SQL runner is configured."
            return {
                "errors": ["SQL runner is not configured for the LangGraph workflow."],
                "agent_messages": [
                    AgentMessage(
                        agent="sql_analyst",
                        message=message,
                        level="error",
                    )
                ],
            }

        try:
            result = self.sql_runner(state)

            sql = result.get("sql") or None
            rows = result.get("rows") or []
            status = result.get("status", "error")
            error = result.get("error")

            update: dict[str, Any] = {
                "sql_query": sql,
                "sql_execution_results": [
                    {
                        "sql": sql or "",
                        "rows": rows,
                        "row_count": result.get("row_count", len(rows)),
                        "status": status,
                        "error": error,
                    }
                ],
                "agent_messages": [
                    AgentMessage(
                        agent="sql_analyst",
                        message=(
                            "SQL analysis completed."
                            if status == "success"
                            else f"SQL analysis finished with status: {status}."
                        ),
                        level="info" if status == "success" else "warning",
                    )
                ],
            }

            if error:
                update["errors"] = [f"SQL analyst: {error}"]

            return update

        except Exception as exc:
            return {
                "errors": [f"SQL analyst failed: {exc}"],
                "agent_messages": [
                    AgentMessage(
                        agent="sql_analyst",
                        message="SQL analysis failed.",
                        level="error",
                    )
                ],
            }
    def esg_node(
        self,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute the ESG compliance agent."""

        query = state.esg_query or state.user_query

        try:
            result = self.esg_agent.analyze(query)

            contexts = result.get(
                "context",
                [],
            )

            sources = result.get(
                "sources",
                [],
            )

            metadata: list[SourceMetadata] = []

            for item in sources:
                if isinstance(item, SourceMetadata):
                    metadata.append(item)
                else:
                    metadata.append(
                        SourceMetadata(
                            source=str(
                                item.get(
                                    "source",
                                    "Unknown",
                                )
                            ),
                            standard=str(
                                item.get(
                                    "standard",
                                    "Unknown",
                                )
                            ),
                            document_id=str(
                                item.get(
                                    "document_id",
                                    "unknown",
                                )
                            ),
                            score=float(
                                item.get(
                                    "score",
                                    0.0,
                                )
                            ),
                        )
                    )

            status = result.get(
                "status",
                "low_confidence",
            )

            if status == "success":
                level = "info"
                message = "ESG compliance analysis completed."
            else:
                level = "warning"
                message = (
                    "ESG compliance analysis completed "
                    "with low retrieval confidence."
                )

            return {
                "esg_query": query,
                "vector_retrieved_context": contexts,
                "source_metadata": metadata,
                "agent_messages": [
                    AgentMessage(
                        agent="esg_compliance",
                        message=message,
                        level=level,
                    )
                ],
            }

        except Exception as exc:
            return {
                "esg_query": query,
                "errors": [
                    f"ESG compliance agent failed: {exc}"
                ],
                "agent_messages": [
                    AgentMessage(
                        agent="esg_compliance",
                        message="ESG compliance analysis failed.",
                        level="error",
                    )
                ],
            }

    def synthesis_node(
        self,
        state: GraphState,
    ) -> dict[str, Any]:
        return self.synthesis_agent.run(state)

    def evaluator_node(
        self,
        state: GraphState,
    ) -> dict[str, Any]:
        return self.evaluator.evaluate(state)

    def human_review_node(
        self,
        state: GraphState,
    ) -> Command:
        """Pause execution until a human approves/rejects the result."""

        decision = interrupt(
            {
                "type": "human_review",
                "message": (
                    "The analysis confidence is below the required "
                    "threshold. Please approve or reject the result."
                ),
                "confidence": state.confidence,
                "evaluation_scores": state.evaluation_scores,
                "report": state.final_synthesis_report,
            }
        )

        if decision is True or decision == "approve":
            return Command(
                update={
                    "human_review_required": False,
                    "human_approved": True,
                    "agent_messages": [
                        AgentMessage(
                            agent="human_review",
                            message="Human reviewer approved the analysis.",
                        )
                    ],
                },
                goto=END,
            )

        return Command(
            update={
                "human_review_required": True,
                "human_approved": False,
                "agent_messages": [
                    AgentMessage(
                        agent="human_review",
                        message="Human reviewer rejected the analysis.",
                        level="warning",
                    )
                ],
            },
            goto=END,
        )

    # ---------------------------------------------------------
    # Routing
    # ---------------------------------------------------------

    @staticmethod
    def route_after_supervisor(
        state: GraphState,
    ) -> str:
        return state.routing_decision

    @staticmethod
    def route_after_sql(
        state: GraphState,
    ) -> str:
        if state.routing_decision == "both":
            return "esg"

        return "synthesis"

    @staticmethod
    def route_after_evaluator(
        state: GraphState,
    ) -> str:
        if state.human_review_required:
            return "review"

        return "complete"


def create_graph(
    sql_runner: SQLRunner | None = None,
    checkpointer: Any | None = None,
):
    """Create a compiled ESG LangGraph workflow."""

    return ESGGraph(
        sql_runner=sql_runner,
        checkpointer=checkpointer,
    ).graph
