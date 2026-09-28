"""Turn a source file into a DoclingDocument ready for chunking (R2.1).

- PDF: Docling with OCR off (D4), then heading levels rebuilt from font size (D16).
  Parsing costs ~5-36 s per PDF on CPU, so results are cached as JSON.
- Markdown: inline `**bold**` and `code` are removed first (D18). Docling turns such a paragraph
  into an inline group of separate items, and the chunker then puts each piece on its own line
  and fences the inline code as if it were a code block. Fenced code blocks are left untouched.
"""

import re
from io import BytesIO
from pathlib import Path

from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DoclingDocument

from medibot.ingestion.headings import fix_heading_levels

_FENCE = re.compile(r"(^```.*?^```[^\n]*$)", re.MULTILINE | re.DOTALL)
_BOLD = re.compile(r"\*\*([^*]+?)\*\*")  # [^*] so a phrase may span a line break
_INLINE_CODE = re.compile(r"`([^`\n]+)`")


def build_converter() -> DocumentConverter:
    pdf_options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
    )


def strip_inline_markdown(text: str) -> str:
    """Remove bold and inline-code markers outside fenced code blocks."""
    parts = _FENCE.split(text)  # odd indexes are fenced blocks, kept as they are
    for i in range(0, len(parts), 2):
        parts[i] = _INLINE_CODE.sub(r"\1", _BOLD.sub(r"\1", parts[i]))
    return "".join(parts)


def load_document(
    path: Path, cache_dir: Path, converter: DocumentConverter | None = None
) -> DoclingDocument:
    """Parse `path` (or load its cached parse) and apply the format-specific fixes."""
    converter = converter or build_converter()
    if path.suffix == ".md":
        cleaned = strip_inline_markdown(path.read_text(encoding="utf-8"))
        stream = DocumentStream(name=path.name, stream=BytesIO(cleaned.encode("utf-8")))
        return converter.convert(stream).document

    cached = cache_dir / f"{path.stem}.json"
    if cached.exists():
        doc = DoclingDocument.load_from_json(cached)
    else:
        doc = converter.convert(path).document
        cache_dir.mkdir(parents=True, exist_ok=True)
        doc.save_as_json(cached)
    fix_heading_levels(doc, path)
    return doc
