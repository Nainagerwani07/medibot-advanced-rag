"""Structure-first chunking with Docling's HybridChunker plus the mandatory metadata (R2.2-R2.4).

HybridChunker works in two passes:
1. structure: one chunk per document element (paragraph, list, table), under its heading path;
2. tokens: split chunks over `max_tokens` and merge small neighbours that share headings.
Tokens are counted with the embedding model's own tokenizer, so nothing is truncated at embed time.

Tables (D18) are written as one `column: value` line per row, so an oversized table is split
between rows and every row stays readable on its own.
"""

from dataclasses import dataclass, field
from pathlib import Path

from docling_core.transforms.chunker.doc_chunk import DocChunk
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    BaseTableSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.types.doc import DocItemLabel, DoclingDocument, TableItem

from medibot.rbac import roles_for_collection

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# D17: every text section fits in 256 tokens with its heading prefix (max ~230, Day 3 profile);
# only large tables get split, into row groups that are more precise to retrieve.
MAX_TOKENS = 256


@dataclass
class Chunk:
    text: str  # chunk body, what the LLM reads and we cite
    embed_text: str  # heading path + body, what gets embedded (R2.3)
    metadata: dict = field(default_factory=dict)  # R2.4 schema + headings/pages


class KeyValueRowTableSerializer(BaseTableSerializer):
    """One line per table row: `Drug: Amoxicillin; Route: Oral; Standard Dose: 500 mg TDS`.

    Docling's default (triplets) writes the whole table as a single line, so its line-based
    splitter can only cut mid-cell. Markdown splits on rows but its `|---|` separator costs
    ~140 bge tokens per piece. Key: value rows cost ~44 tokens and name every column (Day 3).
    """

    def serialize(
        self,
        *,
        item: TableItem,
        doc_serializer: BaseDocSerializer,
        doc: DoclingDocument,
        **kwargs,
    ) -> SerializationResult:
        parts = []
        caption = doc_serializer.serialize_captions(item=item, **kwargs).text
        if caption:
            parts.append(caption)
        if item.self_ref not in doc_serializer.get_excluded_refs(**kwargs):
            df = item.export_to_dataframe(doc=doc)
            columns = [str(c).strip() for c in df.columns]
            has_header = not all(c.isdigit() for c in columns)  # unnamed columns come as 0, 1, ...
            for row in df.itertuples(index=False, name=None):
                cells = [(col, str(val).strip()) for col, val in zip(columns, row, strict=True)]
                if has_header:
                    line = "; ".join(f"{col}: {val}" for col, val in cells if val)
                else:
                    line = "; ".join(val for _, val in cells if val)
                if line:
                    parts.append(line)
        return create_ser_result(text="\n".join(parts), span_source=item)

    def get_header_and_body_lines(
        self, *, table_text: str, **kwargs
    ) -> tuple[list[str], list[str]]:
        # No header: every row names its columns. Keep line endings, because the row packer
        # joins lines as-is (the base class strips them and rows would run together).
        return [], [line for line in table_text.splitlines(keepends=True) if line.strip()]


class _KeyValueSerializerProvider(ChunkingSerializerProvider):
    def get_serializer(self, doc: DoclingDocument) -> BaseDocSerializer:
        return ChunkingDocSerializer(doc=doc, table_serializer=KeyValueRowTableSerializer())


class _HeadingAwareChunker(HybridChunker):
    """HybridChunker whose row-by-row table split also leaves room for the heading prefix.

    The library packs table rows up to the full `max_tokens` and ignores the heading path that
    `contextualize()` adds in front, so table chunks came out up to ~15 tokens over the limit.
    `available_length` (limit minus headings) is already computed; we give the table path a
    tokenizer capped at that budget. Covered by tests/test_chunking.py.
    """

    def segment(
        self, doc_chunk: DocChunk, available_length: int, doc_serializer: BaseDocSerializer
    ) -> list[str]:
        if available_length >= self.max_tokens:
            return super().segment(doc_chunk, available_length, doc_serializer)
        budget = HuggingFaceTokenizer(
            tokenizer=self.tokenizer.get_tokenizer(), max_tokens=available_length
        )
        narrowed = self.model_copy(update={"tokenizer": budget})
        return HybridChunker.segment(narrowed, doc_chunk, available_length, doc_serializer)


def build_chunker() -> HybridChunker:
    tokenizer = HuggingFaceTokenizer.from_pretrained(EMBED_MODEL, max_tokens=MAX_TOKENS)
    return _HeadingAwareChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        repeat_table_header=True,  # enables the row-by-row table path; our rows need no header
        serializer_provider=_KeyValueSerializerProvider(),
    )


def chunk_type_for(labels: set[DocItemLabel]) -> str:
    """text / table / heading / code, from the Docling labels of the items in the chunk."""
    if DocItemLabel.TABLE in labels:
        return "table"
    # only a chunk made purely of code blocks is "code"; inline `code` inside a sentence is text
    if labels == {DocItemLabel.CODE}:
        return "code"
    if labels <= {DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE}:
        return "heading"
    return "text"


def chunk_document(doc: DoclingDocument, source: Path, chunker: HybridChunker) -> list[Chunk]:
    """Chunk one parsed document. `source` is the original file: its folder is the collection."""
    collection = source.parent.name
    access_roles = roles_for_collection(collection)
    chunks = []
    for raw in chunker.chunk(doc):
        headings = list(raw.meta.headings or [])
        labels = {item.label for item in raw.meta.doc_items}
        pages = sorted({p.page_no for item in raw.meta.doc_items for p in item.prov})
        chunks.append(
            Chunk(
                text=raw.text,
                embed_text=chunker.contextualize(raw),
                metadata={
                    "source_document": source.name,
                    "collection": collection,
                    "access_roles": access_roles,
                    # nearest heading; the full path is kept in `headings`
                    "section_title": headings[-1] if headings else doc.name,
                    "chunk_type": chunk_type_for(labels),
                    "headings": headings,
                    "page_numbers": pages,
                },
            )
        )
    return chunks
