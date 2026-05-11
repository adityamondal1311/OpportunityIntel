from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Identity
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    # Raw — never discarded
    raw_description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Extracted
    seniority: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    experience_required: Mapped[str] = mapped_column(String(100), nullable=False, default="Not specified")
    work_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    posted_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Pipeline scores
    tech_match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trajectory_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    competition_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    red_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    founding_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Historical tracking
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    still_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # User layer
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="not_applied")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Dedup key
    canonical_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (
        Index("ix_jobs_canonical_id", "canonical_id"),
        Index("ix_jobs_source", "source"),
        Index("ix_jobs_posted_date", "posted_date"),
        Index("ix_jobs_tech_match_score", "tech_match_score"),
        Index("ix_jobs_trajectory_score", "trajectory_score"),
        Index("ix_jobs_red_flag", "red_flag"),
        Index("ix_jobs_founding_signal", "founding_signal"),
        Index("ix_jobs_still_active", "still_active"),
    )
