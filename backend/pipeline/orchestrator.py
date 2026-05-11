from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from backend.fetchers import jsearch, adzuna, remotive, yc_rss
from backend.fetchers.base import NormalizedJob
from backend.pipeline.dedup import dedup
from backend.pipeline.score_tech import score_tech
from backend.pipeline.score_trajectory import score_trajectory
from backend.pipeline.detect_flags import detect_flags

logger = logging.getLogger(__name__)


async def run_pipeline(session: AsyncSession) -> dict[str, Any]:
    """Run the full fetch → dedup → score → persist pipeline.

    Returns stats dict with fetch summary.
    """
    # Import here to avoid circular import at module load time
    from backend.db import crud

    async with aiohttp.ClientSession() as http:
        # 1. Fetch from all sources concurrently
        results = await asyncio.gather(
            jsearch.fetch(http),
            adzuna.fetch(http),
            remotive.fetch(http),
            yc_rss.fetch(http),
            return_exceptions=True,
        )

    all_jobs: list[NormalizedJob] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Fetcher raised: %s", r)
        elif isinstance(r, list):
            all_jobs.extend(r)

    fetched_count = len(all_jobs)
    logger.info("Total fetched: %d", fetched_count)

    # 2. Load existing canonical_ids from DB
    existing_ids = await crud.get_all_canonical_ids(session)

    # 3. Dedup
    new_jobs, seen_in_fetch = dedup(all_jobs, existing_ids)
    duplicate_count = fetched_count - len(new_jobs)

    # 4. Score each new job
    for job in new_jobs:
        score_tech(job)
        score_trajectory(job)
        detect_flags(job)

    # 5. Persist
    await crud.upsert_jobs(new_jobs, session)
    await crud.mark_duplicates_seen(seen_in_fetch & existing_ids, session)

    # Mark jobs in DB that weren't seen in this fetch as inactive
    stale_ids = existing_ids - seen_in_fetch
    if stale_ids:
        await crud.mark_inactive(stale_ids, session)

    red_flagged = sum(1 for j in new_jobs if j.red_flag)
    founding_signals = sum(1 for j in new_jobs if j.founding_signal)

    stats = {
        "fetched": fetched_count,
        "new": len(new_jobs),
        "duplicates": duplicate_count,
        "red_flagged": red_flagged,
        "founding_signals": founding_signals,
    }
    logger.info("Pipeline complete: %s", stats)
    return stats
