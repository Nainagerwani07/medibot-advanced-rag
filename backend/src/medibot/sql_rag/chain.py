"""SQL RAG over mediassist.db (R5, NF1, D9).

    sql_rag_chain(question) -> str
      1. generate_sql:  LLM writes one SQLite SELECT from the schema + allowed values
      2. clean_sql:     strip fences / "SQLQuery:" / prose, keep one statement, SELECT/WITH only
      3. run_sql + LLM: execute read-only with a row cap, then phrase the rows as an answer

Access (R5.3) is checked by the caller (the chat service), from the JWT role.

Safety does not depend on the prompt: the connection is opened `mode=ro`, `PRAGMA query_only` is
on, only one SELECT/WITH statement passes `clean_sql`, and an authorizer denies anything that
isn't a read.
"""

import os
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from medibot.generation.llm import ANSWER_MODEL, FAST_MODEL, chat

REPO_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = Path(
    os.environ.get("MEDIBOT_DB", REPO_ROOT / "data" / "mediassist_data" / "db" / "mediassist.db")
)
MAX_ROWS = 50
SQL_ROLES = frozenset({"billing_executive", "admin"})  # R5.3

# Day 1 open items: category values must be listed, and "last month" means relative to the data.
_ENUM_COLUMNS = {
    "claims": ["department", "claim_type", "insurer", "status"],
    "maintenance_tickets": ["category", "campus", "issue_type", "status"],
}


class UnsafeSQLError(ValueError):
    """The LLM output wasn't a single read-only SELECT."""


@dataclass(frozen=True)
class SQLResult:
    question: str
    sql: str
    columns: list[str]
    rows: list[tuple]
    answer: str


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")

    def authorizer(action, *_):
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    conn.set_authorizer(authorizer)
    return conn


@lru_cache(maxsize=1)
def schema_description() -> str:
    """Schema + distinct values of low-cardinality columns + date range, for the NL->SQL prompt."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        parts = []
        for (ddl,) in conn.execute("SELECT sql FROM sqlite_master WHERE type='table'"):
            parts.append(re.sub(r"\s+", " ", ddl))
        for table, cols in _ENUM_COLUMNS.items():
            for col in cols:
                sql = f"SELECT DISTINCT {col} FROM {table} ORDER BY 1"  # noqa: S608 - fixed names
                vals = [v for (v,) in conn.execute(sql)]
                parts.append(f"{table}.{col} values: {', '.join(map(str, vals))}")
        lo, hi = conn.execute(
            "SELECT min(submitted_date), max(submitted_date) FROM claims"
        ).fetchone()
        parts.append(f"claims.submitted_date range: {lo} to {hi} (ISO text dates)")
        lo, hi = conn.execute(
            "SELECT min(raised_date), max(raised_date) FROM maintenance_tickets"
        ).fetchone()
        parts.append(f"maintenance_tickets.raised_date range: {lo} to {hi} (ISO text dates)")
        return "\n".join(parts)
    finally:
        conn.close()


SQL_SYSTEM = """You translate questions into ONE SQLite SELECT statement for this database:

{schema}

Rules:
- Return only the SQL, no explanation.
- Use only the tables and columns above; match category values exactly as listed.
- Relative dates ("last month", "this year") are relative to the latest date in the data, not today.
- Amounts are in Indian rupees. Round averages to 2 decimals.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH or PRAGMA."""

ANSWER_SYSTEM = """You answer a hospital billing/operations question from an SQL result.
Use only the rows given. State numbers exactly (amounts in ₹). If the result is empty, say that no
matching records were found. Be concise. Do not mention SQL unless asked."""


def generate_sql(question: str, model: str = FAST_MODEL) -> str:
    """Step 1: NL -> raw LLM output (may contain fences or prose)."""
    return chat(SQL_SYSTEM.format(schema=schema_description()), question, model=model)


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


def clean_sql(raw: str) -> str:
    """Step 2: reduce LLM output to one SELECT/WITH statement, or raise UnsafeSQLError."""
    text = raw.strip()
    fenced = re.search(r"```(?:sql|sqlite)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    text = re.sub(r"^\s*(SQLQuery|SQL|Query)\s*:\s*", "", text, flags=re.IGNORECASE)
    # SELECT, or a real CTE ("WITH name AS ("), not the English word "with" in prose
    start = re.search(r"\bselect\b|\bwith\s+(recursive\s+)?\w+\s+as\s*\(", text, re.IGNORECASE)
    if not start:
        raise UnsafeSQLError(f"no SELECT in LLM output: {raw[:200]!r}")
    text = text[start.start() :]
    statements = [s.strip() for s in text.split(";") if s.strip()]
    if len(statements) != 1:
        raise UnsafeSQLError("expected exactly one SQL statement")
    sql = statements[0]
    if _FORBIDDEN.search(sql):
        raise UnsafeSQLError(f"write/DDL keyword in SQL: {sql[:200]!r}")
    return sql


def run_sql(sql: str, max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple]]:
    """Step 3a: execute on a read-only connection; at most `max_rows` rows."""
    conn = _connect()
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description or []]
        return cols, cur.fetchmany(max_rows)
    except sqlite3.DatabaseError as e:
        raise UnsafeSQLError(f"query failed: {e}") from e
    finally:
        conn.close()


def sql_rag(question: str) -> SQLResult:
    sql = clean_sql(generate_sql(question))
    cols, rows = run_sql(sql)
    table = "\n".join([" | ".join(cols)] + [" | ".join(map(str, r)) for r in rows])
    note = f"\n(showing first {MAX_ROWS} rows)" if len(rows) == MAX_ROWS else ""
    answer = chat(
        ANSWER_SYSTEM,
        f"Question: {question}\n\nSQL: {sql}\n\nResult:\n{table or '(no rows)'}{note}",
        model=ANSWER_MODEL,
    )
    return SQLResult(question, sql, cols, rows, answer)


def sql_rag_chain(question: str) -> str:
    """R5.2: the plain function the brief asks for."""
    try:
        return sql_rag(question).answer
    except UnsafeSQLError as e:
        return f"I couldn't run a safe query for that question ({e})."
