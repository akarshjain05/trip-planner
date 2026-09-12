from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Destination(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "destinations"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rank: Mapped[int] = mapped_column(Integer, default=1)
    reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    suitability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)


class FlightOption(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "flight_options"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str] = mapped_column(String(16))
    depart_at: Mapped[str] = mapped_column(String(64))
    return_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    airline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stops: Mapped[int] = mapped_column(Integer, default=0)
    cabin: Mapped[str] = mapped_column(String(32), default="economy")
    baggage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)


class HotelOption(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "hotel_options"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price_per_night: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_center_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    amenities: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    raw_data: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)


class Place(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "places"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_visit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crowd_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)


class Restaurant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "restaurants"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    cuisine: Mapped[str | None] = mapped_column(String(128), nullable=True)
    price_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)


class ResearchSource(UUIDPKMixin, TimestampMixin, Base):
    """Every web-research fact retains provenance so the itinerary can cite it."""

    __tablename__ = "research_sources"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(1024))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_facts: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
