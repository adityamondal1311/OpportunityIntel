from __future__ import annotations

from backend.fetchers.base import NormalizedJob

_WEIGHTS: dict[str, int] = {
    "c++": 10,
    "cuda": 10,
    "linux": 9,
    "distributed systems": 10,
    "systems programming": 9,
    "fastapi": 8,
    "python": 8,
    "asyncio": 8,
    "docker": 7,
    "kubernetes": 7,
    "kafka": 7,
    "websocket": 6,
    "postgresql": 6,
    "redis": 6,
    "llm": 7,
    "rag": 7,
    "embeddings": 7,
    "low latency": 9,
    "high performance": 8,
    "golang": 7,
    "rust": 8,
    "typescript": 5,
}

_MAX_SCORE: float = float(sum(_WEIGHTS.values()))


def score_tech(job: NormalizedJob) -> None:
    text = job.raw_description.lower()
    matched = sum(w for kw, w in _WEIGHTS.items() if kw in text)
    job.tech_match_score = min(100.0, (matched / _MAX_SCORE) * 100)
