# MediBot — Advanced RAG with Retrieval-Layer RBAC

A secure internal healthcare assistant built with **Hybrid RAG** (dense + BM25), **cross-encoder reranking**,
**SQL RAG**, and **role-based access control enforced inside Qdrant**, not just in the UI.

> 🚧 **Work in progress.** Built step by step as a learning project. Progress is tracked in [docs/ROADMAP.md](docs/ROADMAP.md).

## The problem
MediAssist Health Network (12 hospitals, 40+ clinics) keeps its clinical protocols, drug formularies, billing guides and
equipment manuals in hundreds of PDFs. Staff can't find answers, and there are no access controls: a ward nurse can reach
billing and procurement data.

## What MediBot does
- **Structure-aware ingestion**: Docling parses headings and tables; HybridChunker splits by section first, then by token count.
  Each chunk keeps its heading context.
- **Hybrid retrieval**: dense (semantic) and BM25 (exact terms like drug names and ICD codes) searched in one Qdrant query
  and fused with RRF.
- **Reranking**: a cross-encoder narrows the top-10 candidates to the top-3 before the LLM sees them.
- **SQL RAG**: analytical questions ("how many claims were escalated last month?") are answered from SQLite.
- **RBAC at the retrieval layer**: every vector query carries an `access_roles` filter. The LLM never sees restricted chunks,
  so a prompt injection has nothing to leak.

## Architecture

```mermaid
flowchart LR
    U[User] -->|login| A[FastAPI + JWT]
    A --> R{Router}
    R -->|analytical + permitted role| S[SQL RAG over SQLite]
    R -->|document question| Q["Qdrant hybrid search<br/>dense + BM25 + RBAC filter"]
    Q --> RR[Cross-encoder rerank]
    RR --> L[Groq LLM]
    S --> O[Answer + sources + retrieval type]
    L --> O
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Roles

| Role | Collections |
|---|---|
| doctor | clinical, nursing, general |
| nurse | nursing, general |
| billing_executive | billing, general (+ SQL RAG) |
| technician | equipment, general |
| admin | all (+ SQL RAG) |

## Tech stack
Docling · FastEmbed (bge-small + BM25) · Qdrant · sentence-transformers cross-encoder · Groq (gpt-oss) · SQLite · FastAPI · Next.js · uv · ruff · pre-commit/gitleaks

## Documentation
| Doc | Contents |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Full requirements, traced to IDs R1–R8 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, security model |
| [docs/DECISIONS.md](docs/DECISIONS.md) | What we chose and why (including tool substitutions) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Day-by-day plan and session log |

## Setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/), Docker with Compose v2, [pre-commit](https://pre-commit.com/),
and a [Groq API key](https://console.groq.com/keys). CPU only; no GPU needed.

```bash
# 1. Python environment (uv installs Python 3.12 if missing)
cd backend && uv sync && cd ..

# 2. Git hooks (secret scanning, lint, main-branch guard)
pre-commit install

# 3. Qdrant vector DB (http://localhost:6333/dashboard)
docker compose up -d

# 4. Configuration
cp .env.example .env        # then put your GROQ_API_KEY in .env (never commit it)

# 5. Dataset (provided by the Codebasics bootcamp, not redistributed here)
mkdir -p data && unzip mediassist_data.zip -d data/
# expected: data/mediassist_data/{general,clinical,nursing,billing,equipment,db}/
```

Ingestion, backend and frontend run steps will be added as they're built (see [ROADMAP](docs/ROADMAP.md)).

## Adversarial RBAC tests
_Coming on Day 9._

## License
MIT
