from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

# ── Search parameters shared by all fetchers ────────────────────────────────

SEARCH_TITLES: List[str] = [
    "backend engineer",
    "software engineer",
    "systems engineer",
    "infrastructure engineer",
    "founding engineer",
    "AI engineer",
    "platform engineer",
    "SDE",
]

SEARCH_LOCATIONS: List[str] = ["Remote", "Bengaluru", "Hyderabad", "Mumbai"]

# ── Helper functions ─────────────────────────────────────────────────────────

_SENIORITY_SENIOR = {"senior", "sr", "lead", "staff", "principal", "architect", "head"}
_SENIORITY_ENTRY = {"junior", "jr", "entry", "graduate", "fresher", "intern", "trainee"}
_SENIORITY_MID = {"mid", " ii ", " iii ", "intermediate", "associate"}

_WORK_REMOTE = {"remote", "work from home", "wfh", "fully remote", "100% remote"}
_WORK_HYBRID = {"hybrid"}
_WORK_ONSITE = {"onsite", "on-site", "on site", "in-office", "in office", "office only"}

_EXP_PATTERN = re.compile(
    r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)"
    r"|(\d+)\+\s*(?:years?|yrs?)"
    r"|(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
    re.IGNORECASE,
)


def compute_canonical_id(company: str, title: str, location: str) -> str:
    city = location.split(",")[0].strip().lower() if location else ""
    raw = company.lower() + title.lower() + city
    return hashlib.md5(raw.encode()).hexdigest()


def detect_seniority(title: str) -> str:
    low = title.lower()
    if any(k in low for k in _SENIORITY_SENIOR):
        return "senior"
    if any(k in low for k in _SENIORITY_ENTRY):
        return "entry"
    if any(k in (" " + low + " ") for k in _SENIORITY_MID):
        return "mid"
    return "unknown"


def detect_work_mode(text: str) -> str:
    low = text.lower()
    if any(k in low for k in _WORK_REMOTE):
        return "remote"
    if any(k in low for k in _WORK_HYBRID):
        return "hybrid"
    if any(k in low for k in _WORK_ONSITE):
        return "onsite"
    return "unknown"


def extract_experience(text: str) -> str:
    m = _EXP_PATTERN.search(text)
    if not m:
        return "Not specified"
    if m.group(1) and m.group(2):
        return f"{m.group(1)}-{m.group(2)} years"
    if m.group(3):
        return f"{m.group(3)}+ years"
    if m.group(4):
        return f"{m.group(4)} years"
    return "Not specified"


# ── Core schema ──────────────────────────────────────────────────────────────

@dataclass
class NormalizedJob:
    # Identity
    title: str
    company: str
    location: str
    url: str
    source: str  # "jsearch" | "adzuna" | "remotive" | "yc"

    # Raw — never discard
    raw_description: str

    # Extracted
    seniority: str           # "entry" | "mid" | "senior" | "unknown"
    experience_required: str  # e.g. "0-2 years" | "Not specified"
    work_mode: str           # "remote" | "hybrid" | "onsite" | "unknown"
    posted_date: datetime

    # Dedup key
    canonical_id: str

    # Tracking
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    still_active: bool = True

    # Computed by pipeline (defaults at fetch time)
    tech_match_score: float = 0.0
    trajectory_score: float = 0.0
    competition_score: float = 0.0
    red_flag: bool = False
    founding_signal: bool = False

    # User layer (defaults)
    applied: bool = False
    stage: str = "not_applied"  # not_applied | applied | oa | interview | offer | rejected
    notes: str = ""
