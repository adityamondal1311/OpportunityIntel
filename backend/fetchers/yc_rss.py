from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List

import aiohttp
import feedparser

from .base import (
    NormalizedJob,
    SEARCH_TITLES,
    compute_canonical_id,
    detect_seniority,
    detect_work_mode,
    extract_experience,
)

logger = logging.getLogger(__name__)

_RSS_URL = "https://news.ycombinator.com/jobs.rss"
_SEARCH_LOWER = [t.lower() for t in SEARCH_TITLES]


def _parse_posted(entry) -> datetime:
    try:
        return parsedate_to_datetime(entry.get("published", "")).replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _matches_search(title: str) -> bool:
    low = title.lower()
    return any(term in low for term in _SEARCH_LOWER)


def _parse_feed(content: bytes) -> feedparser.FeedParserDict:
    return feedparser.parse(content)


async def fetch(session: aiohttp.ClientSession) -> List[NormalizedJob]:
    try:
        async with session.get(_RSS_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning("YC RSS: HTTP %s", resp.status)
                return []
            content = await resp.read()

        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, _parse_feed, content)

        jobs: List[NormalizedJob] = []
        for entry in feed.entries:
            title = entry.get("title") or ""
            if not _matches_search(title):
                continue

            url = entry.get("link") or ""
            raw_desc = entry.get("summary") or ""
            company = _extract_company(title)
            location = _extract_location(raw_desc)
            posted = _parse_posted(entry)

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
                founding_signal=True,  # all YC jobs get founding_signal by default
            ))

        logger.info("YC RSS: fetched %d matching jobs", len(jobs))
        return jobs

    except Exception as exc:
        logger.warning("YC RSS: error: %s", exc)
        return []


def _extract_company(title: str) -> str:
    # YC RSS titles are often "Role at Company (YC SXX)"
    if " at " in title:
        return title.split(" at ", 1)[1].split("(")[0].strip()
    return "YC Company"


def _extract_location(summary: str) -> str:
    low = summary.lower()
    if "remote" in low:
        return "Remote"
    if "san francisco" in low or "sf" in low:
        return "San Francisco"
    if "new york" in low or "nyc" in low:
        return "New York"
    return "Unknown"
