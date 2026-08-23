from __future__ import annotations
from typing import Protocol


class MapsProvider(Protocol):
    async def estimate_travel_time(self, origin: str, destination: str, mode: str = "transit") -> dict: ...
