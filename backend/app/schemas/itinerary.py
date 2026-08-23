from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel

from app.models.itinerary import ActivityType, ItineraryStatus


class ActivityRead(BaseModel):
    id: uuid.UUID
    order_index: int
    time: str | None
    activity_type: ActivityType
    title: str
    description: str | None
    location: str | None
    estimated_cost: float | None
    duration_minutes: int | None
    source_ref: str | None

    model_config = {"from_attributes": True}


class DayRead(BaseModel):
    id: uuid.UUID
    day_number: int
    date: dt.date | None
    title: str | None
    weather_summary: str | None
    activities: list[ActivityRead]

    model_config = {"from_attributes": True}


class BudgetLineRead(BaseModel):
    category: str
    estimated_amount: float
    currency: str

    model_config = {"from_attributes": True}


class ItineraryRead(BaseModel):
    id: uuid.UUID
    version: int
    status: ItineraryStatus
    total_estimated_cost: float | None
    currency: str
    critic_notes: str | None
    days: list[DayRead]

    model_config = {"from_attributes": True}


class BudgetRead(BaseModel):
    total_budget: float | None
    currency: str
    lines: list[BudgetLineRead]
    total_estimated: float
    remaining: float | None
