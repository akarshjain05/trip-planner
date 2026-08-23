"""Everything a node needs besides the state itself, bundled once per
graph build (see app/agents/graph.py::build_trip_graph). Keeping this as
plain constructor injection -- not globals, not contextvars -- is what
makes nodes trivial to unit test with fake providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Awaitable

from app.ai.orchestrator import LLMOrchestrator
from app.core.config import Settings


EmitFn = Callable[..., Awaitable[None]]


@dataclass
class NodeDeps:
    settings: Settings
    orchestrator: LLMOrchestrator
    flight_provider: object
    hotel_provider: object
    places_provider: object
    restaurant_provider: object
    weather_provider: object
    currency_provider: object
    maps_provider: object
    web_search_provider: object
    emit: EmitFn
