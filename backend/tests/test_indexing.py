"""Indexing rules from Day 4 (R2.5, R3.1, D19, D20) against an in-memory Qdrant (no Docker)."""

import pytest
from qdrant_client import QdrantClient, models

from medibot.ingestion.chunking import Chunk
from medibot.ingestion.indexing import (
    COLLECTION_NAME,
    DENSE_DIM,
    DENSE_VECTOR,
    SPARSE_VECTOR,
    create_collection,
    index_chunks,
    point_id,
)
from medibot.rbac import roles_for_collection


def _chunk(source: str, collection: str, text: str) -> Chunk:
    return Chunk(
        text=text,
        embed_text=text,
        metadata={
            "source_document": source,
            "collection": collection,
            "access_roles": roles_for_collection(collection),
            "section_title": "Test",
            "chunk_type": "text",
        },
    )


CHUNKS = [
    _chunk("drug_formulary.pdf", "clinical", "Ceftriaxone 1 g IV once daily."),
    _chunk("shift_handover.pdf", "nursing", "Hand over each patient at the bedside."),
    _chunk("billing_codes.pdf", "billing", "CPT 99213 is an established patient visit."),
    _chunk("leave_policy.pdf", "general", "Staff may not leave the ward mid-shift."),
]
IDS = [point_id(c, 0) for c in CHUNKS]


@pytest.fixture(scope="module")
def client() -> QdrantClient:
    client = QdrantClient(":memory:")
    create_collection(client)
    index_chunks(client, CHUNKS, IDS)
    return client


def test_point_id_is_stable_and_unique():
    chunk = CHUNKS[0]
    assert point_id(chunk, 3) == point_id(chunk, 3)  # re-runs overwrite the same point
    assert point_id(chunk, 3) != point_id(chunk, 4)
    assert point_id(chunk, 0) != point_id(CHUNKS[1], 0)  # same index, different document


def test_collection_has_dense_and_sparse_idf_vectors(client):
    params = client.get_collection(COLLECTION_NAME).config.params
    dense = params.vectors[DENSE_VECTOR]
    assert dense.size == DENSE_DIM
    assert dense.distance == models.Distance.COSINE
    assert params.sparse_vectors[SPARSE_VECTOR].modifier == models.Modifier.IDF


def test_every_point_stores_both_vectors_and_the_text(client):
    points = client.retrieve(COLLECTION_NAME, ids=IDS, with_vectors=True)
    assert len(points) == len(CHUNKS)
    for p in points:
        assert len(p.vector[DENSE_VECTOR]) == DENSE_DIM
        assert len(p.vector[SPARSE_VECTOR].indices) > 0
        assert p.payload["text"]


def test_reindexing_does_not_duplicate(client):
    index_chunks(client, CHUNKS, IDS)
    assert client.count(COLLECTION_NAME, exact=True).count == len(CHUNKS)


def test_access_roles_filter_limits_nurse_to_nursing_and_general(client):
    flt = models.Filter(
        must=[models.FieldCondition(key="access_roles", match=models.MatchAny(any=["nurse"]))]
    )
    points, _ = client.scroll(COLLECTION_NAME, scroll_filter=flt, limit=10)
    assert {p.payload["collection"] for p in points} == {"nursing", "general"}
