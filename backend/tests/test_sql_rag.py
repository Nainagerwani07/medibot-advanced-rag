"""SQL RAG safety (R5.2 step 2, NF1, D9): cleaning LLM output, read-only execution. No LLM."""

import pytest

from medibot.sql_rag import chain
from medibot.sql_rag.chain import UnsafeSQLError, clean_sql, run_sql

needs_db = pytest.mark.skipif(not chain.DB_PATH.exists(), reason="dataset not unzipped")


@pytest.mark.parametrize(
    "raw",
    [
        "SELECT status, COUNT(*) FROM claims GROUP BY status",
        "```sql\nSELECT status, COUNT(*) FROM claims GROUP BY status;\n```",
        "SQLQuery: SELECT status, COUNT(*) FROM claims GROUP BY status;",
        "Here it is:\n```\nSELECT status, COUNT(*) FROM claims GROUP BY status\n```\nDone.",
        "Sure! SELECT status, COUNT(*) FROM claims GROUP BY status;",
    ],
)
def test_clean_sql_extracts_the_statement(raw):
    assert clean_sql(raw) == "SELECT status, COUNT(*) FROM claims GROUP BY status"


def test_clean_sql_keeps_cte():
    sql = "WITH t AS (SELECT * FROM claims) SELECT count(*) FROM t"
    assert clean_sql(f"```sql\n{sql}\n```") == sql


@pytest.mark.parametrize(
    "raw",
    [
        "DROP TABLE claims",
        "SELECT 1; DROP TABLE claims",
        "SELECT * FROM claims; DELETE FROM claims",
        "UPDATE claims SET status = 'approved'",
        "WITH x AS (DELETE FROM claims RETURNING *) SELECT * FROM x",
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "I can't help with that.",
        "",
    ],
)
def test_clean_sql_rejects_anything_but_one_select(raw):
    with pytest.raises(UnsafeSQLError):
        clean_sql(raw)


@needs_db
def test_run_sql_returns_rows():
    cols, rows = run_sql("SELECT status, COUNT(*) AS n FROM claims GROUP BY status ORDER BY 1")
    assert cols == ["status", "n"]
    assert ("approved", 44) in rows


@needs_db
def test_run_sql_caps_rows():
    _, rows = run_sql("SELECT * FROM claims", max_rows=5)
    assert len(rows) == 5


@needs_db
@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM claims",
        "UPDATE claims SET status = 'x'",
        "CREATE TABLE t (x)",
        "ATTACH DATABASE ':memory:' AS m",
    ],
)
def test_connection_is_read_only_even_if_cleaning_is_bypassed(sql):
    """Second layer: the SQLite connection itself refuses writes (mode=ro + authorizer)."""
    with pytest.raises(UnsafeSQLError):
        run_sql(sql)
    _, rows = run_sql("SELECT COUNT(*) FROM claims")
    assert rows == [(85,)]


@needs_db
def test_schema_description_lists_allowed_values_and_dates():
    desc = chain.schema_description()
    assert "general_medicine" in desc and "escalated" in desc
    assert "2024-12-19" in desc  # latest claim date, for "last month" questions


def test_only_billing_and_admin_may_use_sql():
    assert frozenset({"billing_executive", "admin"}) == chain.SQL_ROLES
