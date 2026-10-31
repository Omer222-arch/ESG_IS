from src.evaluator import Evaluator
from src.state import (
    ExecutionMetadata,
    GraphState,
    SourceMetadata,
    SqlExecutionResult,
)


def make_base_state(**kwargs):
    defaults = {
        "user_query": "test query",
        "execution_metadata": ExecutionMetadata(
            thread_id="evaluation-test"
        ),
    }

    defaults.update(kwargs)

    return GraphState(**defaults)


def test_sql_evaluation_high_confidence():
    state = make_base_state(
        routing_decision="sql",
        sql_execution_results=[
            SqlExecutionResult(
                sql="SELECT * FROM holdings",
                rows=[{"company": "A"}],
                row_count=1,
                status="success",
            )
        ],
    )

    result = Evaluator().evaluate(state)

    assert result["evaluation_scores"]["sql"] == 1.0
    assert result["evaluation_scores"]["coverage"] == 1.0
    assert result["confidence"] == 1.0
    assert result["human_review_required"] is False


def test_esg_evaluation_high_confidence():
    state = make_base_state(
        routing_decision="esg",
        vector_retrieved_context=[
            "SFDR Article 8 requirements."
        ],
        source_metadata=[
            SourceMetadata(
                source="SFDR",
                standard="SFDR",
                document_id="sfdr-article-8",
                score=0.9,
            )
        ],
    )

    result = Evaluator().evaluate(state)

    assert result["evaluation_scores"]["esg"] == 0.9
    assert result["evaluation_scores"]["coverage"] == 1.0
    assert result["confidence"] == 0.93
    assert result["human_review_required"] is False


def test_both_agents_are_evaluated():
    state = make_base_state(
        routing_decision="both",
        sql_execution_results=[
            SqlExecutionResult(
                sql="SELECT * FROM holdings",
                rows=[{"company": "A"}],
                row_count=1,
                status="success",
            )
        ],
        vector_retrieved_context=[
            "SFDR requirements."
        ],
        source_metadata=[
            SourceMetadata(
                source="SFDR",
                standard="SFDR",
                document_id="sfdr-article-8",
                score=0.8,
            )
        ],
    )

    result = Evaluator().evaluate(state)

    assert result["evaluation_scores"]["sql"] == 1.0
    assert result["evaluation_scores"]["esg"] == 0.8
    assert result["evaluation_scores"]["coverage"] == 1.0
    assert result["confidence"] == 0.93


def test_low_confidence_requires_human_review():
    state = make_base_state(
        routing_decision="esg",
        vector_retrieved_context=[
            "Weak ESG context."
        ],
        source_metadata=[
            SourceMetadata(
                source="Test",
                standard="Test",
                document_id="weak",
                score=0.2,
            )
        ],
    )

    result = Evaluator().evaluate(state)

    assert result["confidence"] == 0.44
    assert result["human_review_required"] is True


def test_missing_results_require_review():
    state = make_base_state(
        routing_decision="both",
    )

    result = Evaluator().evaluate(state)

    assert result["confidence"] == 0.0
    assert result["human_review_required"] is True


def test_unsupported_query_has_zero_confidence():
    state = make_base_state(
        routing_decision="unsupported",
    )

    result = Evaluator().evaluate(state)

    assert result["confidence"] == 0.0
    assert result["human_review_required"] is True