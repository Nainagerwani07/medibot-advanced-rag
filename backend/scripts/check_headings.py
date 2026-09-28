"""Day 3 check: apply the font-size heading fix (D16) to the cached parses and show the result.

Usage (from backend/):
    uv run python scripts/check_headings.py [stem ...]

Prints the heading tree after the fix for the given files (default: three with deep
hierarchies), then font-size counts across all PDFs and any heading that had no match.
"""

import sys
from collections import Counter

from docling_core.types.doc import DoclingDocument
from explore_docling import DATA_DIR

from medibot.ingestion.headings import fix_heading_levels

PARSED_DIR = DATA_DIR.parent / "parsed"
DEFAULT_STEMS = ["leave_policy", "treatment_protocols", "icu_nursing_procedures"]


def main() -> None:
    show = sys.argv[1:] or DEFAULT_STEMS
    size_counts: Counter = Counter()
    unmatched = []

    for pdf_path in sorted(DATA_DIR.rglob("*.pdf")):
        doc = DoclingDocument.load_from_json(PARSED_DIR / f"{pdf_path.stem}.json")
        fixes = fix_heading_levels(doc, pdf_path)
        for fix in fixes:
            size_counts[(fix.font_size, fix.level)] += 1
            if fix.font_size is None:
                unmatched.append((pdf_path.name, fix.text))

        if pdf_path.stem in show:
            print(f"\n=== {pdf_path.name}: heading tree after fix ===")
            for fix in fixes:
                indent = "    " * (fix.level - 1)
                print(f"  p{fix.page} {fix.font_size!s:>5}pt L{fix.level} {indent}{fix.text}")

    print("\n=== (font size, level) across all 11 PDFs ===")
    for (size, level), n in sorted(size_counts.items(), key=lambda kv: -(kv[0][0] or 0)):
        print(f"  {size!s:>5} pt -> L{level}: {n}")
    print(f"\nUnmatched headings (kept Docling's level): {unmatched or 'none'}")


if __name__ == "__main__":
    main()
