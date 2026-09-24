# Roadmap & Progress

Pace: **about 2 hours per day**, one step per day. Each session: ~20 min on the concept and why we need it,
~80 min building, ~20 min checking the output and recapping.

Status legend: ⬜ not started · 🟡 in progress · ✅ done

| Day | Status | Focus | Concepts learned | Done when | Reqs |
|---|---|---|---|---|---|
| 0 | ✅ | Requirements, architecture, repo docs | Reading a brief as testable requirements | `docs/` + `CLAUDE.md` in repo | — |
| 1 | ⬜ | Env setup + data exploration | Why fixed-size chunking hurts medical docs; project layout | venv, deps, Qdrant container up, Groq key works, dataset in `data/`, DB schema looked at | NF2, NF3, R5.1 |
| 2 | ⬜ | Docling parsing | DoclingDocument tree, layout & table models, OCR on/off | Parsed structure of every file inspected (headings, tables, the `.md` file) | R2.1 |
| 3 | ⬜ | HybridChunker + metadata | Structure-first then token splitting; tokenizer alignment; `contextualize()` | Chunks printed with heading context + all 5 metadata fields; chunk_type correct for tables | R2.2–R2.4 |
| 4 | ⬜ | Embeddings + Qdrant indexing | Dense vs sparse vectors, BM25/IDF, named vectors, payload indexes | `scripts/ingest.py` loads everything into Qdrant; counts per collection check out | R2.5, R3.1 |
| 5 | ⬜ | Hybrid retrieval + RBAC filter | Prefetch, RRF fusion, why filtering happens inside the search | One `query_points` call does hybrid + filter; nurse can never get billing chunks | R1.1, R3.2, R3.3 |
| 6 | ⬜ | Eval set + cross-encoder rerank | Bi- vs cross-encoder; hit@k, MRR | Table comparing dense-only / hybrid / hybrid+rerank; reranker scores logged | R3.5, R4 |
| 7 | ⬜ | Grounded generation + SQL RAG | Grounded prompts, citations, text-to-SQL pitfalls, read-only execution | Answers with citations; `sql_rag_chain` correct on ≥4 questions | R3.4, R5 |
| 8 | ⬜ | Router + FastAPI + JWT | Server-side authorization, dependency injection | All 4 endpoints work with curl; role taken from token | R1.4, R6 |
| 9 | ⬜ | Adversarial RBAC testing | Prompt injection vs retrieval-layer security | ≥3 documented attacks + pytest suite passing | R1.2, R1.3, NF4 |
| 10 | ⬜ | Next.js UI | — | Login, role badge, collections, citations, retrieval label, refusal message | R7 |
| 11 | ⬜ | README polish, diagram, screenshots, submit | — | Public repo link submitted | R8 |

## Session log

Add one entry at the end of each session: what was done, what we learned, what's open.

### Day 0 — 2026-09-24
- Read the assignment brief and turned it into [REQUIREMENTS.md](REQUIREMENTS.md).
- Agreed on the architecture ([ARCHITECTURE.md](ARCHITECTURE.md)) and the decisions D1–D9 ([DECISIONS.md](DECISIONS.md)).
- Created `CLAUDE.md` so new sessions can resume without this conversation.
- **Next:** Day 1 — environment setup and data exploration.
