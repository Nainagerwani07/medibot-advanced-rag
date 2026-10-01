"""Day 7: run sql_rag on analytical questions and show SQL + rows + answer (R5.4).

Run from backend/:  set -a; . ../.env; set +a; uv run python scripts/try_sql_rag.py
"""

from medibot.sql_rag.chain import UnsafeSQLError, sql_rag

QUESTIONS = [
    "How many claims are in each status?",
    "What is the total claimed amount and total approved amount per insurer?",
    "Which department has the highest rejection rate?",
    "What is the average approved amount for cashless vs reimbursement claims?",
    "How many claims were submitted last month?",
    "Which equipment category has the most open or escalated maintenance tickets?",
    "List the escalated maintenance tickets at Hyderabad Central.",
]

for q in QUESTIONS:
    print("=" * 100, f"\nQ: {q}")
    try:
        r = sql_rag(q)
    except UnsafeSQLError as e:
        print("  BLOCKED:", e)
        continue
    print(f"SQL: {r.sql}")
    print(f"rows ({len(r.rows)}): {r.rows[:6]}{' ...' if len(r.rows) > 6 else ''}")
    print(f"A: {r.answer}")
