"""Rebuild PDF heading levels from font size (D16, serves R2.3).

Docling's PDF layout model finds headings but gives every one level 1. HybridChunker keeps a
heading stack keyed by level (a level-L heading drops every entry at level >= L), so with all
headings at level 1 each heading replaces the last and chunks get the wrong parent section.

Every MediAssist PDF uses the same template, so a heading's font size tells its depth:
26 pt title, 16 pt section, 12.5/10.8 pt subsection, 9.3 pt callout-box label.
Markdown input already has correct levels and is left alone.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from docling_core.types.doc import CoordOrigin, DoclingDocument, SectionHeaderItem

# (minimum font size in pt, heading level). Levels only need the right order: the chunker
# compares them. Level 1 is the minimum Docling allows for a SectionHeaderItem.
LEVEL_BY_FONT_SIZE = [
    (20.0, 1),  # document title (26 pt)
    (14.0, 2),  # section: "1. Scope", "SOP 2 - ...", "B. Hypertension" (16 pt)
    (10.0, 3),  # subsection: "Monitoring", "Q7. ..." (12.5 / 10.8 pt)
    (0.0, 4),  # callout-box label: "Important", "Red flags" (9.3 pt)
]


@dataclass
class HeadingFix:
    text: str
    page: int
    font_size: float | None  # None when no characters were found inside the heading's box
    level: int


def level_for_size(size: float) -> int:
    return next(level for min_size, level in LEVEL_BY_FONT_SIZE if size >= min_size)


def _page_chars(page: pdfium.PdfPage) -> list[tuple[float, float, float]]:
    """(x centre, y centre, font size) per visible char, PDF coords (bottom-left origin)."""
    textpage = page.get_textpage()
    chars = []
    for i in range(textpage.count_chars()):
        if not chr(pdfium_raw.FPDFText_GetUnicode(textpage, i)).strip():
            continue
        left, bottom, right, top = textpage.get_charbox(i)
        size = pdfium_raw.FPDFText_GetFontSize(textpage, i)
        chars.append(((left + right) / 2, (bottom + top) / 2, size))
    return chars


def fix_heading_levels(doc: DoclingDocument, pdf_path: Path) -> list[HeadingFix]:
    """Set each section header's level from the font size of the text inside its bounding box.

    Matches by position, not text, so headings whose text Docling normalised (e.g. "—" to "-")
    still match. Returns what was changed so callers can print and check it.
    """
    pdf = pdfium.PdfDocument(pdf_path)
    chars_by_page: dict[int, list[tuple[float, float, float]]] = {}
    fixes = []

    for item, _ in doc.iterate_items():
        if not isinstance(item, SectionHeaderItem) or not item.prov:
            continue
        prov = item.prov[0]
        if prov.page_no not in chars_by_page:
            # Docling pages are 1-based, pypdfium2 pages 0-based
            chars_by_page[prov.page_no] = _page_chars(pdf[prov.page_no - 1])

        box = prov.bbox
        if box.coord_origin != CoordOrigin.BOTTOMLEFT:
            box = box.to_bottom_left_origin(doc.pages[prov.page_no].size.height)
        sizes = Counter(
            round(size, 1)
            for x, y, size in chars_by_page[prov.page_no]
            if box.l <= x <= box.r and box.b <= y <= box.t
        )

        font_size = sizes.most_common(1)[0][0] if sizes else None
        if font_size is not None:
            item.level = level_for_size(font_size)
        fixes.append(HeadingFix(item.text, prov.page_no, font_size, item.level))

    pdf.close()
    return fixes
