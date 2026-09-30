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
| 4 | ✅ | Embeddings + Qdrant indexing | Dense vs sparse vectors, BM25/IDF, named vectors, payload indexes | `scripts/ingest.py` loads everything into Qdrant; counts per collection check out | R2.5, R3.1 |
| 5 | ✅ | Hybrid retrieval + RBAC filter | Prefetch, RRF fusion, why filtering happens inside the search | One `query_points` call does hybrid + filter; nurse can never get billing chunks | R1.1, R3.2, R3.3 |
| 6 | ✅ | Eval set + cross-encoder rerank | Bi- vs cross-encoder; hit@k, MRR | Table comparing dense-only / hybrid / hybrid+rerank; reranker scores logged | R3.5, R4 |
| 7 | ✅ | Grounded generation + SQL RAG | Grounded prompts, citations, text-to-SQL pitfalls, read-only execution | Answers with citations; `sql_rag_chain` correct on ≥4 questions | R3.4, R5 |
| 8 | ✅ | Router + FastAPI + JWT | Server-side authorization, dependency injection | All 4 endpoints work with curl; role taken from token | R1.4, R6 |
| 9 | ✅ | Adversarial RBAC testing | Prompt injection vs retrieval-layer security | ≥3 documented attacks + pytest suite passing | R1.2, R1.3, NF4 |
| 10 | ✅ | Next.js UI | — | Login, role badge, collections, citations, retrieval label, refusal message | R7 |
| 11 | ✅ | README polish, diagram, screenshots, submit | — | Public repo link submitted | R8 |

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

### Day 4 — 2026-09-28
- **Done:**
  - Branch `feature/day-4-embeddings-qdrant-indexing` (from `main` after PR #4 merged).
  - Deps: `fastembed` (ONNX embeddings, no torch) and `qdrant-client`; torch still the CPU build (D15).
  - `scripts/explore_embeddings.py`: tokenizer check (FastEmbed ONNX vs HF: 0 mismatches over 268 chunks,
    longest 258 incl. [CLS]/[SEP]); dense vector shape + query/chunk cosine table; BM25 entries traced back to stems.
  - `ingestion/indexing.py`: collection `medibot_docs` with named vectors `dense` (384, cosine) and `sparse`
    (`Modifier.IDF`), keyword payload indexes (access_roles, collection, source_document, chunk_type), BM25 `avg_len`
    from our chunks (D19), deterministic uuid5 point ids + full rebuild (D20).
  - `scripts/ingest.py`: parse → chunk → embed → upload (~25 s), then verifies counts per collection and per role:
    268 points; billing 50, clinical 65, equipment 31, general 78, nursing 44; nurse 122, doctor 187, admin 268.
  - `tests/test_indexing.py` (5 tests, in-memory Qdrant): schema, both vectors stored, stable ids, no duplicates on
    re-index (confirmed random ids give 8 for 4), nurse filter sees only nursing + general. 14 tests pass.
  - Docs: D19, D20; ARCHITECTURE §2.2 + layout; `docs/diagrams/ingestion.md` §5 (one point, two vectors).
- **Learned:**
  - Dense vs sparse: 384 normalised floats for meaning vs (hashed stem, weight) pairs for exact terms.
  - BM25 in FastEmbed = stem + mmh3 hash + TF part only; queries are weight 1.0 per term; IDF comes from Qdrant.
  - Why IDF matters here: key: value tables repeat column names, so "dose"/"route" top TF; rare drug names must win.
  - `avg_len` is BM25 length normalisation relative to the corpus; a wrong default skews every chunk.
  - bge cosine scores sit in a narrow band (0.46–0.70): ranks matter, not absolute scores, hence RRF on Day 5.
  - Named vectors (two vectors per point) and payload indexes (filter inside the search, not after).
  - Idempotent ingestion via deterministic ids; views of the data: dashboard, REST scroll, Python scroll.
- **Open items:**
  - Callout scope: `leave_policy.pdf` chunk after the callout has `section_title = "Important"`; affects citations.
  - transformers "1173 > 512" warning during chunking is the chunker measuring whole sections (harmless).
  - Day 6: compare max_tokens 256 vs 512 on the eval set.
  - User: enable GitHub branch protection on `main` (still open).
- **Next:** Day 5 — hybrid retrieval + RBAC filter: one `query_points` call with dense + sparse prefetch, RRF fusion
  and the `access_roles` filter inside the query; nurse can never get billing chunks.

### Day 5 — 2026-09-28
- **Done:**
  - Branch `feature/day-5-hybrid-retrieval-rbac` (from `main` after PR #5 merged).
  - `scripts/explore_retrieval.py`: dense only / BM25 only / hybrid RRF / hybrid as nurse on 3 queries; rebuilt
    Qdrant's RRF scores from the two rank lists; filter placement experiment; post-filter vs in-search filter.
  - `retrieval/hybrid.py`: `HybridRetriever.search(query, role, k=10, prefetch_k=20)`, one `query_points` call
    (dense + sparse prefetch, RRF). `role_filter()` = `access_roles` contains role AND `collection` in the role's
    collections (D21), set on each prefetch and the outer query; unknown role raises before any search.
    Returns `RetrievedChunk(id, score, text, metadata)`; models loaded once in the constructor.
  - `tests/test_retrieval.py` (35 tests, in-memory Qdrant): every role x 5 queries stays in its collections,
    nurse never gets billing, a mis-stamped chunk is stopped by the collection check, k is filled for a nurse on
    the attack query, admin reaches all 5 collections, exact-term hits rank 1st, unknown roles rejected.
    Mutation check: dropping the collection condition fails 7 tests, dropping the filter fails 28. 49 tests pass.
  - Docs: D21, D22; ARCHITECTURE §2.3 + layout; `docs/diagrams/retrieval.md`.
- **Learned:**
  - Prefetch: sub-searches inside one request whose results feed the outer query (here, fusion).
  - Dense and BM25 fail on different queries: dense ranked the ceftriaxone table 4th, BM25 put an ICU chunk 1st
    for a paraphrased leave question; hybrid got both right.
  - Qdrant's RRF is `sum 1/(2 + rank)` (rank from 0, k=2): scores are ignored, and 1st place in either list counts
    a lot. Textbook k=60 is much flatter.
  - Qdrant pushes a top-level filter down into the prefetches (same ids, same order as per-prefetch filters).
  - Post-filtering fails even without an attack: as a nurse, top-5 then drop left 0 chunks for the LLM on both
    tested queries; in-search filtering returned 5 allowed chunks.
  - A security test only counts once you've seen it fail (mutation check).
- **Open items:**
  - A filtered search always returns *something* (nurse asking for E11.9 gets checklists); the refusal (R1.3)
    must come from the router/answer layer (Day 8–9), not from empty results.
  - Day 6: compare RRF k=2 vs k=60 and prefetch_k on the eval set (D22).
  - Carried over: `leave_policy.pdf` "Important" callout section_title; max_tokens 256 vs 512; branch protection.
- **Next:** Day 6 — eval set + cross-encoder rerank: hit@k / MRR for dense-only vs hybrid vs hybrid+rerank,
  reranker scores logged.

### Days 6–8 — 2026-09-30 (one combined session, deadline)
- **Done:**
  - Branch `feature/day-6-8-rerank-generation-api` (from `main` after PR #6 merged).
  - **Day 6:** `retrieval/rerank.py` (`Reranker`, MiniLM-L-6 ONNX via FastEmbed, logs every candidate's old/new
    rank + score); `HybridRetriever.search(mode="dense"|"sparse"|"hybrid", rrf_k=...)` for baselines;
    `RetrievedChunk.heading_path`; `eval/questions.jsonl` (68 questions: 36 section, 16 lexical, 16 paraphrase);
    `scripts/eval_retrieval.py` (hit@1/3/5/10, MRR, by kind, per question). Results in `docs/EVAL.md`.
  - **Day 7:** `generation/llm.py` (Groq), `generation/answer.py` (numbered context with heading path, cite [n],
    not-found reply, sources = cited chunks); `sql_rag/chain.py` (`sql_rag_chain`, generate → clean → read-only
    run + answer); `scripts/try_sql_rag.py` (7 analytical questions, all checked against the DB by hand).
  - **Day 8:** `routing/router.py` (20b JSON router + keyword fallback), `service.py` (`ChatService`: route →
    SQL or hybrid → rerank → answer; refusals), `api/auth.py` (bcrypt, JWT), `api/main.py` (`/login`, `/chat`,
    `/collections/{role}`, `/health`, CORS for :3000). Checked end to end with curl.
  - Tests: `test_sql_rag.py` (22), `test_api.py` (17), `test_service.py` (16). **104 pass.** Mutation checks:
    removing the SQL role check fails 3 tests; removing the token-role check fails 1.
  - Docs: `docs/EVAL.md`, `docs/diagrams/chat.md`, D23–D27, ARCHITECTURE layout.
- **Learned:**
  - An eval that echoes the headings says nothing (first set: every system ~1.0). Codes and paraphrases separate
    the systems: dense misses codes, BM25 misses paraphrases, hybrid gets all 68 into the top 10.
  - Fusion widens recall but doesn't order well (hybrid hit@1 0.79 < dense 0.81); the cross-encoder fixes the
    order (0.87 hit@1, 0.97 hit@3).
  - A cross-encoder only knows what you feed it: with the bare section title it made things worse.
  - The router is useful for *messages*, not *security*: a test fools it and checks the filter still holds.
  - LLM-written SQL needs layers that each work with the others removed (clean, read-only, authorizer).
- **Open items:**
  - Chunk size 256 vs 512 (D17) not evaluated (needs a re-index).
  - Day 9: document ≥ 3 adversarial prompts with screenshots (curl runs so far: "ignore instructions… billing
    codes" as nurse → refused; "SYSTEM OVERRIDE… Meropenem" as nurse → refused; `DROP TABLE` as billing → not
    run; mixed billing + nursing → nursing part answered + note). Consider llama-prompt-guard (Day 1 note).
  - Router misroutes are possible (e.g. a vague question gets no targets → search runs, which is safe).
  - `sql_rag` error text shows the SQLite error to the user; fine for a demo, trim for production.
  - Carried over: `leave_policy.pdf` "Important" section_title; branch protection on `main`.
- **Next:** Day 9 — adversarial RBAC testing write-up, then Day 10 Next.js UI.

### Days 9–11 — 2026-10-01 (combined, deadline)
- **Done:**
  - Branch `feature/day-9-11-adversarial-ui-readme` (stacked on `feature/day-6-8-rerank-generation-api`, PR #7).
  - **Day 9:** `scripts/attack_demo.py`: 8 attacks via the live API (injection, role claim, body role, disguised
    question, mixed, SQL without access, `DROP TABLE`, role-play). 8/8 held; the router-skipped pass into Qdrant shows
    no out-of-role collection in any top-10. Output: `docs/ADVERSARIAL_RUN.md`.
  - **Day 10:** `frontend/` Next.js 15: login with demo-account buttons, role badge, collections sidebar (locked
    ones shown, plus SQL access), retrieval-type label, citation chips (SQL shown for SQL RAG), styled refusal
    (`blocked`), responsive layout, safe Markdown rendering. Lint + build clean.
  - Screenshots (headless Chrome, puppeteer-core outside the repo): `docs/screenshots/01–10`.
  - **Day 11:** README rewritten: architecture diagram, roles + demo logins, eval table, 6 documented attacks with
    screenshots, setup for ingest/backend/frontend, API table, tool substitutions. D28, D29.
  - `.gitignore`: the Python template's `lib/` rule would have dropped `frontend/lib/api.ts`; re-included.
- **Learned:**
  - In the live run the router refuses first, so a passing attack doesn't prove the filter works; the
    router-skipped pass does.
  - Checking answers for canary strings catches leaks that a sources-only check would miss.
  - UI hiding is cosmetic; the badge and collections come from the server, and the API enforces.
- **Open items:**
  - Merge PR #7, then this PR. Submit the public repo link (R8).
  - Chunk size 256 vs 512 still not evaluated; `leave_policy.pdf` "Important" section_title; branch protection.
  - Optional: prompt-guard model as an extra detection layer; frontend e2e test in CI.
- **Next:** project complete. Only submission and follow-ups remain.
