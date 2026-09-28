"""Day 3 evidence for choosing max_tokens: token size of every section and table (R2.2).

Usage (from backend/):
    uv run python scripts/section_profile.py

Runs Docling's HierarchicalChunker (structure only, no token limit) on the cached parses with
the font-size heading fix applied, groups its output into leaf sections (same heading path)
and tables, and counts tokens with the embedding model's own tokenizer (bge-small, 512 max).
"""

import statistics
from collections import defaultdict

from docling_core.transforms.chunker import HierarchicalChunker
from docling_core.types.doc import DocItemLabel, DoclingDocument
from explore_docling import DATA_DIR
from transformers import AutoTokenizer

from medibot.ingestion.headings import fix_heading_levels

PARSED_DIR = DATA_DIR.parent / "parsed"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
THRESHOLDS = [128, 256, 384, 512]


def profile_doc(doc: DoclingDocument, tokenizer) -> tuple[list[dict], list[dict]]:
    sections: dict[tuple, dict] = defaultdict(lambda: {"tokens": 0, "items": 0})
    tables = []
    for chunk in HierarchicalChunker().chunk(doc):
        headings = tuple(chunk.meta.headings or ())
        n = len(tokenizer.tokenize(chunk.text))
        if any(item.label == DocItemLabel.TABLE for item in chunk.meta.doc_items):
            tables.append({"doc": doc.name, "path": headings, "tokens": n})
        else:
            sections[headings]["tokens"] += n
            sections[headings]["items"] += 1
    heading_tokens = {path: len(tokenizer.tokenize("\n".join(path))) for path in sections}
    return (
        [
            {"doc": doc.name, "path": p, **v, "heading_tokens": heading_tokens[p]}
            for p, v in sections.items()
        ],
        tables,
    )


def describe(name: str, rows: list[dict]) -> None:
    sizes = sorted(r["tokens"] for r in rows)
    over = "  ".join(f">{t}: {sum(s > t for s in sizes)}" for t in THRESHOLDS)
    q = statistics.quantiles(sizes, n=10)
    print(
        f"{name:<9} n={len(sizes):<4} min={sizes[0]:<4} median={int(statistics.median(sizes)):<4}"
        f" p90={int(q[8]):<4} max={sizes[-1]:<5} | {over}"
    )


def main() -> None:
    tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
    all_sections, all_tables = [], []
    for path in sorted(p for p in DATA_DIR.rglob("*") if p.suffix in {".pdf", ".md"}):
        doc = DoclingDocument.load_from_json(PARSED_DIR / f"{path.stem}.json")
        if path.suffix == ".pdf":
            fix_heading_levels(doc, path)
        sections, tables = profile_doc(doc, tokenizer)
        all_sections += sections
        all_tables += tables

    print("=== Token sizes (bge-small tokenizer), no token limit applied ===")
    describe("sections", all_sections)
    describe("tables", all_tables)
    heading_sizes = [s["heading_tokens"] for s in all_sections]
    print(
        f"heading-path prefix added by contextualize(): median="
        f"{int(statistics.median(heading_sizes))} max={max(heading_sizes)} tokens"
    )

    print("\n=== Per document: sections / tables, largest of each ===")
    for doc_name in sorted({r["doc"] for r in all_sections}):
        secs = [r["tokens"] for r in all_sections if r["doc"] == doc_name]
        tabs = [r["tokens"] for r in all_tables if r["doc"] == doc_name]
        print(
            f"  {doc_name:<24} sections={len(secs):<3} median={int(statistics.median(secs)):<4}"
            f" max={max(secs):<4} | tables={len(tabs):<3} max={max(tabs, default=0)}"
        )

    print("\n=== 8 largest units (these are the ones a token limit would split) ===")
    largest = sorted(all_sections + all_tables, key=lambda r: -r["tokens"])[:8]
    for r in largest:
        kind = "table" if "items" not in r else f"section, {r['items']} items"
        print(f"  {r['tokens']:>5} tok  {r['doc']:<24} ({kind})  {' > '.join(r['path'][-2:])}")

    print("\n=== 8 smallest sections (candidates for merging with neighbours) ===")
    for r in sorted(all_sections, key=lambda r: r["tokens"])[:8]:
        print(f"  {r['tokens']:>5} tok  {r['doc']:<24} {' > '.join(r['path'][-2:])}")


if __name__ == "__main__":
    main()
