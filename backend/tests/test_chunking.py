"""Chunking rules from Day 3 (R2.2-R2.4, D17, D18) on small synthetic documents."""

import pytest
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    TableCell,
    TableData,
)

from medibot.ingestion.chunking import MAX_TOKENS, build_chunker, chunk_type_for
from medibot.ingestion.parsing import strip_inline_markdown
from medibot.rbac import roles_for_collection

COLUMNS = ["Drug", "Route", "Standard Dose", "Storage", "Notes"]


def _table_doc(n_rows: int) -> DoclingDocument:
    """A document with a title, one section heading and one wide table under it."""
    doc = DoclingDocument(name="formulary")
    doc.add_title(text="Approved Drug Formulary")
    doc.add_heading(text="1. Antimicrobials", level=2)
    cells = [
        TableCell(
            text=text,
            start_row_offset_idx=r,
            end_row_offset_idx=r + 1,
            start_col_offset_idx=c,
            end_col_offset_idx=c + 1,
            column_header=r == 0,
        )
        for r in range(n_rows + 1)
        for c, text in enumerate(
            COLUMNS
            if r == 0
            else [f"Drug{r}", "Oral/IV", f"{r} mg Q8H", "Room temp", "Check renal function"]
        )
    ]
    doc.add_table(data=TableData(num_rows=n_rows + 1, num_cols=len(COLUMNS), table_cells=cells))
    return doc


@pytest.fixture(scope="module")
def chunker():
    return build_chunker()


def test_large_table_is_split_between_rows_within_limit(chunker):
    raw = list(chunker.chunk(_table_doc(n_rows=40)))
    assert len(raw) > 1, "a 40-row table should not fit in one chunk"

    rows_seen = 0
    for chunk in raw:
        # the limit includes the heading prefix that gets embedded (D17)
        assert chunker.tokenizer.count_tokens(chunker.contextualize(chunk)) <= MAX_TOKENS
        assert chunk.meta.headings == ["Approved Drug Formulary", "1. Antimicrobials"]
        for line in chunk.text.splitlines():
            # every line is one whole row that names all of its columns (D18)
            assert [part.split(":")[0] for part in line.split("; ")] == COLUMNS
            rows_seen += 1
    assert rows_seen == 40, "no row lost or duplicated across pieces"


def test_small_table_stays_one_chunk(chunker):
    raw = list(chunker.chunk(_table_doc(n_rows=3)))
    assert len(raw) == 1
    assert raw[0].text.splitlines()[0].startswith("Drug: Drug1; Route: Oral/IV")


def test_strip_inline_markdown_keeps_fenced_blocks():
    source = "Use **cashless\npre-auth** via `MBP`.\n```\na ──► **b**\n```\n"
    assert (
        strip_inline_markdown(source) == "Use cashless\npre-auth via MBP.\n```\na ──► **b**\n```\n"
    )


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ({DocItemLabel.TABLE, DocItemLabel.TEXT}, "table"),
        ({DocItemLabel.CODE}, "code"),
        ({DocItemLabel.CODE, DocItemLabel.TEXT}, "text"),  # inline code inside a sentence
        ({DocItemLabel.SECTION_HEADER}, "heading"),
        ({DocItemLabel.FOOTNOTE}, "text"),
    ],
)
def test_chunk_type(labels, expected):
    assert chunk_type_for(labels) == expected


def test_access_roles_follow_role_matrix():
    assert roles_for_collection("nursing") == ["admin", "doctor", "nurse"]  # D7
    assert roles_for_collection("billing") == ["admin", "billing_executive"]
    assert len(roles_for_collection("general")) == 5
    with pytest.raises(ValueError, match="unknown collection"):
        roles_for_collection("hr")
