from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import JSON, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class TripStatus(str, enum.Enum):
    DRAFT = "draft"
    AWAITING_INPUT = "awaiting_input"
    PLANNING = "planning"
    COMPLETED = "completed"
    FAILED = "failed"


class Trip(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "trips"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), default="Untitled trip")
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus, native_enum=False), default=TripStatus.DRAFT)
    original_prompt: Mapped[str] = mapped_column(Text)

    # Full last-known LangGraph TripState, so a new request (resume after a
    # clarifying question, or a "modify my trip" partial replan) can
    # reconstruct exactly where the last run left off without depending on
    # the in-process checkpointer surviving across requests/processes.
    state_snapshot: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)

    user: Mapped["User"] = relationship(back_populates="trips")
    requirements: Mapped["TripRequirement | None"] = relationship(
        back_populates="trip", uselist=False, cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    itineraries: Mapped[list["Itinerary"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    feedback: Mapped[list["TripFeedback"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class TripRequirement(UUIDPKMixin, TimestampMixin, Base):
    """Structured requirements extracted from the user's natural-language request."""

    __tablename__ = "trip_requirements"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), unique=True)

    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    travelers: Mapped[int] = mapped_column(Integer, default=1)
    adults: Mapped[int] = mapped_column(Integer, default=1)
    children: Mapped[int] = mapped_column(Integer, default=0)

    budget_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_currency: Mapped[str] = mapped_column(String(8), default="INR")

    travel_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pace: Mapped[str | None] = mapped_column(String(32), nullable=True)
    climate_preferences: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accessibility_requirements: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Flexible free-text preference lists — genuinely variable-shape data,
    # a reasonable use of JSONB rather than a dedicated table each.
    hotel_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    food_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    activity_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    transportation_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    must_see: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    avoid: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    priorities: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    missing_fields: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)

    trip: Mapped["Trip"] = relationship(back_populates="requirements")


class TripFeedback(UUIDPKMixin, TimestampMixin, Base):
    """A user's conversational modification request ('hotels are too expensive')."""

    __tablename__ = "trip_feedback"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text)
    interpreted_changes: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)
    nodes_rerun: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)

    trip: Mapped["Trip"] = relationship(back_populates="feedback")
