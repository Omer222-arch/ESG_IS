from datetime import datetime, timezone

from src.state import (
    AgentMessage,
    ExecutionMetadata,
    GraphState,
    SourceMetadata,
    SqlExecutionResult,
)
from src.synthesis import SynthesisAgent


def make_state() -> GraphState:
    return GraphState(
        user_query="Which companies have high ESG risk?",
        execution_metadata=ExecutionMetadata(
            thread_id="test-thread"
        ),
        sql_execution_results=[
            SqlExecutionResult(
                sql="SELECT company, esg_risk FROM holdings",
                rows=[
                    {
                        "company": "Company A",
                        "esg_risk": "High",
                    }
                ],
                row_count=1,
                status="success",
            )
        ],
        vector_retrieved_context=[
            "SFDR Article 8 products must document how promoted environmental or social characteristics are monitored."
        ],
        source_metadata=[
            SourceMetadata(
                source="SFDR",
                standard="SFDR",
                document_id="sfdr-article-8",
                score=0.9,
            )
        ],
        confidence=0.9,
    )


def test_synthesis_creates_report():
    state = make_state()

    result = SynthesisAgent().run(state)

    report = result["final_synthesis_report"]

    assert report["query"] == "Which companies have high ESG risk?"
    assert report["report"]
    assert report["confidence"] == 0.9


def test_synthesis_contains_sql_findings():
    state = make_state()

    result = SynthesisAgent().run(state)

    report = result["final_synthesis_report"]

    assert len(report["sql_findings"]) == 1
    assert report["sql_findings"][0]["row_count"] == 1


def test_synthesis_contains_esg_context():
    state = make_state()

    result = SynthesisAgent().run(state)

    report = result["final_synthesis_report"]

    assert len(report["esg_findings"]) == 1
    assert "SFDR" in report["esg_findings"][0]


def test_synthesis_contains_sources():
    state = make_state()

    result = SynthesisAgent().run(state)

    report = result["final_synthesis_report"]

    assert len(report["sources"]) == 1
    assert report["sources"][0]["standard"] == "SFDR"


def test_synthesis_handles_empty_specialist_results():
    state = GraphState(
        user_query="What is ESG?",
        execution_metadata=ExecutionMetadata(
            thread_id="empty-test"
        ),
        confidence=0.0,
    )

    result = SynthesisAgent().run(state)

    report = result["final_synthesis_report"]

    assert report["query"] == "What is ESG?"
    assert report["sql_findings"] == []
    assert report["esg_findings"] == []
    assert report["sources"] == []