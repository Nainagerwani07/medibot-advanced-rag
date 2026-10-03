"""Chat pipeline: role (from the JWT) -> router -> SQL RAG or hybrid+rerank -> answer (R6 /chat).

Security boundaries (docs/ARCHITECTURE.md section 3):
- documents: every Qdrant query carries the role filter (HybridRetriever), whatever the router says
- SQL: only SQL_ROLES reach sql_rag, checked here from the role argument, never from the question
The router's collection guess is only used to explain a refusal (D8).
"""

import logging
from dataclasses import dataclass, field

from medibot.generation.answer import NOT_FOUND, generate_answer
from medibot.rbac import ROLE_COLLECTIONS
from medibot.retrieval.hybrid import HybridRetriever
from medibot.retrieval.rerank import Reranker
from medibot.routing.router import Route, route
from medibot.sql_rag.chain import SQL_ROLES, UnsafeSQLError, sql_rag

log = logging.getLogger(__name__)

ROLE_LABELS = {
    "doctor": "a doctor",
    "nurse": "a nurse",
    "billing_executive": "a billing executive",
    "technician": "a technician",
    "admin": "an admin",
}


@dataclass
class ChatResult:
    answer: str
    sources: list[dict]
    retrieval_type: str  # "hybrid_rag" | "sql_rag"
    role: str
    blocked: bool = False
    debug: dict = field(default_factory=dict)  # route, SQL, rerank scores (logged, not returned)


def _join(items) -> str:
    items = sorted(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def refusal(role: str, blocked: frozenset[str], sql: bool = False) -> str:
    """R1.3 wording: say what is off-limits and what the role *can* ask about."""
    allowed = ROLE_COLLECTIONS[role]
    if sql:
        what = "the claims and maintenance analytics database"
    else:
        what = f"{_join(blocked)} documents" if blocked else "that information"
    return (
        f"As {ROLE_LABELS[role]}, you do not have access to {what}. "
        f"I can only answer questions from the {_join(allowed)} collections."
    )


class ChatService:
    def __init__(self, retriever: HybridRetriever | None = None, reranker: Reranker | None = None):
        self.retriever = retriever or HybridRetriever()
        self.reranker = reranker or Reranker()

    def chat(self, question: str, role: str) -> ChatResult:
        if role not in ROLE_COLLECTIONS:
            raise ValueError(f"unknown role {role!r}")
        r: Route = route(question)
        log.info(
            "route role=%s type=%s targets=%s via=%s",
            role,
            r.type,
            sorted(r.target_collections),
            r.via,
        )
        allowed = ROLE_COLLECTIONS[role]

        if r.type == "analytical":
            if role not in SQL_ROLES:  # R5.3
                msg = refusal(role, frozenset(), sql=True)
                return ChatResult(msg, [], "sql_rag", role, blocked=True)
            try:
                res = sql_rag(question)
            except UnsafeSQLError as e:
                log.warning("sql rejected: %s", e)
                return ChatResult(
                    f"I couldn't run a safe query for that question ({e}).", [], "sql_rag", role
                )
            src = {
                "source_document": "mediassist.db",
                "section_title": res.sql,
                "collection": "database",
            }
            return ChatResult(res.answer, [src], "sql_rag", role, debug={"sql": res.sql})

        # Always search (D30). The router's guess only words the refusal; it never skips the
        # search, because a wrong guess ("needles" -> equipment) would hide an allowed answer.
        blocked = r.target_collections - allowed
        candidates = self.retriever.search(question, role)  # role filter inside Qdrant (R1.1)
        top = self.reranker.rerank(question, candidates)  # top-10 -> top-3, scores logged (R4)
        ans = generate_answer(question, top)
        if ans.text == NOT_FOUND and blocked:
            # the allowed docs don't answer it, and it looks aimed at a blocked collection
            return ChatResult(refusal(role, blocked), [], "hybrid_rag", role, blocked=True)
        text = ans.text
        if blocked and r.target_collections & allowed:
            # mixed question: answered the allowed part; say why the rest is missing.
            # (All targets blocked but an answer found = the router guessed wrong; no note.)
            text += f"\n\nNote: {refusal(role, blocked)}"
        scores = [(c.metadata["source_document"], round(c.score, 3)) for c in top]
        return ChatResult(text, ans.sources, "hybrid_rag", role, debug={"rerank": scores})
