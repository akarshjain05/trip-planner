from __future__ import annotations
import datetime as dt
from typing import Protocol
from app.schemas.domain import FlightOptionModel


class FlightProvider(Protocol):
    async def search_flights(
        self, origin: str, destination: str,
        depart_date: dt.date | None = None, return_date: dt.date | None = None,
        adults: int = 1, cabin: str = "economy",
    ) -> list[FlightOptionModel]: ...
