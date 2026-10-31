from src.graph import create_graph
from src.state import (
    ExecutionMetadata,
    GraphState,
    SqlExecutionResult,
)


def make_state(query: str) -> GraphState:
    return GraphState(
        user_query=query,
        execution_metadata=ExecutionMetadata(
            thread_id="graph-test"
        ),
    )


def fake_sql_runner(state):
    return {
        "sql_query": "SELECT company, revenue FROM holdings",
        "sql_execution_results": [
            SqlExecutionResult(
                sql="SELECT company, revenue FROM holdings",
                rows=[
                    {
                        "company": "Company A",
                        "revenue": 500,
                    }
                ],
                row_count=1,
                status="success",
            )
        ],
    }


def test_graph_sql_path():
    graph = create_graph(sql_runner=fake_sql_runner)

    config = {
        "configurable": {
            "thread_id": "sql-test"
        }
    }

    result = graph.invoke(
        make_state(
            "Show companies with revenue above 100 crore"
        ),
        config,
    )

    assert result["routing_decision"] == "sql"
    assert result["sql_execution_results"]
    assert result["final_synthesis_report"]
    assert result["evaluation_scores"]


def test_graph_esg_path():
    graph = create_graph(sql_runner=fake_sql_runner)

    config = {
        "configurable": {
            "thread_id": "esg-test"
        }
    }

    result = graph.invoke(
        make_state(
            "What does SFDR Article 8 require?"
        ),
        config,
    )

    assert result["routing_decision"] == "esg"
    assert result["vector_retrieved_context"]
    assert result["final_synthesis_report"]


def test_graph_unsupported_path():
    graph = create_graph(sql_runner=fake_sql_runner)

    config = {
        "configurable": {
            "thread_id": "unsupported-test"
        }
    }

    result = graph.invoke(
        make_state(
            "Write a Python game"
        ),
        config,
    )

    assert result["routing_decision"] == "unsupported"
    assert result["final_synthesis_report"]