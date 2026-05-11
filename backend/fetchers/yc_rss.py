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
    detect_work_mode,
    extract_experience,
)

logger = logging.getLogger(__name__)

# Algolia HN search API — reliable replacement for the defunct jobs.rss
_HN_API = "https://hn.algolia.com/api/v1/search_by_date"
_SEARCH_LOWER = [t.lower() for t in SEARCH_TITLES]


def _matches_search(title: str) -> bool:
    low = title.lower()
    return any(term in low for term in _SEARCH_LOWER)


def _parse_posted(iso: str | None) -> datetime:
    if not iso:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def _extract_company(title: str) -> str:
    # HN job titles are often "Role at Company (YC SXX)" or "Company is hiring Role"
    if " at " in title:
        return title.split(" at ", 1)[1].split("(")[0].strip()
    if " is hiring" in title.lower():
        return title.lower().split(" is hiring")[0].strip().title()
    return "YC Company"


def _extract_location(text: str) -> str:
    low = text.lower()
    if "remote" in low:
        return "Remote"
    if "san francisco" in low or "sf, ca" in low:
        return "San Francisco"
    if "new york" in low or "nyc" in low:
        return "New York"
    if "bengaluru" in low or "bangalore" in low:
        return "Bengaluru"
    return "Unknown"


async def fetch(session: aiohttp.ClientSession) -> List[NormalizedJob]:
    jobs: List[NormalizedJob] = []
    seen_urls: set[str] = set()

    try:
        params = {
            "tags": "job",
            "hitsPerPage": "100",
        }
        async with session.get(_HN_API, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning("YC/HN Algolia: HTTP %s", resp.status)
                return []
            data = await resp.json()

        for hit in data.get("hits", []):
            title = hit.get("title") or ""
            if not _matches_search(title):
                continue

            # HN jobs link to the HN item page; use objectID to build URL
            hn_id = hit.get("objectID") or ""
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            raw_desc = hit.get("story_text") or hit.get("comment_text") or ""
            company = _extract_company(title)
            location = _extract_location(raw_desc + " " + title)
            posted = _parse_posted(hit.get("created_at"))

            jobs.append(NormalizedJob(
                title=title,
                company=company,
                location=location,
                url=url,
                source="yc",
                raw_description=raw_desc,
                seniority=detect_seniority(title),
                experience_required=extract_experience(raw_desc),
                work_mode=detect_work_mode(raw_desc + " " + title),
                posted_date=posted,
                canonical_id=compute_canonical_id(company, title, location),
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                founding_signal=True,
            ))

        logger.info("YC/HN: fetched %d matching jobs", len(jobs))
        return jobs

    except Exception as exc:
        logger.warning("YC/HN: error: %s", exc)
        return []
