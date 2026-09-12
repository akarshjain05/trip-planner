from __future__ import annotations
import datetime as dt
from typing import Protocol
from app.schemas.domain import HotelOptionModel

class HotelProvider(Protocol):
    async def search_hotels(
        self, destination: str, check_in: dt.date | None = None, check_out: dt.date | None = None,
        adults: int = 1, rooms: int = 1, query: str | None = None
    ) -> list[HotelOptionModel]: ...
