"""Day 2 exploration: parse one document with Docling and show its structure (R2.1).

Usage (from backend/):
    uv run python scripts/explore_docling.py [path/to/file] [--markdown]

Prints the DoclingDocument element tree (label, heading level, page), every table as a
DataFrame, and optionally the Markdown export. Not part of the app; ingestion comes on Day 4.
"""

import sys
import time
from pathlib import Path

from docling_core.types.doc import ContentLayer, SectionHeaderItem, TableItem

from medibot.ingestion.parsing import build_converter

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "mediassist_data"
DEFAULT_FILE = DATA_DIR / "general" / "leave_policy.pdf"


def print_tree(doc) -> None:
    print(f"\n=== Element tree: {doc.name} ===")
    print(f"{'layer':<9} {'page':>4}  {'label':<15} text")
    # BODY is the real content; FURNITURE is page headers/footers Docling set aside.
    layers = {ContentLayer.BODY, ContentLayer.FURNITURE}
    for item, depth in doc.iterate_items(included_content_layers=layers):
        page = item.prov[0].page_no if getattr(item, "prov", None) else "-"
        label = str(item.label.value)
        if isinstance(item, SectionHeaderItem):
            label += f"(L{item.level})"
        text = getattr(item, "text", "") or ("<table>" if isinstance(item, TableItem) else "")
        text = text.replace("\n", " ")
        indent = "  " * max(depth - 1, 0)
        print(f"{item.content_layer.value:<9} {page:>4}  {label:<15} {indent}{text[:80]}")


def print_tables(doc) -> None:
    tables = list(doc.tables)
    print(f"\n=== Tables: {len(tables)} ===")
    for i, table in enumerate(tables, 1):
        df = table.export_to_dataframe(doc=doc)
        page = table.prov[0].page_no if table.prov else "-"
        print(f"\n--- Table {i} (page {page}, {df.shape[0]} rows x {df.shape[1]} cols) ---")
        print(df.to_string(max_colwidth=40))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else DEFAULT_FILE

    converter = build_converter()
    start = time.perf_counter()
    result = converter.convert(path)
    elapsed = time.perf_counter() - start
    doc = result.document
    print(f"Parsed {path.name}: {doc.num_pages()} pages in {elapsed:.1f}s, status={result.status}")

    print_tree(doc)
    print_tables(doc)
    if "--markdown" in sys.argv:
        print("\n=== Markdown export ===")
        print(doc.export_to_markdown())


if __name__ == "__main__":
    main()
