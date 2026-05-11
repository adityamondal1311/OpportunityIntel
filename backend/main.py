from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

from backend.db.crud import get_jobs, get_stats, jobs_to_csv, update_job
from backend.db.session import AsyncSessionLocal, get_session, init_db
from backend.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── App state ────────────────────────────────────────────────────────────────

_last_refresh: datetime | None = None
_refresh_running: bool = False
_last_refresh_stats: dict | None = None
_scheduler = AsyncIOScheduler()


async def _run_refresh() -> None:
    global _last_refresh, _refresh_running, _last_refresh_stats
    if _refresh_running:
        logger.info("Refresh already in progress, skipping")
        return
    _refresh_running = True
    try:
        async with AsyncSessionLocal() as session:
            stats = await run_pipeline(session)
            _last_refresh = datetime.now(timezone.utc)
            _last_refresh_stats = stats
            logger.info("Refresh complete: %s", stats)
    except Exception as exc:
        logger.error("Refresh failed: %s", exc)
    finally:
        _refresh_running = False


async def _scheduled_refresh() -> None:
    logger.info("Auto-refresh triggered by scheduler")
    await _run_refresh()


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    interval_hours = float(os.getenv("REFRESH_INTERVAL_HOURS", "4"))
    _scheduler.add_job(
        _scheduled_refresh,
        trigger="interval",
        hours=interval_hours,
        id="auto_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — auto-refresh every %.1fh", interval_hours)

    yield

    _scheduler.shutdown(wait=False)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="OpportunityIntel", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: str
    seniority: str
    experience_required: str
    work_mode: str
    posted_date: datetime
    tech_match_score: float
    trajectory_score: float
    competition_score: float
    red_flag: bool
    founding_signal: bool
    first_seen: datetime
    last_seen: datetime
    still_active: bool
    applied: bool
    stage: str
    notes: str
    canonical_id: str

    class Config:
        from_attributes = True


class JobUpdate(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None
    applied: Optional[bool] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/jobs", response_model=dict[str, Any])
async def list_jobs(
    keyword: Optional[str] = Query(None),
    min_tech_score: float = Query(0),
    min_trajectory_score: float = Query(0),
    hide_red_flags: bool = Query(False),
    founding_only: bool = Query(False),
    source: Optional[str] = Query(None),
    work_mode: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    still_active: bool = Query(True),
    session: AsyncSession = Depends(get_session),
):
    filters = {
        "keyword": keyword,
        "min_tech_score": min_tech_score,
        "min_trajectory_score": min_trajectory_score,
        "hide_red_flags": hide_red_flags,
        "founding_only": founding_only,
        "source": source,
        "work_mode": work_mode,
        "stage": stage,
        "still_active": still_active,
    }
    jobs = await get_jobs(filters, session)
    stats = await get_stats(session)
    return {
        "jobs": [JobOut.model_validate(j).model_dump() for j in jobs],
        "total": stats["total"],
        "filtered": len(jobs),
        "stats": stats,
    }


@app.post("/jobs/refresh")
async def refresh_jobs():
    if _refresh_running:
        return {"status": "already_running", "message": "Refresh already in progress"}
    asyncio.create_task(_run_refresh())
    return {"status": "started", "message": "Refresh started in background"}


@app.patch("/jobs/{job_id}", response_model=JobOut)
async def patch_job(
    job_id: int,
    payload: JobUpdate,
    session: AsyncSession = Depends(get_session),
):
    job = await update_job(job_id, payload.model_dump(exclude_none=True), session)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@app.get("/jobs/export")
async def export_jobs(
    keyword: Optional[str] = Query(None),
    min_tech_score: float = Query(0),
    min_trajectory_score: float = Query(0),
    hide_red_flags: bool = Query(False),
    founding_only: bool = Query(False),
    source: Optional[str] = Query(None),
    work_mode: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    still_active: bool = Query(True),
    session: AsyncSession = Depends(get_session),
):
    filters = {
        "keyword": keyword,
        "min_tech_score": min_tech_score,
        "min_trajectory_score": min_trajectory_score,
        "hide_red_flags": hide_red_flags,
        "founding_only": founding_only,
        "source": source,
        "work_mode": work_mode,
        "stage": stage,
        "still_active": still_active,
    }
    jobs = await get_jobs(filters, session)
    csv_content = jobs_to_csv(jobs)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=opportunityintel_export.csv"},
    )


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    stats = await get_stats(session)
    return {
        "status": "ok",
        "db_count": stats["total"],
        "last_refresh": _last_refresh.isoformat() if _last_refresh else None,
        "refresh_running": _refresh_running,
        "last_refresh_stats": _last_refresh_stats,
    }


# ── Static frontend ───────────────────────────────────────────────────────────

_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(_frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found — place index.html in frontend/"}
