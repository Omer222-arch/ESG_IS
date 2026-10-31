"""LLM-driven, guarded natural-language-to-SQL portfolio analysis."""
from __future__ import annotations

from typing import Any, Protocol

from src.config import Settings, settings
from src.database import DatabaseError, PortfolioDatabase, UnsafeSqlError, validate_read_only_sql


class SqlGenerationError(RuntimeError):
    """A controlled failure at the LLM boundary."""


class SqlGenerator(Protocol):
    def generate(self, prompt: str) -> str: ...


def format_schema(schema: dict[str, list[dict[str, str]]]) -> str:
    lines: list[str] = []
    for table, columns in schema.items():
        definitions = ", ".join(
            f"{column['name']} {column.get('type', '')}" for column in columns
        )
        lines.append(f"{table}({definitions})")
    return "\n".join(lines)


def build_sql_prompt(query: str, schema: dict[str, list[dict[str, str]]]) -> str:
    return f"""You generate SQLite SQL for a portfolio analytics application.
Database schema:
{format_schema(schema)}

User question: {query}

Return ONLY one SQLite read-only SQL query. Do not use Markdown, code fences, comments,
explanations, semicolons, or multiple statements. The query must begin with SELECT or WITH,
and must never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, TRUNCATE,
ATTACH, DETACH, PRAGMA, or transaction-control statements."""


class OpenAISqlGenerator:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def generate(self, prompt: str) -> str:
        if not self.config.openai_api_key:
            raise SqlGenerationError("OPENAI_API_KEY is not configured; SQL generation is unavailable.")
        try:
            # Lazy import keeps local API startup independent of optional LLM packages.
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(
                model=self.config.openai_model,
                temperature=0,
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
            )
            response = model.invoke(prompt)
        except Exception as exc:
            raise SqlGenerationError("The SQL generation service is unavailable.") from exc

        content = response.content if hasattr(response, "content") else response
        if not isinstance(content, str):
            raise SqlGenerationError("The SQL generation service returned an invalid response.")
        return content.strip()


def _result(
    sql: str = "",
    rows: list[dict[str, Any]] | None = None,
    status: str = "error",
    error: str | None = None,
) -> dict[str, Any]:
    rows = rows or []
    return {
        "sql": sql,
        "columns": list(rows[0]) if rows else [],
        "rows": rows,
        "row_count": len(rows),
        "status": status,
        "error": error,
    }


def analyze_sql(
    query: str,
    database: PortfolioDatabase,
    config: Settings = settings,
    llm: SqlGenerator | None = None,
) -> dict[str, Any]:
    """Generate, validate, and execute one read-only query without leaking internals."""
    try:
        schema = database.discover_schema()
    except DatabaseError as exc:
        return _result(error=str(exc))
    if not schema:
        return _result(status="empty", error="No portfolio tables are available.")

    try:
        generated_sql = (llm or OpenAISqlGenerator(config)).generate(
            build_sql_prompt(query, schema)
        )
        if not generated_sql or "```" in generated_sql:
            raise SqlGenerationError("The SQL generator returned malformed output.")

        # Allow one conventional trailing SQL terminator only.
        normalized_sql = generated_sql.strip()
        if normalized_sql.endswith(";"):
            normalized_sql = normalized_sql[:-1].rstrip()

        sql = validate_read_only_sql(normalized_sql)
    except (SqlGenerationError, UnsafeSqlError) as exc:
        return _result(status="rejected", error=str(exc))

    try:
        rows = database.execute(sql)
    except DatabaseError as exc:
        return _result(sql=sql, error=str(exc))
    return _result(sql=sql, rows=rows, status="success" if rows else "empty")
