# OpportunityIntel — Progress Tracker

## ✅ Done
- **Layer 0 — Scaffold**: directories, requirements.txt, .env.example, .gitignore, PROGRESS.md
- **Layer 1A — Base schema**: `backend/fetchers/base.py` — NormalizedJob dataclass, canonical_id, seniority/work_mode/experience helpers
- **Layer 1B — Fetchers**: jsearch.py, adzuna.py, remotive.py, yc_rss.py — all fully async, silent error handling
- **Layer 2 — Pipeline**: dedup.py (exact + rapidfuzz), score_tech.py, score_trajectory.py, detect_flags.py, orchestrator.py
- **Layer 3 — Database**: models.py (SQLAlchemy Job), crud.py (upsert, filters, update, stats, CSV), session.py (AsyncSession), alembic full setup + initial migration applied
- **Layer 4 — API**: main.py — 5 endpoints, APScheduler auto-refresh, CORS, static file serving
- **Layer 5 — Frontend**: frontend/index.html — full dark-mode dashboard, all filters, sorting, inline editing, mock data fallback
- **README.md**: Setup guide, API reference, scoring explanation

## 🔄 In Progress
- End-to-end verification (server running, all endpoints tested)

## ⏳ Remaining
- Final GitHub push with README + frontend

## ⚠️ Architecture Decisions
- DB: aiosqlite + SQLAlchemy AsyncSession (fully async)
- Auto-refresh: APScheduler AsyncIOScheduler, default every 4h (REFRESH_INTERVAL_HOURS env var)
- Alembic: full setup with initial migration
- GitHub: push after each layer

## 📋 API Key Sources
| Source | URL | Key Needed? |
|--------|-----|-------------|
| JSearch (RapidAPI) | https://rapidapi.com/letscrape-6bghW3d0Gh/api/jsearch | Yes — JSEARCH_KEY |
| Adzuna | https://developer.adzuna.com | Yes — ADZUNA_APP_ID + ADZUNA_APP_KEY |
| Remotive | https://remotive.com/api/remote-jobs | No |
| YC Jobs RSS | https://news.ycombinator.com/jobs.rss | No |
