from src.human_review import HumanReviewManager
from src.state import ExecutionMetadata, GraphState


def make_state(confidence: float) -> GraphState:
    return GraphState(
        user_query="Test ESG query",
        execution_metadata=ExecutionMetadata(
            thread_id="review-test"
        ),
        confidence=confidence,
    )


def test_high_confidence_does_not_require_review():
    state = make_state(0.90)

    result = HumanReviewManager().request_review(state)

    assert result["human_review_required"] is False
    assert result["human_approved"] is True


def test_low_confidence_requires_review():
    state = make_state(0.50)

    result = HumanReviewManager().request_review(state)

    assert result["human_review_required"] is True
    assert result["human_approved"] is False


def test_approval():
    state = make_state(0.50)

    result = HumanReviewManager().approve(state)

    assert result["human_review_required"] is False
    assert result["human_approved"] is True


def test_rejection():
    state = make_state(0.50)

    result = HumanReviewManager().reject(state)

    assert result["human_review_required"] is True
    assert result["human_approved"] is False


def test_threshold_boundary():
    state = make_state(0.82)

    result = HumanReviewManager().request_review(state)

    assert result["human_review_required"] is False
    assert result["human_approved"] is True