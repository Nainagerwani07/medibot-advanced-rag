# Retrieval evaluation (Day 6, R3.5, R4, NF5)

Run: `cd backend && uv run python scripts/eval_retrieval.py` (add `--show-rerank` to log every reranker score).
Questions: `backend/eval/questions.jsonl`. 68 questions, each asked **under its own role** (the RBAC filter is on,
as in production). A question counts as answered at rank *r* when the chunk at rank *r* has the expected
`source_document` + `section_title` (and, for split tables, contains the expected row, e.g. `K40.9`).

Three kinds of question:
- **section** (36): wording close to the section heading. Easy for everything; a sanity check.
- **lexical** (16): an exact code or drug name inside a large table (`K40.9`, `PROC-ORTH-02`, `Colistin`, `F-09`).
- **paraphrase** (16): none of the heading's words ("which bin do used needles go in?" → *7. Waste Segregation*).

## Results (2026-09-30, MiniLM-L-6 reranker scores heading path + text)

| system | hit@1 | hit@3 | hit@5 | hit@10 | MRR | ms/query |
|---|---|---|---|---|---|---|
| dense only | 0.81 | 0.93 | 0.94 | 0.96 | 0.868 | 13 |
| BM25 only | 0.78 | 0.90 | 0.93 | 0.96 | 0.844 | 7 |
| hybrid RRF k=2 | 0.79 | 0.93 | 0.96 | **1.00** | 0.874 | 8 |
| hybrid RRF k=60 | 0.79 | 0.91 | 0.91 | 0.97 | 0.858 | 8 |
| **hybrid k=2 + rerank (shipped)** | **0.87** | **0.97** | **0.99** | **1.00** | **0.921** | 477 |

MRR by question kind:

| system | lexical | paraphrase | section |
|---|---|---|---|
| dense only | 0.762 | **0.740** | 0.972 |
| BM25 only | **0.896** | 0.578 | 0.940 |
| hybrid RRF k=2 | 0.859 | 0.666 | 0.972 |
| hybrid RRF k=60 | 0.812 | 0.616 | 0.986 |
| hybrid k=2 + rerank | **0.906** | **0.790** | **0.986** |

Reranker comparison (same hybrid top-10 candidates, before the heading-path fix):

| reranker | hit@1 | hit@3 | MRR | ms/query |
|---|---|---|---|---|
| ms-marco-MiniLM-L-6-v2 | 0.76 | 0.97 | 0.864 | 257 |
| ms-marco-MiniLM-L-12-v2 | 0.79 | 0.97 | 0.881 | 500 |
| bge-reranker-base | 0.72 | 0.94 | 0.832 | 2194 |

## What the numbers say
- **Dense and BM25 fail on different questions.** Dense misses exact codes (`N17.9`, `Troponin I` not in its
  top 10); BM25 misses paraphrases (`p10`, `p15`, `p16` not in its top 10). Hybrid finds the answer in the top 10
  for **all 68** (dense: 65, BM25: 65), which is what the reranker needs.
- **Hybrid alone is not better at rank 1** (0.79 vs dense 0.81): RRF k=2 lets a strong BM25 1st place push the
  right dense hit down. Fusion widens recall; it doesn't order well. That's the reranker's job.
- **Rerank is the best system on every metric**, and hit@3 = 0.97 matters most because the LLM only sees 3 chunks
  (R4.2). The cost is ~0.5 s per query on CPU.
- **The reranker needs the heading path.** Scoring `section_title + text`, the reranker *lowered* hit@1 (0.81 →
  0.76): the diabetes and hypertension protocols both have a section called "Pharmacological management", and a
  Metformin table under that title lost its disease. Scoring `A. Type 2 Diabetes Mellitus > Pharmacological
  management` + text raised hit@1 to 0.87. The LLM prompt now gets the same path.
- **RRF k=60 is worse than k=2** here (MRR 0.858 vs 0.874; hit@10 0.97 vs 1.00), so D22's default stays.
- **Bigger rerankers didn't pay off**: L-12 is 2x slower for +0.03 hit@1; bge-reranker-base is 8x slower and worse.

## Limits
- 68 hand-written questions; a small corpus (268 chunks, ~50–130 visible per role). Differences of one or two
  questions (0.01–0.03) are noise.
- Only the first relevant chunk counts; questions that need two sections aren't tested.
- The chunk size (256 vs 512 tokens, D17) was not compared: it needs a re-index. Still an open item.
