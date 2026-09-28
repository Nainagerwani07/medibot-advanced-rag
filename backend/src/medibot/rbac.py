"""Single source of truth for who may read which collection (R1, docs/REQUIREMENTS.md section 2).

Ingestion stamps `access_roles` on every chunk from this map, and retrieval filters on it, so
changing access means editing this file and re-indexing, never touching prompts.
"""

ROLE_COLLECTIONS: dict[str, frozenset[str]] = {
    # D7: doctor also gets nursing (the brief's data-source table grants it)
    "doctor": frozenset({"clinical", "nursing", "general"}),
    "nurse": frozenset({"nursing", "general"}),
    "billing_executive": frozenset({"billing", "general"}),
    "technician": frozenset({"equipment", "general"}),
    "admin": frozenset({"general", "clinical", "nursing", "billing", "equipment"}),
}

COLLECTIONS: frozenset[str] = frozenset().union(*ROLE_COLLECTIONS.values())


def roles_for_collection(collection: str) -> list[str]:
    """Roles allowed to read a collection, sorted so payloads are deterministic."""
    if collection not in COLLECTIONS:
        raise ValueError(
            f"unknown collection {collection!r}; expected one of {sorted(COLLECTIONS)}"
        )
    return sorted(role for role, cols in ROLE_COLLECTIONS.items() if collection in cols)
