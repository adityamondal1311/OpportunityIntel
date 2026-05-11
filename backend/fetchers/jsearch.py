from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import List

import aiohttp

from .base import (
    NormalizedJob,
    SEARCH_TITLES,
    SEARCH_LOCATIONS,
    compute_canonical_id,
    detect_seniority,
    detect_work_mode,
    extract_experience,
)

logger = logging.getLogger(__name__)

_HOST = "jsearch.p.rapidapi.com"
_BASE_URL = f"https://{_HOST}/search"

# RapidAPI free tier allows ~5 req/s — cap concurrent calls to avoid 429s
_SEMAPHORE = asyncio.Semaphore(3)

_EMPLOYMENT_TYPE_MAP = {
    "FULLTIME": "onsite",
    "PARTTIME": "onsite",
    "CONTRACTOR": "onsite",
    "INTERN": "onsite",
}


def _parse_posted(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


async def _fetch_one(
    session: aiohttp.ClientSession,
    headers: dict,
    title: str,
    location: str,
    seen_urls: set,
) -> List[NormalizedJob]:
    async with _SEMAPHORE:
        try:
            params = {
                "query": f"{title} {location}",
                "num_pages": "1",
                "date_posted": "3days",  # wider window — "today" returns empty for many combos
            }
            async with session.get(
                _BASE_URL, headers=headers, params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 429:
                    logger.warning("JSearch: rate limited for %s/%s", title, location)
                    return []
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning("JSearch: HTTP %s for %s/%s — %s", resp.status, title, location, text[:120])
                    return []
                data = await resp.json(content_type=None)

        except asyncio.TimeoutError:
            logger.warning("JSearch: timeout for %s/%s", title, location)
            return []
        except Exception as exc:
            logger.warning("JSearch: error for %s/%s: %s (%s)", title, location, exc, type(exc).__name__)
            return []

    jobs: List[NormalizedJob] = []
    for item in data.get("data", []):
        url = item.get("job_apply_link") or item.get("job_url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        raw_desc = item.get("job_description") or ""
        job_title = item.get("job_title") or title
        company = item.get("employer_name") or "Unknown"
        city = item.get("job_city") or location
        emp_type = item.get("job_employment_type") or ""

        work_mode = detect_work_mode(raw_desc + " " + job_title)
        if work_mode == "unknown":
            work_mode = _EMPLOYMENT_TYPE_MAP.get(emp_type.upper(), "unknown")

        posted = _parse_posted(item.get("job_posted_at_datetime_utc"))

        jobs.append(NormalizedJob(
            title=job_title,
            company=company,
            location=city,
            url=url,
            source="jsearch",
            raw_description=raw_desc,
            seniority=detect_seniority(job_title),
            experience_required=extract_experience(raw_desc),
            work_mode=work_mode,
            posted_date=posted,
            canonical_id=compute_canonical_id(company, job_title, city),
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        ))

    return jobs


async def fetch(session: aiohttp.ClientSession) -> List[NormalizedJob]:
    api_key = os.getenv("JSEARCH_KEY", "")
    if not api_key:
        logger.warning("JSearch: JSEARCH_KEY not set, skipping")
        return []

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": _HOST,
    }

    seen_urls: set[str] = set()

    # Run all (title × location) combos concurrently, capped by semaphore
    tasks = [
        _fetch_one(session, headers, title, location, seen_urls)
        for title in SEARCH_TITLES
        for location in SEARCH_LOCATIONS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs: List[NormalizedJob] = []
    for r in results:
        if isinstance(r, list):
            jobs.extend(r)
        elif isinstance(r, Exception):
            logger.warning("JSearch gather error: %s", r)

    logger.info("JSearch: fetched %d jobs total", len(jobs))
    return jobs
