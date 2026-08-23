from __future__ import annotations
import datetime as dt
from typing import Protocol


class WeatherProvider(Protocol):
    async def get_forecast(self, destination: str, start_date: dt.date | None, days: int) -> list[dict]: ...
