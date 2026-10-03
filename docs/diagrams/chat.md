# `/chat` request flow (Days 6–8)

```mermaid
flowchart TD
    A["POST /chat<br/>Authorization: Bearer JWT<br/>body: {question, (role ignored)}"] --> B{"current_user()<br/>signature ok? exp ok?<br/>account's role == token role?"}
    B -->|no| E401[401]
    B -->|yes: role| R["route(question)<br/>gpt-oss-20b JSON, keyword fallback<br/>{type, target_collections}"]
    R -->|analytical| S{"role in<br/>billing_executive, admin?"}
    S -->|no| X["refusal (blocked=true)<br/>'As a technician, you do not have access to...'"]
    S -->|yes| SQL["sql_rag<br/>1 NL→SQL (20b) · 2 clean_sql · 3 read-only run (≤50 rows) + answer (120b)"]
    R -->|document| H["HybridRetriever.search<br/>dense + BM25 prefetch, RRF, role filter on every stage → top-10"]
    H --> RR["Reranker (MiniLM-L-6)<br/>scores heading path + text → top-3, scores logged"]
    RR --> G["generate_answer (gpt-oss-120b)<br/>numbered context, cite [n], 'not found' if absent"]
    G --> F{"answer found in<br/>the allowed docs?"}
    F -->|"no, and router flagged<br/>a blocked collection"| X
    F -->|"yes, mixed question<br/>(some targets allowed)"| NOTE["answer + note naming the blocked collection"]
    F -->|"yes / not found, nothing flagged"| OUT
    NOTE --> OUT["{answer, sources, retrieval_type, role, blocked}"]
    SQL --> OUT
    X --> OUT
```

The router decides the *path* and the *wording of a refusal*. It never decides *access*, and since D30 it never
skips the search either (a wrong guess used to hide allowed answers): if it's fooled into
calling a billing question "general", the Qdrant filter still only returns the role's collections
(`tests/test_service.py::test_fooled_router_still_cannot_leak_documents`), and SQL access is checked from the
token's role, not from the router.
