# OpportunityIntel

A job intelligence system that fetches, scores, deduplicates, and presents software engineering opportunities from 4 sources. Built for engineers targeting backend/systems/founding-engineer roles in India and remote.

## Features

- **4 data sources**: JSearch (RapidAPI), Adzuna, Remotive, YC Jobs RSS
- **Tech scoring**: weighted keyword match across 22 technologies (C++, CUDA, Python, Kafka, etc.)
- **Trajectory scoring**: systems depth + startup ownership signals
- **Smart dedup**: exact canonical_id match + rapidfuzz fuzzy matching (>88% similarity)
- **Red flag detection**: bonds, BPO, walk-ins, mass hiring, 10+ year requirements
- **Founding signal detection**: YC, seed stage, greenfield, 0→1 roles
- **Competition scoring**: based on posting age + source + founding signal
- **Auto-refresh**: APScheduler runs pipeline every N hours (configurable)
- **User tracking**: per-job stage (not_applied → offer), notes, applied flag
- **CSV export**: download filtered results
- **Dark-mode dashboard**: glassmorphism UI, score bars, inline editing

## Project Structure

```
opportunity-intel/
├── backend/
│   ├── fetchers/
│   │   ├── base.py              # NormalizedJob dataclass + helpers
│   │   ├── jsearch.py           # RapidAPI JSearch fetcher
│   │   ├── adzuna.py            # Adzuna Jobs API fetcher
│   │   ├── remotive.py          # Remotive public API fetcher
│   │   └── yc_rss.py            # YC Jobs RSS fetcher
│   ├── pipeline/
│   │   ├── dedup.py             # Exact + fuzzy deduplication
│   │   ├── score_tech.py        # Tech keyword scoring
│   │   ├── score_trajectory.py  # Systems + startup scoring
│   │   ├── detect_flags.py      # Red flags, founding signals, competition
│   │   └── orchestrator.py      # Async pipeline coordinator
│   ├── db/
│   │   ├── models.py            # SQLAlchemy Job model
│   │   ├── crud.py              # Async DB operations
│   │   └── session.py           # AsyncSession factory
│   └── main.py                  # FastAPI app + APScheduler
├── alembic/                     # Database migrations
├── frontend/
│   └── index.html               # Single-file dark-mode dashboard
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
git clone https://github.com/adityamondal1311/OpportunityIntel.git
cd OpportunityIntel
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your API keys (see below)
```

### Run database migrations

```bash
alembic upgrade head
```

### Start the server

```bash
uvicorn backend.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## API Keys

| Source | Signup URL | Env Var(s) | Cost |
|--------|-----------|------------|------|
| **JSearch** | [rapidapi.com/letscrape-6bghW3d0Gh/api/jsearch](https://rapidapi.com/letscrape-6bghW3d0Gh/api/jsearch) | `JSEARCH_KEY` | Free tier available |
| **Adzuna** | [developer.adzuna.com](https://developer.adzuna.com) | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Free |
| **Remotive** | No signup needed | — | Free |
| **YC Jobs RSS** | No signup needed | — | Free |

## Environment Variables

```
JSEARCH_KEY=your_key_here
ADZUNA_APP_ID=your_id_here
ADZUNA_APP_KEY=your_key_here
DATABASE_URL=sqlite+aiosqlite:///./opportunityintel.db
REFRESH_INTERVAL_HOURS=4
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/jobs` | List jobs with filters |
| `POST` | `/jobs/refresh` | Trigger full pipeline run |
| `PATCH` | `/jobs/{id}` | Update stage, notes, applied |
| `GET` | `/jobs/export` | Download filtered CSV |
| `GET` | `/health` | DB count + last refresh time |

### GET /jobs — query parameters

| Param | Default | Description |
|-------|---------|-------------|
| `keyword` | — | Search in title, company, description |
| `min_tech_score` | 0 | Minimum tech match % |
| `min_trajectory_score` | 0 | Minimum trajectory % |
| `hide_red_flags` | false | Exclude flagged jobs |
| `founding_only` | false | Only founding signal jobs |
| `source` | — | jsearch / adzuna / remotive / yc |
| `work_mode` | — | remote / hybrid / onsite |
| `stage` | — | not_applied / applied / oa / interview / offer / rejected |
| `still_active` | true | Only active listings |

## Scoring

**Tech Match %** — Scans job description for 22 weighted keywords (C++, CUDA, Python, FastAPI, Kafka, Kubernetes, LLM, RAG, etc.). Normalized to 0–100.

**Trajectory %** — Average of:
1. *Systems depth*: kernel, memory management, lock-free, IPC, compiler, bare metal, etc.
2. *Startup ownership*: founding engineer, 0→1, seed, YC, greenfield, wear many hats, etc.

**Competition score** — Based on posting age (older = more competition). Reduced for YC jobs (×0.7) and founding signal jobs (×0.8). LOW < 33, MED 33–66, HIGH > 66.
