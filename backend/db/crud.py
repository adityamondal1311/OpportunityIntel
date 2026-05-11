from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Set

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Job
from backend.fetchers.base import NormalizedJob


# ── Write operations ─────────────────────────────────────────────────────────

async def upsert_jobs(jobs: list[NormalizedJob], session: AsyncSession) -> None:
    for job in jobs:
        stmt = sqlite_insert(Job).values(
            canonical_id=job.canonical_id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            source=job.source,
            raw_description=job.raw_description,
            seniority=job.seniority,
            experience_required=job.experience_required,
            work_mode=job.work_mode,
            posted_date=_ensure_tz(job.posted_date),
            tech_match_score=job.tech_match_score,
            trajectory_score=job.trajectory_score,
            competition_score=job.competition_score,
            red_flag=job.red_flag,
            founding_signal=job.founding_signal,
            first_seen=_ensure_tz(job.first_seen),
            last_seen=_ensure_tz(job.last_seen),
            still_active=job.still_active,
            applied=job.applied,
            stage=job.stage,
            notes=job.notes,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["canonical_id"],
            set_={
                "last_seen": _ensure_tz(job.last_seen),
                "still_active": True,
                "tech_match_score": job.tech_match_score,
                "trajectory_score": job.trajectory_score,
                "competition_score": job.competition_score,
                "red_flag": job.red_flag,
                "founding_signal": job.founding_signal,
            },
        )
        await session.execute(stmt)
    await session.commit()


async def mark_duplicates_seen(ids: Set[str], session: AsyncSession) -> None:
    if not ids:
        return
    now = datetime.now(timezone.utc)
    stmt = (
        update(Job)
        .where(Job.canonical_id.in_(ids))
        .values(last_seen=now, still_active=True)
    )
    await session.execute(stmt)
    await session.commit()


async def mark_inactive(ids: Set[str], session: AsyncSession) -> None:
    if not ids:
        return
    stmt = (
        update(Job)
        .where(Job.canonical_id.in_(ids))
        .values(still_active=False)
    )
    await session.execute(stmt)
    await session.commit()


# ── Read operations ──────────────────────────────────────────────────────────

async def get_all_canonical_ids(session: AsyncSession) -> Set[str]:
    result = await session.execute(select(Job.canonical_id))
    return {row[0] for row in result.all()}


async def get_jobs(filters: dict[str, Any], session: AsyncSession) -> list[Job]:
    stmt = select(Job)

    still_active = filters.get("still_active", True)
    if still_active is not None:
        stmt = stmt.where(Job.still_active == still_active)

    min_tech = filters.get("min_tech_score", 0)
    if min_tech:
        stmt = stmt.where(Job.tech_match_score >= min_tech)

    min_traj = filters.get("min_trajectory_score", 0)
    if min_traj:
        stmt = stmt.where(Job.trajectory_score >= min_traj)

    if filters.get("hide_red_flags"):
        stmt = stmt.where(Job.red_flag == False)  # noqa: E712

    if filters.get("founding_only"):
        stmt = stmt.where(Job.founding_signal == True)  # noqa: E712

    if filters.get("source"):
        stmt = stmt.where(Job.source == filters["source"])

    if filters.get("work_mode"):
        stmt = stmt.where(Job.work_mode == filters["work_mode"])

    if filters.get("stage"):
        stmt = stmt.where(Job.stage == filters["stage"])

    if filters.get("keyword"):
        kw = f"%{filters['keyword'].lower()}%"
        from sqlalchemy import or_, func as sqlfunc
        stmt = stmt.where(
            or_(
                sqlfunc.lower(Job.title).like(kw),
                sqlfunc.lower(Job.company).like(kw),
                sqlfunc.lower(Job.raw_description).like(kw),
            )
        )

    stmt = stmt.order_by(Job.trajectory_score.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_job(job_id: int, payload: dict[str, Any], session: AsyncSession) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None

    if "stage" in payload:
        job.stage = payload["stage"]
    if "notes" in payload:
        job.notes = payload["notes"]
    if "applied" in payload:
        job.applied = payload["applied"]

    job.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(job)
    return job


async def get_stats(session: AsyncSession) -> dict[str, Any]:
    from sqlalchemy import func as sqlfunc
    total_q = await session.execute(select(sqlfunc.count()).select_from(Job))
    total = total_q.scalar() or 0

    active_q = await session.execute(
        select(sqlfunc.count()).select_from(Job).where(Job.still_active == True)  # noqa: E712
    )
    active = active_q.scalar() or 0

    applied_q = await session.execute(
        select(sqlfunc.count()).select_from(Job).where(Job.applied == True)  # noqa: E712
    )
    applied = applied_q.scalar() or 0

    by_source_q = await session.execute(
        select(Job.source, sqlfunc.count()).group_by(Job.source)
    )
    by_source = {row[0]: row[1] for row in by_source_q.all()}

    return {"total": total, "active": active, "applied": applied, "by_source": by_source}


# ── CSV export ───────────────────────────────────────────────────────────────

def jobs_to_csv(jobs: list[Job]) -> str:
    output = io.StringIO()
    fieldnames = [
        "id", "title", "company", "location", "work_mode", "source",
        "tech_match_score", "trajectory_score", "competition_score",
        "red_flag", "founding_signal", "seniority", "experience_required",
        "posted_date", "stage", "applied", "notes", "url",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        writer.writerow({f: getattr(job, f, "") for f in fieldnames})
    return output.getvalue()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
