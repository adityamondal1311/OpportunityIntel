from __future__ import annotations

from typing import List, Set, Tuple

from rapidfuzz import fuzz

from backend.fetchers.base import NormalizedJob

_FUZZY_THRESHOLD = 88


def _fuzzy_key(job: NormalizedJob) -> str:
    return (job.company + job.title).lower()


def dedup(
    jobs: List[NormalizedJob],
    existing_ids: Set[str],
) -> Tuple[List[NormalizedJob], Set[str]]:
    """Return (new_jobs, seen_canonical_ids).

    new_jobs: jobs not already in DB and not duplicates of each other.
    seen_canonical_ids: all canonical_ids present in this fetch (for still_active tracking).
    """
    seen_in_fetch: Set[str] = set()
    new_jobs: List[NormalizedJob] = []

    # Build fuzzy keys for jobs already committed to new_jobs (intra-fetch dedup)
    committed_fuzzy: List[str] = []

    for job in jobs:
        seen_in_fetch.add(job.canonical_id)

        # Exact match against DB
        if job.canonical_id in existing_ids:
            continue

        # Fuzzy match against already-accepted new jobs in this batch
        key = _fuzzy_key(job)
        is_dupe = False
        for existing_key in committed_fuzzy:
            if fuzz.ratio(key, existing_key) > _FUZZY_THRESHOLD:
                is_dupe = True
                break

        if not is_dupe:
            new_jobs.append(job)
            committed_fuzzy.append(key)

    return new_jobs, seen_in_fetch
