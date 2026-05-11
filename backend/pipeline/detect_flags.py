from __future__ import annotations

from datetime import datetime, timezone

from backend.fetchers.base import NormalizedJob

_RED_FLAG_TERMS: list[str] = [
    "unpaid",
    "stipend only",
    "no salary",
    "6 days a week",
    "6 days/week",
    "immediate joiner",
    "immediate joining",
    "bond",
    "service agreement",
    "mass hiring",
    "walk-in",
    "bpo",
    "kpo",
    "data entry",
    "10+ years",
    "12+ years",
    "15+ years",
]

_FOUNDING_TERMS: list[str] = [
    "founding engineer",
    "founding team",
    "0 to 1",
    "0→1",
    "first engineer",
    "small team",
    "wear many hats",
    "work directly with founder",
    "greenfield",
    "build from scratch",
    "series a",
    "seed stage",
    "yc",
    "y combinator",
]


def detect_flags(job: NormalizedJob) -> None:
    desc_low = job.raw_description.lower()
    combined_low = desc_low + " " + job.title.lower()

    job.red_flag = any(term in desc_low for term in _RED_FLAG_TERMS)

    if job.source == "yc":
        job.founding_signal = True
    else:
        job.founding_signal = any(term in combined_low for term in _FOUNDING_TERMS)

    now = datetime.now(timezone.utc)
    posted = job.posted_date
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)

    posting_age_hours = (now - posted).total_seconds() / 3600
    competition_score = min(100.0, posting_age_hours * 2)

    if job.source == "yc":
        competition_score *= 0.7
    if job.founding_signal:
        competition_score *= 0.8

    job.competition_score = competition_score
