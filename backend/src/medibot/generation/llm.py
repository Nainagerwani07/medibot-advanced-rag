"""Groq chat client (R3.4, D1, D24).

gpt-oss models reason before answering and those hidden tokens count toward the completion limit,
so the limit is generous and reasoning effort is set low: our prompts are lookups, not puzzles.
"""

import os
from functools import lru_cache

from groq import Groq

ANSWER_MODEL = os.environ.get("MEDIBOT_ANSWER_MODEL", "openai/gpt-oss-120b")
FAST_MODEL = os.environ.get("MEDIBOT_FAST_MODEL", "openai/gpt-oss-20b")  # router, NL->SQL


@lru_cache(maxsize=1)
def _client() -> Groq:
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set; load .env into the environment first")
    return Groq()


def chat(
    system: str,
    user: str,
    model: str = ANSWER_MODEL,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    resp = _client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        max_completion_tokens=max_tokens,
        reasoning_effort="low",
        response_format={"type": "json_object"} if json_mode else None,
    )
    return (resp.choices[0].message.content or "").strip()
