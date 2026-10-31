"""Read-only SQLite access for portfolio analysis."""
from __future__ import annotations
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

class DatabaseError(RuntimeError): pass
class UnsafeSqlError(DatabaseError): pass
_COMMENT = re.compile(r"(?:--[^\n]*|/\*.*?\*/)", re.DOTALL)
_BLOCKED = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|vacuum|reindex|pragma|grant|revoke|begin|commit|rollback|savepoint|release|end)\b", re.I)

def validate_read_only_sql(sql: str) -> str:
    if _COMMENT.search(sql): raise UnsafeSqlError("SQL comments are not allowed")
    statement = sql.strip()
    if not statement: raise UnsafeSqlError("SQL statement is empty")
    if ";" in statement: raise UnsafeSqlError("SQL terminators and multiple statements are not allowed")
    if not re.match(r"^(select|with)\b", statement, re.I): raise UnsafeSqlError("Only SELECT or WITH queries are allowed")
    if _BLOCKED.search(statement): raise UnsafeSqlError("Mutating or administrative SQL is not allowed")
    if re.match(r"^with\b", statement, re.I) and not re.search(r"\bselect\b", statement, re.I): raise UnsafeSqlError("WITH queries must contain a SELECT statement")
    return statement

class PortfolioDatabase:
    def __init__(self, path: Path) -> None: self.path = path
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if not self.path.exists(): raise DatabaseError(f"Portfolio database does not exist: {self.path}")
        try:
            conn = sqlite3.connect(f"file:{self.path.resolve().as_posix()}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc: raise DatabaseError(f"Database operation failed: {exc}") from exc
        try:
            yield conn
        finally:
            conn.close()
    def discover_schema(self) -> dict[str, list[dict[str, str]]]:
        with self.connection() as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            return {table["name"]: [dict(row) for row in conn.execute(f'PRAGMA table_info("{table["name"].replace(chr(34), chr(34) * 2)}")')] for table in tables}
    def execute(self, sql: str) -> list[dict[str, object]]:
        try:
            with self.connection() as conn: return [dict(row) for row in conn.execute(validate_read_only_sql(sql)).fetchall()]
        except sqlite3.Error as exc: raise DatabaseError(f"SQL execution failed: {exc}") from exc
