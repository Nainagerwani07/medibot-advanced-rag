"""Day 6 retrieval eval (R3.5, R4, NF5): dense-only vs BM25-only vs hybrid vs hybrid+rerank.

Each question in `eval/questions.jsonl` names the chunk that answers it: `source` + `section`, and
optionally `contains` (a word that picks the right row group of a split table). Each question runs
under its own role, so the numbers are measured with the RBAC filter on, as in production.

Metrics, over the first relevant chunk's rank r (1-based) in each result list:
    hit@k = share of questions with r <= k      (hit@3 = "is the answer in what the LLM sees")
    MRR   = mean of 1/r (0 if not found in top 10)

Run from backend/ (Qdrant up):  uv run python scripts/eval_retrieval.py [--show-rerank]
"""

import argparse
import json
import logging
import time
from pathlib import Path

from medibot.retrieval.hybrid import HybridRetriever, RetrievedChunk
from medibot.retrieval.rerank import Reranker

EVAL_FILE = Path(__file__).resolve().parents[1] / "eval" / "questions.jsonl"
KS = (1, 3, 5, 10)


def is_relevant(chunk: RetrievedChunk, q: dict) -> bool:
    m = chunk.metadata
    return (
        m["source_document"] == q["source"]
        and m["section_title"] == q["section"]
        and q.get("contains", "").lower() in chunk.text.lower()
    )


def first_rank(chunks: list[RetrievedChunk], q: dict) -> int | None:
    return next((i + 1 for i, c in enumerate(chunks) if is_relevant(c, q)), None)


def summarise(ranks: list[int | None]) -> dict:
    n = len(ranks)
    out = {f"hit@{k}": sum(r is not None and r <= k for r in ranks) / n for k in KS}
    out["MRR"] = sum(1 / r for r in ranks if r) / n
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-rerank", action="store_true", help="log reranker scores (R4.4)")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.show_rerank else logging.WARNING, format="%(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    questions = [json.loads(line) for line in EVAL_FILE.read_text().splitlines() if line.strip()]
    retriever, reranker = HybridRetriever(), Reranker()

    systems = {
        "dense only": lambda q: retriever.search(q["question"], q["role"], mode="dense"),
        "BM25 only": lambda q: retriever.search(q["question"], q["role"], mode="sparse"),
        "hybrid RRF k=2": lambda q: retriever.search(q["question"], q["role"]),
        "hybrid RRF k=60": lambda q: retriever.search(q["question"], q["role"], rrf_k=60),
        "hybrid k=2 + rerank": lambda q: reranker.rerank(
            q["question"], retriever.search(q["question"], q["role"]), top_n=10
        ),
    }
    ranks: dict[str, list[int | None]] = {name: [] for name in systems}
    latency: dict[str, float] = {}
    for name, run in systems.items():
        t0 = time.perf_counter()
        for q in questions:
            if args.show_rerank and "rerank" in name:
                print(f"\n{q['id']} [{q['role']}] {q['question']}")
            ranks[name].append(first_rank(run(q), q))
        latency[name] = (time.perf_counter() - t0) / len(questions) * 1000

    print(f"\n{len(questions)} questions, each under its own role\n")
    print("| system | hit@1 | hit@3 | hit@5 | hit@10 | MRR | ms/query |")
    print("|---|---|---|---|---|---|---|")
    for name in systems:
        s = summarise(ranks[name])
        cells = " | ".join(f"{s[f'hit@{k}']:.2f}" for k in KS)
        print(f"| {name} | {cells} | {s['MRR']:.3f} | {latency[name]:.0f} |")

    kinds = sorted({q.get("kind", "section") for q in questions})
    print("\nMRR by question kind (section = wording close to the heading, lexical = exact code or")
    print("drug name inside a table, paraphrase = none of the heading's words):\n")
    counts = {k: sum(q.get("kind", "section") == k for q in questions) for k in kinds}
    print("| system | " + " | ".join(f"{k} (n={counts[k]})" for k in kinds) + " |")
    print("|---|" + "---|" * len(kinds))
    for name in systems:
        cells = []
        for k in kinds:
            sub = [r for r, q in zip(ranks[name], questions, strict=True) if q.get("kind") == k]
            cells.append(f"{summarise(sub)['MRR']:.3f}")
        print(f"| {name} | " + " | ".join(cells) + " |")

    print("\nPer question rank of the answer chunk (- = not in top 10):")
    names = list(systems)
    print("id   " + "  ".join(f"{n[:12]:>12}" for n in names))
    for i, q in enumerate(questions):
        cells = "  ".join(f"{ranks[n][i] or '-':>12}" for n in names)
        print(f"{q['id']}  {cells}")


if __name__ == "__main__":
    main()
