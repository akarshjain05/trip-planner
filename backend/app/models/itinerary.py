from __future__ import annotations

import enum
import uuid
import datetime as dt

from sqlalchemy import JSON, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ItineraryStatus(str, enum.Enum):
    DRAFT = "draft"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"


class ActivityType(str, enum.Enum):
    FLIGHT = "flight"
    TRANSFER = "transfer"
    MEAL = "meal"
    ATTRACTION = "attraction"
    HOTEL_CHECKIN = "hotel_checkin"
    HOTEL_CHECKOUT = "hotel_checkout"
    FREE_TIME = "free_time"
    OTHER = "other"


class Itinerary(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "itineraries"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ItineraryStatus] = mapped_column(Enum(ItineraryStatus, native_enum=False), default=ItineraryStatus.DRAFT)
    total_estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    critic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="itineraries")
    days: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="itinerary", cascade="all, delete-orphan", order_by="ItineraryDay.day_number"
    )
    budget_lines: Mapped[list["TripBudget"]] = relationship(back_populates="itinerary", cascade="all, delete-orphan")


class ItineraryDay(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_days"

    itinerary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("itineraries.id", ondelete="CASCADE"))
    day_number: Mapped[int] = mapped_column(Integer)
    date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weather_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)

    itinerary: Mapped["Itinerary"] = relationship(back_populates="days")
    activities: Mapped[list["ItineraryActivity"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="ItineraryActivity.order_index"
    )


class ItineraryActivity(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "itinerary_activities"

    itinerary_day_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("itinerary_days.id", ondelete="CASCADE"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType, native_enum=False), default=ActivityType.OTHER)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)

    day: Mapped["ItineraryDay"] = relationship(back_populates="activities")


class TripBudget(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "trip_budgets"

    itinerary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("itineraries.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(64))
    estimated_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    itinerary: Mapped["Itinerary"] = relationship(back_populates="budget_lines")
