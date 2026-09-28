"""Day 4: parse, chunk, embed and index every document into Qdrant (R2.5, R3.1).

Usage (from backend/, Qdrant running via `docker compose up -d`):
    uv run python scripts/ingest.py

Standalone on purpose (R2.5): model downloads and the ~200 s PDF parse (first run only) happen
here, never inside the API. Rebuilds the `medibot_docs` collection from scratch, then checks that
Qdrant's counts per collection and per role match the chunk list.
"""

import time
from collections import Counter

from explore_docling import DATA_DIR
from qdrant_client import models

from medibot.ingestion.chunking import build_chunker, chunk_document
from medibot.ingestion.indexing import (
    COLLECTION_NAME,
    create_collection,
    index_chunks,
    point_id,
    qdrant_client,
)
from medibot.ingestion.parsing import build_converter, load_document
from medibot.rbac import ROLE_COLLECTIONS

PARSED_DIR = DATA_DIR.parent / "parsed"


def load_chunks():
    chunker = build_chunker()
    converter = build_converter()
    chunks, ids = [], []
    for path in sorted(p for p in DATA_DIR.rglob("*") if p.suffix in {".pdf", ".md"}):
        doc_chunks = chunk_document(load_document(path, PARSED_DIR, converter), path, chunker)
        chunks += doc_chunks
        ids += [point_id(c, i) for i, c in enumerate(doc_chunks)]
    return chunks, ids


def count(client, key: str, values: list[str]) -> int:
    flt = models.Filter(must=[models.FieldCondition(key=key, match=models.MatchAny(any=values))])
    return client.count(COLLECTION_NAME, count_filter=flt, exact=True).count


def verify(client, chunks) -> bool:
    ok = True
    total = client.count(COLLECTION_NAME, exact=True).count
    print(f"\n=== verify: {total} points in Qdrant, {len(chunks)} chunks ===")
    ok &= total == len(chunks)

    expected = Counter(c.metadata["collection"] for c in chunks)
    print(f"  {'collection':<12}{'chunks':>8}{'qdrant':>8}")
    for col in sorted(expected):
        got = count(client, "collection", [col])
        ok &= got == expected[col]
        print(f"  {col:<12}{expected[col]:>8}{got:>8}")

    # what each role could ever retrieve: the filter Day 5 puts inside every query (R1.1)
    print(f"\n  {'role':<18}{'expected':>9}{'qdrant':>8}  collections")
    for role, cols in ROLE_COLLECTIONS.items():
        want = sum(expected[c] for c in cols)
        got = count(client, "access_roles", [role])
        ok &= got == want
        print(f"  {role:<18}{want:>9}{got:>8}  {', '.join(sorted(cols))}")
    print(f"\n  {'OK' if ok else 'MISMATCH'}")
    return ok


def main() -> None:
    t0 = time.perf_counter()
    chunks, ids = load_chunks()
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate point ids")
    print(f"chunked {len(chunks)} chunks in {time.perf_counter() - t0:.1f}s")

    client = qdrant_client()
    create_collection(client)
    t1 = time.perf_counter()
    index_chunks(client, chunks, ids)
    print(f"embedded + uploaded in {time.perf_counter() - t1:.1f}s")

    info = client.get_collection(COLLECTION_NAME)
    print(f"collection status: {info.status}, payload indexes: {sorted(info.payload_schema)}")
    sample = client.retrieve(COLLECTION_NAME, ids=[ids[0]], with_vectors=True)[0]
    payload = {k: v for k, v in sample.payload.items() if k not in {"text", "embed_text"}}
    print(f"sample point {sample.id}: payload {payload}")
    print(
        f"  dense[:4]={[round(x, 4) for x in sample.vector['dense'][:4]]}, "
        f"sparse entries={len(sample.vector['sparse'].indices)}"
    )
    if not verify(client, chunks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
