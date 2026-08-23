from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin

# JSONB is Postgres-only; fall back to generic JSON so the same models work
# against SQLite in unit tests without touching production schema semantics.
try:
    from sqlalchemy.dialects.postgresql import JSONB as _JSONVariant
except ImportError:  # pragma: no cover
    _JSONVariant = JSON  # type: ignore


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserPreferences(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    home_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    travel_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget_range_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_range_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transportation_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)

    hotel_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    activity_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    food_preferences: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    favorite_destinations: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)
    dislikes: Mapped[list] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=list)

    user: Mapped["User"] = relationship(back_populates="preferences")
