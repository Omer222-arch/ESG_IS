import os
import sqlite3

import pytest

from src.config import settings
from src.database import PortfolioDatabase, UnsafeSqlError, validate_read_only_sql
from src.sql_agent import analyze_sql, build_sql_prompt


class FakeLlm:
    def __init__(self, output: str) -> None:
        self.output = output
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.output


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "portfolio.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE holdings (company TEXT, esg_risk REAL)")
        conn.executemany("INSERT INTO holdings VALUES (?, ?)", [("Low", 2.0), ("High", 9.0)])
    return PortfolioDatabase(path)


def test_successful_llm_sql_generation(database):
    llm = FakeLlm("SELECT company, esg_risk FROM holdings ORDER BY esg_risk DESC")
    result = analyze_sql("Which companies have highest ESG risk?", database, llm=llm)
    assert result["status"] == "success"
    assert result["rows"][0]["company"] == "High"
    assert result["columns"] == ["company", "esg_risk"]
    assert "holdings(company TEXT, esg_risk REAL)" in llm.prompts[0]
    assert "Return ONLY one SQLite read-only SQL query" in llm.prompts[0]


@pytest.mark.parametrize("sql", [
    "INSERT INTO holdings VALUES ('x', 1)",
    "UPDATE holdings SET esg_risk = 1",
    "DELETE FROM holdings",
    "DROP TABLE holdings",
    "SELECT * FROM holdings; DELETE FROM holdings",
    "SELECT * FROM holdings -- bypass",
])
def test_unsafe_sql_is_rejected(sql):
    with pytest.raises(UnsafeSqlError):
        validate_read_only_sql(sql)


def test_select_and_with_queries_validate():
    assert validate_read_only_sql("SELECT * FROM holdings") == "SELECT * FROM holdings"
    assert validate_read_only_sql("WITH ranked AS (SELECT * FROM holdings) SELECT * FROM ranked")


def test_malformed_llm_output_is_rejected(database):
    result = analyze_sql("portfolio", database, llm=FakeLlm("Here is your query: SELECT * FROM holdings"))
    assert result["status"] == "rejected"
    assert result["sql"] == ""


def test_database_execution_failure_is_structured(database):
    result = analyze_sql("portfolio", database, llm=FakeLlm("SELECT * FROM missing_table"))
    assert result["status"] == "error"
    assert result["error"] == "SQL execution failed: no such table: missing_table"


def test_empty_result_is_structured(database):
    result = analyze_sql("portfolio", database, llm=FakeLlm("SELECT * FROM holdings WHERE esg_risk > 99"))
    assert result["status"] == "empty"
    assert result["row_count"] == 0


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY")
def test_real_llm_sql_generation_when_configured(database):
    result = analyze_sql("Which company has the highest ESG risk?", database, config=settings)
    assert result["status"] in {"success", "empty"}
