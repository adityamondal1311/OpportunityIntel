from __future__ import annotations

from backend.fetchers.base import NormalizedJob

_SYSTEMS_WEIGHTS: dict[str, int] = {
    "kernel": 10,
    "memory management": 10,
    "concurrency": 9,
    "multithreading": 9,
    "lock-free": 10,
    "ipc": 9,
    "networking": 8,
    "tcp": 7,
    "performance": 7,
    "profiling": 8,
    "optimization": 7,
    "compiler": 9,
    "operating system": 9,
    "bare metal": 10,
}

_STARTUP_WEIGHTS: dict[str, int] = {
    "founding engineer": 10,
    "0 to 1": 10,
    "0→1": 10,
    "greenfield": 9,
    "ownership": 8,
    "end to end": 7,
    "end-to-end": 7,
    "wear many hats": 8,
    "small team": 7,
    "series a": 7,
    "series b": 6,
    "seed": 8,
    "yc": 9,
    "y combinator": 9,
    "backed": 6,
}

# Calibrated to ~35% of theoretical max for the same reason as score_tech.
_SYSTEMS_MAX: float = float(sum(_SYSTEMS_WEIGHTS.values())) * 0.35
_STARTUP_MAX: float = float(sum(_STARTUP_WEIGHTS.values())) * 0.33


def score_trajectory(job: NormalizedJob) -> None:
    desc = job.raw_description.lower()
    combined = desc + " " + job.title.lower()

    systems_matched = sum(w for kw, w in _SYSTEMS_WEIGHTS.items() if kw in desc)
    systems_score = min(100.0, (systems_matched / _SYSTEMS_MAX) * 100)

    startup_matched = sum(w for kw, w in _STARTUP_WEIGHTS.items() if kw in combined)
    startup_score = min(100.0, (startup_matched / _STARTUP_MAX) * 100)

    job.trajectory_score = (systems_score + startup_score) / 2
