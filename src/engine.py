
"""
Application orchestration layer for the ESG Intelligence System.

Connects FastAPI with the LangGraph workflow and provides:
- REST analysis
- SSE streaming
- persistent LangGraph threads
- human-in-the-loop interruption
- human approval/rejection and resume
- JSON-safe serialization
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncIterator

from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.database import PortfolioDatabase
from src.graph import create_graph
from src.state import ExecutionMetadata, GraphState
from src.sql_agent import analyze_sql


# ============================================================================
# SHARED CHECKPOINTER
# ============================================================================

# The graph and checkpointer MUST remain shared between:
#
#   initial request
#       ↓
#   interrupt()
#       ↓
#   resume_analysis()
#
# Otherwise MemorySaver loses the interrupted thread.

_CHECKPOINTER = MemorySaver()


# ============================================================================
# SQL RUNNER
# ============================================================================


def _sql_runner(state: GraphState) -> dict[str, Any]:
    """
    Execute the SQL analyst using the current GraphState.

    graph.py passes GraphState into SQLRunner, not a raw string.
    """

    database = PortfolioDatabase(
        settings.database_path
    )

    query = (
        state.sql_query
        or state.user_query
    )

    return analyze_sql(
        query=query,
        database=database,
        config=settings,
    )


# ============================================================================
# SHARED GRAPH
# ============================================================================

_GRAPH = create_graph(
    sql_runner=_sql_runner,
    checkpointer=_CHECKPOINTER,
)


# ============================================================================
# JSON SERIALIZATION
# ============================================================================


def _serialize_state(value: Any) -> Any:
    """
    Recursively convert Pydantic, LangGraph and Python objects
    into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    # Pydantic models.
    if hasattr(value, "model_dump"):
        try:
            return _serialize_state(
                value.model_dump(mode="json")
            )
        except Exception:
            return str(value)

    # Dictionaries.
    if isinstance(value, dict):
        return {
            str(key): _serialize_state(item)
            for key, item in value.items()
        }

    # Lists / tuples.
    if isinstance(value, (list, tuple)):
        return [
            _serialize_state(item)
            for item in value
        ]

    # Sets.
    if isinstance(value, set):
        return [
            _serialize_state(item)
            for item in value
        ]

    # LangGraph Interrupt-like objects.
    if hasattr(value, "id") and hasattr(
        value,
        "value",
    ):
        return {
            "id": str(
                getattr(value, "id", "")
            ),
            "value": _serialize_state(
                getattr(value, "value", None)
            ),
        }

    # Final fallback.
    return str(value)


def _serialize_interrupt(
    item: Any,
) -> dict[str, Any]:
    """
    Convert a LangGraph Interrupt to JSON-safe data.
    """

    return {
        "id": str(
            getattr(item, "id", "")
        ),
        "value": _serialize_state(
            getattr(item, "value", None)
        ),
    }


# ============================================================================
# INITIAL STATE
# ============================================================================


def _build_initial_state(
    user_query: str,
    thread_id: str,
    live_web_context: str = "",
) -> GraphState:
    """
    Build the initial GraphState.
    """

    return GraphState(
        user_query=user_query.strip(),
        live_web_context=(
            live_web_context or ""
        ),
        execution_metadata=ExecutionMetadata(
            thread_id=thread_id,
            started_at=datetime.now(
                timezone.utc
            ),
        ),
    )


# ============================================================================
# LANGGRAPH CONFIGURATION
# ============================================================================


def _config(
    thread_id: str,
) -> dict[str, Any]:
    """
    Return LangGraph configuration for a thread.
    """

    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


# ============================================================================
# PERSISTED STATE
# ============================================================================


def _final_state_from_snapshot(
    thread_id: str,
) -> dict[str, Any]:
    """
    Retrieve the latest state for a thread.
    """

    snapshot = _GRAPH.get_state(
        _config(thread_id)
    )

    if snapshot is None:
        return {}

    return _serialize_state(
        snapshot.values
    )


# ============================================================================
# INTERRUPT DETECTION
# ============================================================================


def _interrupts_for_thread(
    thread_id: str,
) -> list[Any]:
    """
    Retrieve pending interrupts for a LangGraph thread.
    """

    snapshot = _GRAPH.get_state(
        _config(thread_id)
    )

    if snapshot is None:
        return []

    interrupts: list[Any] = []

    for task in getattr(
        snapshot,
        "tasks",
        (),
    ):
        for item in getattr(
            task,
            "interrupts",
            (),
        ):
            interrupts.append(item)

    return interrupts


# ============================================================================
# NORMAL REST ANALYSIS
# ============================================================================


async def run_analysis(
    user_query: str,
    thread_id: str,
    live_web_context: str = "",
) -> dict[str, Any]:
    """
    Execute one analysis request.
    """

    initial_state = _build_initial_state(
        user_query=user_query,
        thread_id=thread_id,
        live_web_context=live_web_context,
    )

    config = _config(thread_id)

    result = _GRAPH.invoke(
        initial_state.model_dump(),
        config=config,
    )

    interrupts = _interrupts_for_thread(
        thread_id
    )

    output = _final_state_from_snapshot(
        thread_id
    )

    if not output:
        output = _serialize_state(
            result
        )

    if interrupts:
        output["status"] = (
            "human_review_required"
        )

        output[
            "human_review_required"
        ] = True

        output["interrupts"] = [
            _serialize_interrupt(item)
            for item in interrupts
        ]

        return output
    output["status"] = "completed"

    return output


# ============================================================================
# SSE STREAMING
# ============================================================================



async def run_analysis_events(
    user_query: str,
    thread_id: str,
    live_web_context: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """
    Stream LangGraph progress events and emit a final result.
    """

    initial_state = _build_initial_state(
        user_query=user_query,
        thread_id=thread_id,
        live_web_context=live_web_context,
    )

    config = _config(thread_id)

    yield {
        "event": "started",
        "thread_id": thread_id,
    }

    try:
        for update in _GRAPH.stream(
            initial_state.model_dump(),
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_update in update.items():

                # Handle interrupts through get_state().
                if node_name == "__interrupt__":
                    continue

                yield {
                    "event": "agent_update",
                    "thread_id": thread_id,
                    "agent": node_name,
                    "update": _serialize_state(node_update),
                }

        interrupts = _interrupts_for_thread(thread_id)

        final_state = _final_state_from_snapshot(thread_id)

        if not final_state:
            yield {
                "event": "error",
                "thread_id": thread_id,
                "detail": "Analysis finished, but no final state was found.",
            }
            return

        if interrupts:
            final_state["status"] = "human_review_required"
            final_state["human_review_required"] = True
            final_state["interrupts"] = [
                _serialize_interrupt(item)
                for item in interrupts
            ]
        else:
            final_state["status"] = "completed"

        yield {
            "event": "completed",
            "thread_id": thread_id,
            "result": final_state,
        }

    except Exception as exc:
        yield {
            "event": "error",
            "thread_id": thread_id,
            "detail": str(exc),
        }

# ============================================================================
# HUMAN-IN-THE-LOOP RESUME
# ============================================================================


async def resume_analysis(
    thread_id: str,
    human_approved: bool,
) -> dict[str, Any]:
    """
    Resume a previously interrupted analysis.

    IMPORTANT:
    human_review_node() calls:

        interrupt({...})

    Therefore the resume value must be the boolean itself:

        Command(resume=True)

    NOT:

        Command(resume={"decision": "approve"})
    """

    config = _config(thread_id)

    # --------------------------------------------------------------
    # Verify persisted state exists.
    # --------------------------------------------------------------

    snapshot = _GRAPH.get_state(
        config
    )

    if snapshot is None:
        raise ValueError(
            f"No persisted state found for thread: {thread_id}"
        )

    if not snapshot.values:
        raise ValueError(
            f"Persisted state is empty for thread: {thread_id}"
        )

    # Verify that the required GraphState
    # fields are present before attempting resume.
    if not snapshot.values.get(
        "user_query"
    ):
        raise ValueError(
            "Persisted state is missing user_query."
        )

    if not snapshot.values.get(
        "execution_metadata"
    ):
        raise ValueError(
            "Persisted state is missing execution_metadata."
        )

    # --------------------------------------------------------------
    # Resume the interrupted graph.
    # --------------------------------------------------------------

    from langgraph.types import Command

    result = _GRAPH.invoke(
        Command(
            # IMPORTANT:
            # interrupt() receives this value directly.
            resume=bool(human_approved)
        ),
        config=config,
    )

    # --------------------------------------------------------------
    # Retrieve state after resume.
    # --------------------------------------------------------------

    output = _final_state_from_snapshot(
        thread_id
    )

    if not output:
        output = _serialize_state(
            result
        )

    output["thread_id"] = thread_id

    output[
        "human_approved"
    ] = bool(human_approved)

    if human_approved:

        output[
            "human_review_required"
        ] = False

        output["status"] = "completed"

    else:

        output[
            "human_review_required"
        ] = True

        output["status"] = "rejected"

    return output
