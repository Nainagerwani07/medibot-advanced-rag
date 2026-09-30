"""Hybrid retrieval: dense + BM25 in one Qdrant request, RRF fusion, RBAC filter (R1.1, R3.2, R3.3).

One `query_points` call:
    prefetch dense  (top `prefetch_k`, role filter)  ┐
    prefetch sparse (top `prefetch_k`, role filter)  ┴─> RRF fusion (role filter) -> top `k`

The role filter is built only from `rbac.ROLE_COLLECTIONS`. Day 5 exploration showed Qdrant pushes a
top-level filter down into the prefetches; we still set it on every stage so a restricted chunk can
never become a fusion candidate, whatever the query shape.
"""

from dataclasses import dataclass
from typing import Literal

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

from medibot.ingestion.chunking import EMBED_MODEL
from medibot.ingestion.indexing import (
    COLLECTION_NAME,
    DENSE_VECTOR,
    SPARSE_MODEL,
    SPARSE_VECTOR,
    qdrant_client,
)
from medibot.rbac import ROLE_COLLECTIONS

TOP_K = 10  # broad set for the reranker to cut to 3 (R4.2)
PREFETCH_K = 20  # candidates per retriever before fusion
Mode = Literal["hybrid", "dense", "sparse"]  # dense/sparse only exist for the Day 6 eval baselines


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    score: float  # RRF score: rank-based, only comparable within one query
    text: str  # what the LLM reads and we cite
    metadata: dict  # source_document, collection, access_roles, section_title, chunk_type, ...

    @property
    def heading_path(self) -> str:
        """Full heading path below the document title, e.g. "A. Type 2 Diabetes > Pharmacological
        management". The section title alone is ambiguous: two protocols share that title."""
        headings = self.metadata.get("headings") or [self.metadata.get("section_title", "")]
        return " > ".join(headings[1:] or headings)


def role_filter(role: str) -> models.Filter:
    """Both must hold: the chunk lists this role, and it sits in a collection the role owns.

    The second check is defence in depth: a chunk indexed with stale `access_roles` still can't
    reach a role whose collections don't include it.
    """
    if role not in ROLE_COLLECTIONS:
        raise ValueError(f"unknown role {role!r}; expected one of {sorted(ROLE_COLLECTIONS)}")
    return models.Filter(
        must=[
            models.FieldCondition(key="access_roles", match=models.MatchValue(value=role)),
            models.FieldCondition(
                key="collection", match=models.MatchAny(any=sorted(ROLE_COLLECTIONS[role]))
            ),
        ]
    )


class HybridRetriever:
    """Holds the Qdrant client and both query encoders; build once (model load takes seconds)."""

    def __init__(self, client: QdrantClient | None = None) -> None:
        self.client = client or qdrant_client()
        self.dense = TextEmbedding(EMBED_MODEL)
        self.sparse = SparseTextEmbedding(SPARSE_MODEL)

    def search(
        self,
        query: str,
        role: str,
        k: int = TOP_K,
        prefetch_k: int = PREFETCH_K,
        mode: Mode = "hybrid",
        rrf_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """`rrf_k=None` keeps Qdrant's default (k=2, D22); the eval tries 60.

        Every mode applies the same role filter, so the baselines are compared under RBAC too.
        """
        flt = role_filter(role)  # first, so an unknown role fails before any search runs
        dense_vec = next(self.dense.query_embed(query)).tolist()
        s = next(self.sparse.query_embed(query))
        sparse_vec = models.SparseVector(indices=s.indices.tolist(), values=s.values.tolist())

        if mode == "dense":
            points = self.client.query_points(
                COLLECTION_NAME,
                query=dense_vec,
                using=DENSE_VECTOR,
                query_filter=flt,
                limit=k,
                with_payload=True,
            ).points
        elif mode == "sparse":
            points = self.client.query_points(
                COLLECTION_NAME,
                query=sparse_vec,
                using=SPARSE_VECTOR,
                query_filter=flt,
                limit=k,
                with_payload=True,
            ).points
        else:
            fusion = (
                models.FusionQuery(fusion=models.Fusion.RRF)
                if rrf_k is None
                else models.RrfQuery(rrf=models.Rrf(k=rrf_k))
            )
            points = self.client.query_points(
                COLLECTION_NAME,
                prefetch=[
                    models.Prefetch(
                        query=dense_vec, using=DENSE_VECTOR, limit=prefetch_k, filter=flt
                    ),
                    models.Prefetch(
                        query=sparse_vec, using=SPARSE_VECTOR, limit=prefetch_k, filter=flt
                    ),
                ],
                query=fusion,
                query_filter=flt,
                limit=k,
                with_payload=True,
            ).points

        return [
            RetrievedChunk(
                id=str(p.id),
                score=p.score,
                text=p.payload["text"],
                metadata={k_: v for k_, v in p.payload.items() if k_ not in ("text", "embed_text")},
            )
            for p in points
        ]
