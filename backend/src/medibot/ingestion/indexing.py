"""Embed chunks and store them in Qdrant (R2.5, R3.1).

One collection (D5) with two named vectors per point:
- `dense`:  bge-small-en-v1.5, 384-dim, cosine (meaning)
- `sparse`: BM25 term-frequency weights; Qdrant adds IDF itself (`Modifier.IDF`), so rare terms
            such as drug names outweigh words every table row repeats ("dose", "route")
Payload indexes on `access_roles` and `collection` let the RBAC filter run inside the search (R1.1).
"""

import os
import uuid
from collections.abc import Iterable

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

from medibot.ingestion.chunking import EMBED_MODEL, Chunk

COLLECTION_NAME = "medibot_docs"
DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"
DENSE_DIM = 384
SPARSE_MODEL = "Qdrant/bm25"
KEYWORD_INDEXES = ["access_roles", "collection", "source_document", "chunk_type"]

# fixed namespace: the same chunk always gets the same point id, so re-runs overwrite
_POINT_NAMESPACE = uuid.UUID("6f1c2a0e-5d8b-4c7e-9a3f-2b6d8e4f1a90")


def qdrant_client() -> QdrantClient:
    return QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))


def bm25_avg_len(embed_texts: list[str]) -> float:
    """Average stemmed-word length of our chunks; FastEmbed's default (256) is ~5x too long."""
    bm25 = SparseTextEmbedding(SPARSE_MODEL).model
    lengths = [len(bm25._stem(bm25.tokenizer.tokenize(t))) for t in embed_texts]
    return sum(lengths) / len(lengths)


def create_collection(client: QdrantClient, recreate: bool = True) -> None:
    """Full rebuild by default: chunking changes would otherwise leave stale points behind."""
    if recreate and client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR: models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            SPARSE_VECTOR: models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )
    for field in KEYWORD_INDEXES:
        client.create_payload_index(
            COLLECTION_NAME, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
        )


def point_id(chunk: Chunk, index_in_doc: int) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{chunk.metadata['source_document']}#{index_in_doc}"))


def build_points(
    chunks: list[Chunk], ids: list[str], dense: TextEmbedding, sparse: SparseTextEmbedding
) -> Iterable[models.PointStruct]:
    texts = [
        c.embed_text for c in chunks
    ]  # heading-contextualised text is what gets embedded (R2.3)
    dense_vecs = dense.passage_embed(texts)
    sparse_vecs = sparse.passage_embed(texts)
    for chunk, pid, d, s in zip(chunks, ids, dense_vecs, sparse_vecs, strict=True):
        yield models.PointStruct(
            id=pid,
            vector={
                DENSE_VECTOR: d.tolist(),
                SPARSE_VECTOR: models.SparseVector(
                    indices=s.indices.tolist(), values=s.values.tolist()
                ),
            },
            # `text` goes to the LLM and citations; `embed_text` kept for debugging retrieval
            payload={**chunk.metadata, "text": chunk.text, "embed_text": chunk.embed_text},
        )


def index_chunks(
    client: QdrantClient, chunks: list[Chunk], ids: list[str], batch_size: int = 64
) -> None:
    dense = TextEmbedding(EMBED_MODEL)
    sparse = SparseTextEmbedding(SPARSE_MODEL, avg_len=bm25_avg_len([c.embed_text for c in chunks]))
    client.upload_points(
        COLLECTION_NAME,
        points=build_points(chunks, ids, dense, sparse),
        batch_size=batch_size,
        wait=True,
    )
