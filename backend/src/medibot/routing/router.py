"""Query router: SQL RAG or Hybrid RAG, plus a guess of which collections the question is about.

D8: `target_collections` only shapes the refusal message (R1.3). It is NOT the access check: if
the router is fooled, the Qdrant filter (documents) and the role check (SQL) still hold.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from medibot.generation.llm import FAST_MODEL, chat
from medibot.rbac import COLLECTIONS

log = logging.getLogger(__name__)

RouteType = Literal["document", "analytical"]


@dataclass(frozen=True)
class Route:
    type: RouteType
    target_collections: frozenset[str] = field(default_factory=frozenset)
    via: str = "llm"  # "llm" or "keywords" (fallback)


ROUTER_SYSTEM = """Classify a hospital staff question. Reply with JSON only:
{"type": "analytical" | "document", "target_collections": [...]}

type:
- "analytical": needs counting, totals, averages, rankings or listing of records from the
  database tables `claims` (insurance claims: status, amounts, insurer, department, dates) or
  `maintenance_tickets` (equipment tickets: category, campus, status, fault codes, dates).
- "document": anything answered by policy/protocol/manual text.

target_collections: which document collections the question is about (any of):
- general: HR, leave, salary, code of conduct, staff FAQs, campuses, emergency codes
- clinical: treatment protocols, drug formulary, doses, lab reference ranges, diagnosis
- nursing: ICU nursing procedures, infection control, hand hygiene, PPE, isolation precautions,
  waste segregation and bin colours, sharps and needlestick injuries, outbreaks
- billing: billing/ICD codes, package rates, insurers, claims process, pre-authorisation
- equipment: medical device manuals (monitors, infusion pumps, autoclave, x-ray), device fault
  codes, device maintenance and calibration
For analytical questions use billing for claims and equipment for maintenance tickets."""

_KEYWORDS = {
    "billing": r"billing|insur|claim|icd|package rate|pre-?auth|tpa|co-?pay|reimburs|excl-\d",
    "clinical": r"dose|dosage|drug|formulary|protocol|diagnos|treatment|mg\b|lab |haemoglobin|"
    r"troponin|antibiotic|metformin",
    "nursing": r"nurs|icu|ventilat|cannula|dressing|hand hygiene|ppe|infection|restrain|"
    r"needle|sharps|waste|bin\b",
    "equipment": r"equipment|fault code|monitor|infusion pump|autoclave|steril|x-?ray|"
    r"calibrat|maintenance",
    "general": r"leave|salary|holiday|payslip|conduct|handbook|resign|notice period|hr\b",
}
_ANALYTICAL = (
    r"\b(how many|count|total|sum|average|avg|mean|most|least|highest|lowest|top \d|"
    r"per (insurer|department|campus|category)|rate of|list (all|the))\b"
)


def keyword_route(question: str) -> Route:
    q = question.lower()
    targets = frozenset(c for c, pat in _KEYWORDS.items() if re.search(pat, q))
    analytical = bool(re.search(_ANALYTICAL, q)) and bool(
        re.search(r"claim|ticket|maintenance|insurer|rejected|approved|escalated", q)
    )
    return Route("analytical" if analytical else "document", targets, via="keywords")


def route(question: str) -> Route:
    try:
        raw = chat(ROUTER_SYSTEM, question, model=FAST_MODEL, max_tokens=512, json_mode=True)
        data = json.loads(raw)
        rtype = data.get("type")
        if rtype not in ("document", "analytical"):
            raise ValueError(f"bad type {rtype!r}")
        targets = frozenset(c for c in data.get("target_collections", []) if c in COLLECTIONS)
        return Route(rtype, targets)
    except Exception as e:  # noqa: BLE001 - any router failure falls back, never blocks the query
        log.warning("router fell back to keywords: %s", e)
        return keyword_route(question)
