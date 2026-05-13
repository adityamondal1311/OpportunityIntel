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

# Calibrated to ~30% of theoretical max so that a job mentioning 4-5 strong
# keywords (e.g. python+docker+kubernetes+redis) scores around 50%, and an
# exceptional job scores 80-100%. Using full sum made avg scores ~7%.
_CALIBRATED_MAX: float = float(sum(_WEIGHTS.values())) * 0.30


def score_tech(job: NormalizedJob) -> None:
    text = job.raw_description.lower()
    matched = sum(w for kw, w in _WEIGHTS.items() if kw in text)
    job.tech_match_score = min(100.0, (matched / _CALIBRATED_MAX) * 100)
