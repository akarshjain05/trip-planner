from __future__ import annotations

import enum
import uuid

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class AgentRunStatus(str, enum.Enum):
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(UUIDPKMixin, TimestampMixin, Base):
    """One execution of the LangGraph workflow for a trip (initial plan or a
    partial replan triggered by user feedback)."""

    __tablename__ = "agent_runs"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"))
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus, native_enum=False), default=AgentRunStatus.RUNNING)
    trigger: Mapped[str] = mapped_column(String(32), default="initial_plan")  # initial_plan | modification
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="agent_runs")
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan", order_by="AgentEvent.created_at"
    )


class AgentEvent(UUIDPKMixin, TimestampMixin, Base):
    """A single node-execution / tool-call / critic-verdict event, also
    streamed live to the frontend over SSE as it happens."""

    __tablename__ = "agent_events"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(32))  # agent_started, agent_completed, tool_started, ...
    agent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB().with_variant(JSON, "sqlite"), default=dict)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="events")
