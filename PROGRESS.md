# OpportunityIntel — Progress Tracker

## ✅ Done
- Nothing yet.

## 🔄 In Progress
- **Layer 0 — Scaffold**: Creating directory structure, requirements.txt, .env.example

## ⏳ Remaining
- Layer 1A: base.py (NormalizedJob dataclass)
- Layer 1B: Fetchers (jsearch, adzuna, remotive, yc_rss)
- Layer 2: Pipeline (dedup, score_tech, score_trajectory, detect_flags, orchestrator)
- Layer 3: Database (models, crud, session, alembic)
- Layer 4: API (main.py — FastAPI + APScheduler)
- Layer 5: Frontend (index.html)
- README.md + end-to-end verification

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
