from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel

from app.models.trip import TripStatus


class TripCreate(BaseModel):
    prompt: str


class TripModify(BaseModel):
    message: str


class TripRead(BaseModel):
    id: uuid.UUID
    title: str
    status: TripStatus
    original_prompt: str
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class TripStatusRead(BaseModel):
    trip_id: uuid.UUID
    status: TripStatus
    latest_agent_run_id: uuid.UUID | None = None
    awaiting_input: bool = False
    clarifying_question: str | None = None
