from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

import aiohttp

from .base import (
    NormalizedJob,
    SEARCH_TITLES,
    compute_canonical_id,
    detect_seniority,
    extract_experience,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://remotive.com/api/remote-jobs"


def _parse_posted(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


async def fetch(session: aiohttp.ClientSession) -> List[NormalizedJob]:
    seen_urls: set[str] = set()
    jobs: List[NormalizedJob] = []

    for title in SEARCH_TITLES:
        try:
            params = {"search": title, "limit": "20"}
            async with session.get(_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning("Remotive: HTTP %s for %s", resp.status, title)
                    continue
                data = await resp.json()

            for item in data.get("jobs", []):
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                raw_desc = item.get("description") or ""
                job_title = item.get("title") or title
                company = item.get("company_name") or "Unknown"
                location = item.get("candidate_required_location") or "Remote"
                posted = _parse_posted(item.get("publication_date"))

                jobs.append(NormalizedJob(
                    title=job_title,
                    company=company,
                    location=location,
                    url=url,
                    source="remotive",
                    raw_description=raw_desc,
                    seniority=detect_seniority(job_title),
                    experience_required=extract_experience(raw_desc),
                    work_mode="remote",  # all Remotive jobs are remote
                    posted_date=posted,
                    canonical_id=compute_canonical_id(company, job_title, location),
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                ))

        except Exception as exc:
            logger.warning("Remotive: error for %s: %s", title, exc)

    logger.info("Remotive: fetched %d jobs", len(jobs))
    return jobs
