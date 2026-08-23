from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel

from app.models.agent import AgentRunStatus


class AgentEventRead(BaseModel):
    event_type: str
    agent_name: str | None
    message: str | None
    payload: dict
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class AgentRunRead(BaseModel):
    id: uuid.UUID
    status: AgentRunStatus
    trigger: str
    iteration_count: int
    tool_call_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    events: list[AgentEventRead]

    model_config = {"from_attributes": True}


class ResearchSourceRead(BaseModel):
    url: str
    title: str | None
    source: str | None
    extracted_facts: str | None
    confidence: float

    model_config = {"from_attributes": True}
