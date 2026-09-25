# Decision Log

A short record of each decision: what we chose and why. New entries go at the bottom.

| # | Date | Decision | Alternatives | Why |
|---|---|---|---|---|
| D1 | 2026-09-24 | **Groq** for LLM inference. *Updated 2026-09-25:* Llama 3.x 70B isn't offered on our key; candidates are `openai/gpt-oss-120b` (answers) and `openai/gpt-oss-20b` (router, NL→SQL); final pick on Day 7 after testing | OpenAI, Anthropic, Gemini | Meets "cloud-hosted LLM" requirement; free tier; fast (~0.2 s/call measured); matches bootcamp notebook |
| D2 | 2026-09-24 | **Qdrant in Docker** | in-memory, local file mode, Qdrant Cloud | Index survives restarts; closest to production; Docker available |
| D3 | 2026-09-24 | **qdrant-client directly**, no LangChain vector-store wrapper | `langchain_qdrant.QdrantVectorStore(RetrievalMode.HYBRID)` | Learning goal: see prefetch, fusion and filter directly; RBAC filter placement is easy to audit |
| D4 | 2026-09-24 | **CPU-only** stack: FastEmbed (ONNX) embeddings, MiniLM-L-6 cross-encoder, Docling with OCR off | GPU models, larger rerankers | No GPU on dev machine; PDFs are digital so OCR isn't needed |
| D5 | 2026-09-24 | **One** Qdrant collection + `access_roles` payload filter | One Qdrant collection per document collection | The brief asks for metadata-filtered RBAC; admin cross-collection search stays a single query |
| D6 | 2026-09-24 | Role comes **from the JWT**, not the `/chat` body | Trust `role` in the request as the brief literally says | Otherwise anyone can send `role: admin`; server-side authorization |
| D7 | 2026-09-24 | `doctor` can access `nursing` | Only clinical + general, as in the brief's role table | The brief's data-source table lists doctor under nursing; the two tables disagree, and we follow the more specific one |
| D8 | 2026-09-24 | Router's target-collection guess is used **only for the refusal message** | Using the router as the access check | An LLM router can be prompt-injected; the Qdrant filter is the real boundary |
| D9 | 2026-09-24 | SQL executes read-only, SELECT/WITH only, row limit | Execute whatever the LLM returns | LLM output is untrusted input |
| D10 | 2026-09-25 | **uv** for Python and dependencies; Python 3.12 pinned; `uv.lock` committed | pip + venv, poetry | Fast, reproducible installs; manages the interpreter (system Python is 3.10) |
| D11 | 2026-09-25 | **src layout**: `backend/src/medibot/` installed as a package | Flat `backend/app/` | Same imports from scripts, tests and the API; tests run against the installed package |
| D12 | 2026-09-25 | **Quality gates:** pre-commit (gitleaks + custom Groq rule, ruff, large-file, private-key, no-commit-to-main); Claude hooks (branch guard, ruff on edit); `/start-session` and `/end-session` skills | Rely on discipline / CLAUDE.md text only | Enforced checks beat reminders. Testing showed default gitleaks **missed a bare Groq key**, hence the custom rule |
| D13 | 2026-09-25 | **Qdrant v1.19.1** pinned, ports bound to 127.0.0.1, named volume, no container healthcheck | `latest` tag, 0.0.0.0, bind mount | Version stays compatible with the client; no API key so it must not be network-reachable; image has no curl, so readiness is checked from Python via `/readyz` |
| D14 | 2026-09-25 | Dependencies added **on the day they're first used** | Install everything on Day 1 | Each dependency comes with its reason, and the git history shows why it was added |
