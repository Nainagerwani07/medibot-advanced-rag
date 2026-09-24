# Decision Log

A short record of each decision: what we chose and why. New entries go at the bottom.

| # | Date | Decision | Alternatives | Why |
|---|---|---|---|---|
| D1 | 2026-09-24 | **Groq** for LLM inference | OpenAI, Anthropic, Gemini | Meets "cloud-hosted LLM" requirement; free tier; fast; matches bootcamp notebook |
| D2 | 2026-09-24 | **Qdrant in Docker** | in-memory, local file mode, Qdrant Cloud | Index survives restarts; closest to production; Docker available |
| D3 | 2026-09-24 | **qdrant-client directly**, no LangChain vector-store wrapper | `langchain_qdrant.QdrantVectorStore(RetrievalMode.HYBRID)` | Learning goal: see prefetch, fusion and filter directly; RBAC filter placement is easy to audit |
| D4 | 2026-09-24 | **CPU-only** stack: FastEmbed (ONNX) embeddings, MiniLM-L-6 cross-encoder, Docling with OCR off | GPU models, larger rerankers | No GPU on dev machine; PDFs are digital so OCR isn't needed |
| D5 | 2026-09-24 | **One** Qdrant collection + `access_roles` payload filter | One Qdrant collection per document collection | The brief asks for metadata-filtered RBAC; admin cross-collection search stays a single query |
| D6 | 2026-09-24 | Role comes **from the JWT**, not the `/chat` body | Trust `role` in the request as the brief literally says | Otherwise anyone can send `role: admin`; server-side authorization |
| D7 | 2026-09-24 | `doctor` can access `nursing` | Only clinical + general, as in the brief's role table | The brief's data-source table lists doctor under nursing; the two tables disagree, and we follow the more specific one |
| D8 | 2026-09-24 | Router's target-collection guess is used **only for the refusal message** | Using the router as the access check | An LLM router can be prompt-injected; the Qdrant filter is the real boundary |
| D9 | 2026-09-24 | SQL executes read-only, SELECT/WITH only, row limit | Execute whatever the LLM returns | LLM output is untrusted input |
