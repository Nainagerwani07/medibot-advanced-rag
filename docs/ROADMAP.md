# Roadmap & Progress

Pace: **about 2 hours per day**, one step per day. Each session: ~20 min on the concept and why we need it,
~80 min building, ~20 min checking the output and recapping.

Status legend: ⬜ not started · 🟡 in progress · ✅ done

| Day | Status | Focus | Concepts learned | Done when | Reqs |
|---|---|---|---|---|---|
| 0 | ✅ | Requirements, architecture, repo docs | Reading a brief as testable requirements | `docs/` + `CLAUDE.md` in repo | — |
| 1 | ✅ | Env setup + data exploration | Why fixed-size chunking hurts medical docs; project layout | venv, deps, Qdrant container up, Groq key works, dataset in `data/`, DB schema looked at | NF2, NF3, R5.1 |
| 2 | ✅ | Docling parsing | DoclingDocument tree, layout & table models, OCR on/off | Parsed structure of every file inspected (headings, tables, the `.md` file) | R2.1 |
| 3 | ✅ | HybridChunker + metadata | Structure-first then token splitting; tokenizer alignment; `contextualize()` | Chunks printed with heading context + all 5 metadata fields; chunk_type correct for tables | R2.2–R2.4 |
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

### Day 1 — 2026-09-25
- **Done:**
  - Branch `feature/day-1-env-setup`. uv project in `backend/` (Python 3.12, src layout, ruff + pytest config).
  - pre-commit: gitleaks (+ custom Groq-key rule), ruff, large-file, private-key, no-commit-to-main.
  - Claude hooks (branch guard on git commit/push, ruff after edits) and `/start-session`, `/end-session` skills.
  - Qdrant v1.19.1 via docker-compose (localhost-only, named volume). `.env.example` + gitignored `.env`.
  - Groq key checked; models listed; generation tested on gpt-oss-20b / 120b.
  - Dataset unzipped to `data/` and profiled (12 docs, all digital PDFs, ~14k words; DB: `claims` 85 rows,
    `maintenance_tickets` 78 rows).
  - Decisions D10–D14 recorded; D1 updated (model list).
- **Learned:**
  - uv: `pyproject.toml` (asked-for ranges) vs `uv.lock` (exact resolution); `uv run` syncs before running.
  - Git hooks vs Claude hooks: git hooks guard every commit; Claude hooks guard Claude's tool calls (incl. push).
  - Test your safety tools: default gitleaks missed a bare API key.
  - Scope lint exceptions narrowly: bandit's subprocess warnings are ignored only for dev-tool hook scripts.
  - Plain PDF text breaks tables (wrapped cells) and repeats headers/footers, which is why we use Docling.
  - Look at the data before designing: DB dates are all 2024, categories are lowercase snake_case.
- **Open items:**
  - Day 7: "last month" questions must be relative to the data's date range (2024), not today.
  - Day 7: NL→SQL prompt must list allowed category values (`escalated`, `general_medicine`, …).
  - Day 7: brief gives SQL RAG only to billing/admin, so technicians can't query `maintenance_tickets`. Decide and log.
  - Day 9: consider `llama-prompt-guard-2-86m` (on Groq) as an extra injection-detection layer, not the boundary.
  - User: enable GitHub branch protection on `main` after this PR merges.
- **Next:** Day 2 — Docling parsing: inspect the DoclingDocument tree (headings, tables, page header/footer
  labels) for every file, including the `.md` guide.

### Day 2 — 2026-09-27
- **Done:**
  - Branch `feature/day-2-docling-parsing` (from `main` after PR #1 merged).
  - `uv add docling` (2.130.0). torch/torchvision switched to CPU-only wheels (D15): venv 5.9 GB → 1.5 GB.
  - `backend/scripts/explore_docling.py`: parses one file (OCR off, table structure on); prints the element tree
    with content layer / label / heading level / page, tables as DataFrames, optional Markdown export.
  - `backend/scripts/inspect_all.py`: parses all 12 files (~198 s total on CPU); per-file label counts, heading levels,
    tables, unnumbered headings. Caches DoclingDocument JSON + tree text in `data/parsed/` (gitignored).
  - Checked PDF font sizes of every Docling heading (pypdfium2, scratchpad script): consistent across all 11 PDFs.
- **Learned:**
  - DoclingDocument is a typed tree (title, section_header, text, list_item, table, code, footnote), not a string.
  - Layout model classifies page regions; TableFormer rebuilds rows/columns (wrapped cells rejoined; 53 tables intact).
  - Content layers: page headers/footers go to `FURNITURE`, real content to `BODY`, so no regex cleanup is needed.
  - OCR off: digital PDFs already have an exact text layer; OCR only adds CPU time and character errors.
  - Docling detects PDF headings but not their depth (all L1); callout labels ("Important", "Red flags") look like headings.
  - Test a rule on the whole dataset: numbering-based levels would fail on 6/11 PDFs; font size is consistent.
  - Markdown input keeps real `#` levels; fenced blocks become `code` items (R2.1 code blocks).
  - Check the default build of ML dependencies: torch installed as CUDA on a CPU-only machine.
- **Open items:**
  - Day 3: implement font-size heading levels (D16) before HybridChunker. Edge cases: equipment manual title didn't
    match by text (needs fallback); bold `ICD-10: A90…` line in treatment_protocols is labelled a heading.
  - Day 3: inline code in the `.md` (`billing_codes.pdf`) becomes separate `code` items; make sure chunks keep them in their sentence
    and `chunk_type` isn't set to `code` for them.
  - Day 3: `diagnostic_reference` has 2 `footnote` items; decide chunk_type (probably text).
  - User: enable GitHub branch protection on `main` (still open from Day 1).
- **Next:** Day 3 — HybridChunker + metadata, starting from the cached `data/parsed/*.json` and the heading-level fix.

### Day 3 — 2026-09-28
- **Done:**
  - Branch `feature/day-3-hybridchunker-metadata` (from `main` after PR #2 merged).
  - `ingestion/headings.py`: PDF heading levels from the font size inside each heading's bbox (D16); all 241 matched.
  - `scripts/section_profile.py`: token size of every section/table → `max_tokens = 256` (D17).
  - `rbac.py`: role → collections map (single source of truth); `access_roles` derived per collection.
  - `ingestion/chunking.py`: HybridChunker (bge tokenizer, 256, merge_peers), `KeyValueRowTableSerializer` and
    `_HeadingAwareChunker` for row-aligned table splits within budget (D18); `Chunk(text, embed_text, metadata)`.
  - `ingestion/parsing.py`: shared converter, cached PDF parse + heading fix, Markdown inline cleanup (`load_document()`).
  - `scripts/show_chunks.py`, `scripts/check_headings.py`; first tests `tests/test_chunking.py` (9 passing; confirmed
    the table test fails without the budget fix).
  - Result: 268 chunks (194 text, 73 table, 1 code), all ≤ 256 tokens, 0 missing metadata.
  - Diagrams: `docs/diagrams/ingestion.md` (pipeline, content layers, heading stack, table formats); ARCHITECTURE updated.
  - Follow-up (`feature/day-3-chunks-export`): `show_chunks.py` also writes all chunks to `data/chunks.jsonl`
    (gitignored; index, tokens, metadata, text, embed_text) for browsing and diffing chunking changes.
- **Learned:**
  - Heading stack: a level-L heading drops every entry at level ≥ L; flat levels make each heading replace the last.
  - Tokenizer alignment: count with the embedding model's tokenizer; medical terms split into many subwords, `----` is costly.
  - Two passes: structure first, then tokens; the limit should only bite where structure gives big units (tables).
  - Serialisation is a retrieval decision: how a table is written decides where it can split and what gets embedded.
  - Read the library source before overriding it; verify a guard test fails without the fix.
  - Decision practice: profile, measure the options, choose, record (D17, D18); chunking-strategy interview answer.
- **Open items:**
  - Callout scope: text after a callout box (same section) inherits the callout label; not seen in this data, watch it.
  - Day 4: check FastEmbed's bge-small ONNX tokenizer matches the HF tokenizer we counted with.
  - Day 4: `load_document()` re-parses PDFs if `data/parsed/` is missing (~200 s); fine for `ingest.py`.
  - Day 6: compare max_tokens 256 vs 512 on the eval set.
  - User: enable GitHub branch protection on `main` (still open).
- **Next:** Day 4 — embeddings + Qdrant indexing: dense (bge-small) + sparse (BM25) named vectors, payload indexes,
  `scripts/ingest.py` loading all 268 chunks.
