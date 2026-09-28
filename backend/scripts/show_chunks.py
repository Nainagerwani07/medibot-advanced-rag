"""Day 3 check: chunk all 12 documents and inspect the result (R2.2-R2.4).

Usage (from backend/):
    uv run python scripts/show_chunks.py

Prints per-document chunk counts by type, validates every chunk (5 metadata fields present,
embed_text within the token limit), then prints a few hand-picked chunks in full.
Also writes every chunk to data/chunks.jsonl (gitignored), one JSON object per line, for browsing
and for diffing what changes when chunking settings change.
"""

import json
import statistics
from collections import Counter

from explore_docling import DATA_DIR

from medibot.ingestion.chunking import MAX_TOKENS, build_chunker, chunk_document
from medibot.ingestion.parsing import build_converter, load_document

PARSED_DIR = DATA_DIR.parent / "parsed"
EXPORT_PATH = DATA_DIR.parent / "chunks.jsonl"
REQUIRED = ["source_document", "collection", "access_roles", "section_title", "chunk_type"]

# (source_document, substring of the chunk text) for the cases we flagged on Day 2 / Day 3
SAMPLES = [
    ("leave_policy.pdf", "voluntary abandonment"),  # text after a callout box
    ("drug_formulary.pdf", "Ceftriaxone"),  # piece of a split table
    ("treatment_protocols.pdf", "Dengue"),  # ICD-10 line that became a heading
    ("claim_submission_guide.md", "Admission"),  # fenced code block (flow diagram)
    ("claim_submission_guide.md", "empanelled insurer listed in"),  # inline code
    ("treatment_protocols.pdf", "ICD-10: E11"),  # tiny intro-only section
]


def export(chunks, token_counts) -> None:
    with EXPORT_PATH.open("w", encoding="utf-8") as fh:
        for i, (chunk, tokens) in enumerate(zip(chunks, token_counts, strict=True)):
            record = {
                "index": i,
                "tokens": tokens,
                "metadata": chunk.metadata,
                "text": chunk.text,
                "embed_text": chunk.embed_text,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")  # keep ₹, — readable
    print(f"  wrote {len(chunks)} chunks to {EXPORT_PATH}")


def main() -> None:
    chunker = build_chunker()
    tokenizer = chunker.tokenizer
    chunks = []
    converter = build_converter()
    for path in sorted(p for p in DATA_DIR.rglob("*") if p.suffix in {".pdf", ".md"}):
        doc = load_document(path, PARSED_DIR, converter)
        chunks += chunk_document(doc, path, chunker)

    print(f"=== {len(chunks)} chunks, max_tokens={MAX_TOKENS} ===")
    for source in sorted({c.metadata["source_document"] for c in chunks}):
        mine = [c for c in chunks if c.metadata["source_document"] == source]
        types = Counter(c.metadata["chunk_type"] for c in mine)
        coll = mine[0].metadata["collection"]
        print(f"  {source:<28} {coll:<10} {len(mine):>3} chunks  {dict(types)}")

    print("\n=== Validation ===")
    token_counts = [tokenizer.count_tokens(c.embed_text) for c in chunks]
    missing = [c for c in chunks if any(c.metadata.get(k) in (None, "", []) for k in REQUIRED)]
    over = [n for n in token_counts if n > MAX_TOKENS]
    print(f"  chunk types overall: {dict(Counter(c.metadata['chunk_type'] for c in chunks))}")
    median = int(statistics.median(token_counts))
    print(
        f"  embed_text tokens: min={min(token_counts)} median={median}"
        f" max={max(token_counts)}  over limit: {len(over)}"
    )
    print(f"  chunks missing a required field: {len(missing)}")
    export(chunks, token_counts)
    roles = {c.metadata["collection"]: c.metadata["access_roles"] for c in chunks}
    for collection, allowed in sorted(roles.items()):
        print(f"  access_roles[{collection}] = {allowed}")

    for source, needle in SAMPLES:
        match = next(
            (c for c in chunks if c.metadata["source_document"] == source and needle in c.text),
            None,
        )
        print(f"\n--- sample: {source} / {needle!r} ---")
        if match is None:
            print("  (no chunk found)")
            continue
        meta = {k: v for k, v in match.metadata.items() if k != "access_roles"}
        print(f"  metadata: {meta}")
        print(f"  tokens: {tokenizer.count_tokens(match.embed_text)}")
        print("  embed_text:")
        print("    " + match.embed_text[:700].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
