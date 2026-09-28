"""Day 4 exploration: what dense and sparse (BM25) vectors look like for our chunks (R3.1).

Usage (from backend/):
    uv run python scripts/show_chunks.py        # once, writes data/chunks.jsonl
    uv run python scripts/explore_embeddings.py

1. Tokenizer check: FastEmbed's ONNX bge-small tokenizer vs the HF tokenizer used on Day 3.
2. Dense: shape and values of a bge-small vector; cosine similarity of queries vs sample chunks.
3. Sparse: BM25 (token_id, weight) pairs traced back to the stemmed words, document vs query side.
"""

import json
from collections import Counter

import numpy as np
from explore_docling import DATA_DIR
from fastembed import SparseTextEmbedding, TextEmbedding
from transformers import AutoTokenizer

from medibot.ingestion.chunking import EMBED_MODEL, MAX_TOKENS

CHUNKS_PATH = DATA_DIR.parent / "chunks.jsonl"
SPARSE_MODEL = "Qdrant/bm25"

# (source_document, substring) of chunks to embed, same style as show_chunks.py
SAMPLES = [
    ("drug_formulary.pdf", "Ceftriaxone"),  # table row(s)
    ("leave_policy.pdf", "voluntary abandonment"),  # policy text
    ("claim_submission_guide.md", "Admission"),  # code block
]
QUERIES = [
    "What is the dose of ceftriaxone?",
    "Can a nurse leave the ward in the middle of a shift?",
    "steps to submit an insurance claim after the patient is admitted",
]


def load_chunks() -> list[dict]:
    with CHUNKS_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def pick(chunks: list[dict], source: str, needle: str) -> dict:
    return next(
        c for c in chunks if c["metadata"]["source_document"] == source and needle in c["text"]
    )


def check_tokenizers(chunks: list[dict], dense: TextEmbedding) -> None:
    print("=== 1. Tokenizer check: FastEmbed (ONNX) vs Hugging Face ===")
    hf = AutoTokenizer.from_pretrained(EMBED_MODEL)
    fe = dense.model.tokenizer  # tokenizers.Tokenizer used right before the ONNX model
    print(f"  FastEmbed truncation: {fe.truncation}")
    mismatches, longest = 0, 0
    for c in chunks:
        hf_ids = hf(c["embed_text"])["input_ids"]  # includes [CLS] ... [SEP]
        fe_ids = fe.encode(c["embed_text"]).ids
        longest = max(longest, len(fe_ids))
        mismatches += hf_ids != fe_ids
    print(f"  {len(chunks)} chunks, token-id mismatches: {mismatches}")
    print(
        f"  longest chunk incl. [CLS]/[SEP]: {longest} tokens (budget {MAX_TOKENS}, model max 512)"
    )


def show_dense(samples: list[dict], dense: TextEmbedding) -> None:
    print("\n=== 2. Dense vectors (bge-small-en-v1.5) ===")
    doc_vecs = np.array(list(dense.passage_embed([s["embed_text"] for s in samples])))
    v = doc_vecs[0]
    print(f"  shape {v.shape}, dtype {v.dtype}, L2 norm {np.linalg.norm(v):.3f}")
    print(f"  first 8 values: {np.round(v[:8], 4)}")
    print(f"  non-zero values: {np.count_nonzero(v)} of {v.size}")

    # bge uses an instruction prefix for queries; query_embed adds it for us
    query_vecs = np.array(list(dense.query_embed(QUERIES)))
    sims = query_vecs @ doc_vecs.T  # vectors are normalised, so dot product == cosine
    print("\n  cosine similarity (rows: queries, columns: sample chunks)")
    print("  " + " " * 58 + "  ".join(f"chunk{i}" for i in range(len(samples))))
    for q, row in zip(QUERIES, sims, strict=True):
        print(f"  {q[:56]:<58}" + "  ".join(f"{s:6.3f}" for s in row))
    for i, s in enumerate(samples):
        print(f"  chunk{i} = {s['metadata']['source_document']} / {s['metadata']['section_title']}")


def show_sparse(samples: list[dict], chunks: list[dict], sparse: SparseTextEmbedding) -> None:
    print("\n=== 3. Sparse vectors (Qdrant/bm25) ===")
    bm25 = sparse.model
    print(f"  params: k={bm25.k}, b={bm25.b}, avg_len={bm25.avg_len}, stemmer={bm25.language}")
    lengths = [len(bm25._stem(bm25.tokenizer.tokenize(c["embed_text"]))) for c in chunks]
    print(
        f"  our corpus: avg {np.mean(lengths):.0f} stemmed words per chunk (FastEmbed assumes 256)"
    )

    sample = samples[0]
    words = bm25._stem(bm25.tokenizer.tokenize(sample["embed_text"]))
    id_to_word = {bm25.compute_token_id(w): w for w in words}
    counts = Counter(words)
    emb = next(iter(sparse.passage_embed([sample["embed_text"]])))
    print(
        f"\n  document: {sample['metadata']['source_document']}"
        f" / {sample['metadata']['section_title']}"
    )
    print(f"  {len(words)} stemmed words -> {len(emb.indices)} non-zero entries")
    print(f"  {'stem':<16}{'count':>6}{'token_id':>13}{'tf weight':>11}")
    top = sorted(zip(emb.indices, emb.values, strict=True), key=lambda p: -p[1])[:10]
    for idx, val in top:
        word = id_to_word[idx]
        print(f"  {word:<16}{counts[word]:>6}{idx:>13}{val:>11.3f}")

    q = QUERIES[0]
    q_emb = next(iter(sparse.query_embed(q)))
    q_words = bm25._stem(bm25.tokenizer.tokenize(q))
    print(f"\n  query: {q!r}")
    print(f"  stems after stopword removal: {q_words}")
    print(f"  indices {q_emb.indices.tolist()}  values {q_emb.values.tolist()}")
    shared = set(q_emb.indices) & set(emb.indices)
    print(f"  terms shared with the document: {[id_to_word[i] for i in shared]}")
    df = sum(
        any(w == "ceftriaxon" for w in bm25._stem(bm25.tokenizer.tokenize(c["embed_text"])))
        for c in chunks
    )
    print(f"  'ceftriaxon' appears in {df} of {len(chunks)} chunks -> rare -> high IDF")


def main() -> None:
    chunks = load_chunks()
    samples = [pick(chunks, src, needle) for src, needle in SAMPLES]
    dense = TextEmbedding(EMBED_MODEL)
    sparse = SparseTextEmbedding(SPARSE_MODEL)
    check_tokenizers(chunks, dense)
    show_dense(samples, dense)
    show_sparse(samples, chunks, sparse)


if __name__ == "__main__":
    main()
