# Ingestion pipeline: diagrams

Built on Day 2 (parsing) and Day 3 (chunking + metadata). Code: `backend/src/medibot/ingestion/`,
`backend/src/medibot/rbac.py`. Decisions: D4, D16, D17, D18 in [DECISIONS.md](../DECISIONS.md).

## 1. From source file to chunk

```mermaid
flowchart TD
    SRC["Source file<br/>data/mediassist_data/&lt;collection&gt;/…"]
    SRC -->|.pdf| PDF["Docling convert<br/>OCR off (D4), TableFormer on"]
    SRC -->|.md| MDC["strip_inline_markdown()<br/>drop **bold** / `code`, keep fenced blocks (D18)"]
    PDF --> CACHE[("data/parsed/*.json<br/>cache, ~200 s to rebuild")]
    CACHE --> FIX["fix_heading_levels() (D16)<br/>font size in heading bbox → level<br/>26pt L1 · 16pt L2 · 12.5/10.8pt L3 · 9.3pt L4"]
    MDC --> MDP["Docling Markdown backend<br/># levels already correct"]
    FIX --> DOC["DoclingDocument<br/>typed tree, BODY layer only"]
    MDP --> DOC

    subgraph CHUNK["HybridChunker (chunking.py)"]
        P1["Pass 1: structure<br/>one chunk per paragraph / list / table<br/>under its heading path"]
        SER["Tables: KeyValueRowTableSerializer<br/>one 'column: value' line per row (D18)"]
        P2["Pass 2: tokens, bge-small tokenizer<br/>max 256 incl. headings (D17)"]
        SPLIT["too big: table → split between rows<br/>(_HeadingAwareChunker budget)<br/>text → semantic split (never needed)"]
        MERGE["too small: merge_peers<br/>(only if same headings)"]
        CTX["contextualize()<br/>heading path + body"]
        P1 --> SER --> P2
        P2 --> SPLIT --> CTX
        P2 --> MERGE --> CTX
    end
    DOC --> P1

    RBAC["rbac.py<br/>role → collections"] -->|access_roles| OUT
    CTX --> OUT["Chunk<br/>text · embed_text · metadata<br/>source_document, collection, access_roles,<br/>section_title, chunk_type (+ headings, pages)"]
    OUT --> NEXT["Day 4: dense + BM25 embed → Qdrant"]
```

Result on the dataset: 268 chunks (194 text, 73 table, 1 code), all ≤ 256 tokens, 0 missing metadata.

## 2. Content layers: why headers and footers never reach a chunk (Day 2)

```mermaid
flowchart LR
    PAGE["PDF page"] --> LAYOUT["Docling layout model<br/>labels every region"]
    LAYOUT --> BODY["BODY<br/>title, section_header, text,<br/>list_item, table, code, footnote"]
    LAYOUT --> FURN["FURNITURE<br/>page_header, page_footer<br/>'Page 3 of 4', 'CONFIDENTIAL…'"]
    BODY --> CH["chunker reads this"]
    FURN --> SKIP["ignored: no regex cleanup needed"]
```

## 3. The heading stack: why heading levels matter (Day 3)

The chunker keeps one heading per level. A heading at level L removes every entry at level ≥ L,
then takes its place. Each chunk gets the headings on the stack when it's emitted.

```
leave_policy.pdf, walking the document top to bottom:

                               BEFORE fix (all L1)          AFTER fix (font size)
  "Leave & Attendance Policy"  [Leave…]                     L1 [Leave…]
  "10. Abandonment of Service" [10. Abandonment…]           L2 [Leave…, 10. Abandonment…]
  "Important" (callout, 9.3pt) [Important]  ← replaced it!  L4 [Leave…, 10. Abandonment…, Important]
  "Absence from duty…" (text)  chunk headings: Important    chunk headings: Leave… > 10. Abandonment… > Important
```

With flat levels the paragraph was embedded under "Important" only; now it carries its real section.

## 4. Splitting a big table: three formats measured (Day 3, D18)

```
drug_formulary "1. Antimicrobials" (16 rows × 7 cols), bge-small tokens

A. Triplets (Docling default)  whole table on ONE line → can only be cut mid-line
   …Piperacillin-Tazobactam, Storage =  ║  Refrigerate post-recon.. Piperacillin-Tazobactam, Notes = …
                               chunk 1 ends here ║ chunk 2 starts here   ✗ fact split in two

B. Markdown + repeat header    splits between rows ✓, but every piece repeats
   | Drug | Class | … |
   |------|-------|---| ← 142 tokens of dashes per piece, only 1–2 rows fit   ✗

C. key: value rows (chosen)    one row per line, ~44 tokens, split between rows ✓
   Approved Drug Formulary
   1. Antimicrobials
   Drug: Amoxicillin; Class: Penicillin; Route: Oral; Standard Dose: 500 mg TDS; …
   Drug: Piperacillin-Tazobactam; …; Storage: Refrigerate post-recon.; …      ✓ every row stands alone
```
