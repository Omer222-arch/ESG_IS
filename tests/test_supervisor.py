from src.supervisor import Supervisor


def test_routes_sql_query():
    result = Supervisor().route(
        "Show companies with revenue above 500 crore"
    )

    assert result["routing_decision"] == "sql"
    assert result["tasks_assigned"] == ["sql_analyst"]


def test_routes_esg_query():
    result = Supervisor().route(
        "What does SFDR Article 8 require?"
    )

    assert result["routing_decision"] == "esg"
    assert result["tasks_assigned"] == ["esg_compliance"]


def test_routes_combined_query():
    result = Supervisor().route(
        "Which portfolio companies are exposed to SFDR requirements?"
    )

    assert result["routing_decision"] == "both"
    assert "sql_analyst" in result["tasks_assigned"]
    assert "esg_compliance" in result["tasks_assigned"]


def test_routes_unsupported_query():
    result = Supervisor().route(
        "Write a Python game for me"
    )

    assert result["routing_decision"] == "unsupported"
    assert result["tasks_assigned"] == []


def test_empty_query_is_unsupported():
    result = Supervisor().route("   ")

    assert result["routing_decision"] == "unsupported"
    assert result["tasks_assigned"] == []