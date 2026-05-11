from __future__ import annotations

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

_BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"


def _parse_posted(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


async def fetch(session: aiohttp.ClientSession) -> List[NormalizedJob]:
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        logger.warning("Adzuna: ADZUNA_APP_ID or ADZUNA_APP_KEY not set, skipping")
        return []

    seen_urls: set[str] = set()
    jobs: List[NormalizedJob] = []

    for title in SEARCH_TITLES:
        for location in SEARCH_LOCATIONS:
            try:
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": title,
                    "where": location,
                    "results_per_page": "20",
                    "max_days_old": "1",
                }
                async with session.get(_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning("Adzuna: HTTP %s for %s/%s", resp.status, title, location)
                        continue
                    data = await resp.json()

                for item in data.get("results", []):
                    url = item.get("redirect_url") or ""
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    raw_desc = item.get("description") or ""
                    job_title = item.get("title") or title
                    company = (item.get("company") or {}).get("display_name") or "Unknown"
                    loc_obj = item.get("location") or {}
                    loc_str = loc_obj.get("display_name") or location

                    work_mode = detect_work_mode(raw_desc + " " + job_title + " " + loc_str)
                    posted = _parse_posted(item.get("created"))

                    jobs.append(NormalizedJob(
                        title=job_title,
                        company=company,
                        location=loc_str,
                        url=url,
                        source="adzuna",
                        raw_description=raw_desc,
                        seniority=detect_seniority(job_title),
                        experience_required=extract_experience(raw_desc),
                        work_mode=work_mode,
                        posted_date=posted,
                        canonical_id=compute_canonical_id(company, job_title, loc_str),
                        first_seen=datetime.now(timezone.utc),
                        last_seen=datetime.now(timezone.utc),
                    ))

            except Exception as exc:
                logger.warning("Adzuna: error for %s/%s: %s", title, location, exc)

    logger.info("Adzuna: fetched %d jobs", len(jobs))
    return jobs
