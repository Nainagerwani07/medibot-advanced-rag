"""Cross-encoder reranking: top-10 hybrid candidates -> top-3 for the LLM (R4.1-R4.4).

A bi-encoder (bge-small) embeds query and chunk separately, so it can only compare two points in
vector space. A cross-encoder reads "[query] [SEP] [chunk]" as one input and every query token
attends to every chunk token, which is more accurate but costs one model pass per pair. That is
why it only sees the 10 candidates retrieval already found, never the whole index.

Model: ms-marco-MiniLM-L-6-v2 as ONNX via FastEmbed (D4, D23): CPU friendly, no torch at query time.
"""

import logging
from dataclasses import replace

from fastembed.rerank.cross_encoder import TextCrossEncoder

from medibot.retrieval.hybrid import RetrievedChunk

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 3

log = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model: str = RERANK_MODEL) -> None:
        self.model = TextCrossEncoder(model)

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_n: int = RERANK_TOP_N
    ) -> list[RetrievedChunk]:
        """Return the `top_n` chunks by cross-encoder score (a raw logit; higher = more relevant).

        The returned chunks carry the reranker score in `score`, replacing the RRF score.
        """
        if not chunks:
            return []
        # Same context the embeddings saw (R2.3): heading path + text. With the section title
        # alone, a Metformin table under "Pharmacological management" lost its disease.
        docs = [f"{c.heading_path}\n{c.text}" for c in chunks]
        scores = list(self.model.rerank(query, docs))
        order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
        for new_rank, i in enumerate(order):  # R4.4: log where rerank moves each candidate
            c = chunks[i]
            log.info(
                "rerank %2d <- rrf %2d  score=%7.3f  %s | %s",
                new_rank + 1,
                i + 1,
                scores[i],
                c.metadata.get("source_document"),
                c.metadata.get("section_title"),
            )
        return [replace(chunks[i], score=float(scores[i])) for i in order[:top_n]]
