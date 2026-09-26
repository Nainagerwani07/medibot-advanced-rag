"""Day 2 exploration: parse all 12 documents and summarise their structure (R2.1).

Usage (from backend/):
    uv run python scripts/inspect_all.py

For each file prints: pages, parse time, element counts per label, heading levels,
numbered vs unnumbered headings (callout suspects), tables and code blocks.
Full element trees and DoclingDocument JSON go to data/parsed/ (gitignored) for Day 3.
"""

import re
import time
from collections import Counter
from contextlib import redirect_stdout

from docling_core.types.doc import ContentLayer, SectionHeaderItem, TitleItem
from explore_docling import DATA_DIR, build_converter, print_tree

OUT_DIR = DATA_DIR.parent / "parsed"
NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s")  # "1. Scope", "2.1 Dosing", "3 Triage"


def summarise(doc, seconds: float) -> dict:
    body, furniture = Counter(), Counter()
    headings = []
    layers = {ContentLayer.BODY, ContentLayer.FURNITURE}
    for item, _ in doc.iterate_items(included_content_layers=layers):
        target = furniture if item.content_layer == ContentLayer.FURNITURE else body
        target[item.label.value] += 1
        if isinstance(item, SectionHeaderItem | TitleItem):
            level = getattr(item, "level", 0)
            headings.append((level, item.text))
    return {
        "pages": doc.num_pages(),
        "seconds": seconds,
        "body": body,
        "furniture": furniture,
        "headings": headings,
        "tables": [
            (t.prov[0].page_no if t.prov else "-", t.data.num_rows, t.data.num_cols)
            for t in doc.tables
        ],
    }


def print_summary(name: str, s: dict) -> None:
    levels = Counter(level for level, _ in s["headings"])
    unnumbered = [text for _, text in s["headings"] if not NUMBERED.match(text)]
    print(f"\n### {name}  ({s['pages']} pages, {s['seconds']:.1f}s)")
    print(f"  body:      {dict(s['body'].most_common())}")
    print(f"  furniture: {dict(s['furniture'].most_common())}")
    print(f"  heading levels: {dict(sorted(levels.items()))}")
    print(f"  tables (page, rows, cols): {s['tables']}")
    print(f"  unnumbered headings ({len(unnumbered)}): {unnumbered}")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    files = sorted(p for p in DATA_DIR.rglob("*") if p.suffix in {".pdf", ".md"})
    converter = build_converter()
    total = 0.0
    for path in files:
        start = time.perf_counter()
        doc = converter.convert(path).document
        seconds = time.perf_counter() - start
        total += seconds

        name = f"{path.parent.name}/{path.name}"
        print_summary(name, summarise(doc, seconds))

        doc.save_as_json(OUT_DIR / f"{path.stem}.json")
        with open(OUT_DIR / f"{path.stem}.tree.txt", "w") as fh, redirect_stdout(fh):
            print_tree(doc)
    print(f"\nParsed {len(files)} files in {total:.1f}s. Trees + JSON in {OUT_DIR}")


if __name__ == "__main__":
    main()
