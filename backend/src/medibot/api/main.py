"""FastAPI app (R6): /login, /chat, /collections/{role}, /health.

Run from backend/:  set -a; . ../.env; set +a; uv run uvicorn medibot.api.main:app --port 8000
"""

import logging
import os
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from medibot.api.auth import User, authenticate, create_token, current_user
from medibot.ingestion.indexing import qdrant_client
from medibot.rbac import ROLE_COLLECTIONS
from medibot.service import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("medibot.api")

app = FastAPI(title="MediBot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("MEDIBOT_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@lru_cache(maxsize=1)
def get_service() -> ChatService:
    """Built on first use (loads the embedding + reranker models); tests override this."""
    return ChatService()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - the OAuth2 scheme name, not a secret
    username: str
    role: str
    collections: list[str]


class ChatRequest(BaseModel):
    # extra fields such as "role" are ignored: the role comes from the token (R1.4, D6)
    model_config = ConfigDict(extra="ignore")
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    source_document: str
    section_title: str
    collection: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieval_type: Literal["hybrid_rag", "sql_rag"]
    role: str
    blocked: bool = False  # true for an RBAC refusal, so the UI can style it (R7)


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    user = authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")
    return LoginResponse(
        access_token=create_token(user),
        username=user.username,
        role=user.role,
        collections=sorted(ROLE_COLLECTIONS[user.role]),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user: User = Depends(current_user),  # noqa: B008
    service: ChatService = Depends(get_service),  # noqa: B008
) -> ChatResponse:
    result = service.chat(req.question, user.role)
    log.info(
        "chat user=%s role=%s type=%s blocked=%s sources=%d debug=%s",
        user.username,
        user.role,
        result.retrieval_type,
        result.blocked,
        len(result.sources),
        result.debug,
    )
    return ChatResponse(
        answer=result.answer,
        sources=[Source(**s) for s in result.sources],
        retrieval_type=result.retrieval_type,
        role=user.role,
        blocked=result.blocked,
    )


@app.get("/collections/{role}")
def collections(role: str, user: User = Depends(current_user)) -> dict:  # noqa: B008
    """Collections a role can read. Users may look up their own role; admin may look up any."""
    if role not in ROLE_COLLECTIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown role {role!r}")
    if role != user.role and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "you can only view your own role")
    return {"role": role, "collections": sorted(ROLE_COLLECTIONS[role])}


@app.get("/health")
def health() -> dict:
    try:
        qdrant_ok = bool(qdrant_client().get_collections())
    except Exception:  # noqa: BLE001 - health must answer even when Qdrant is down
        qdrant_ok = False
    return {"status": "ok" if qdrant_ok else "degraded", "qdrant": qdrant_ok}
