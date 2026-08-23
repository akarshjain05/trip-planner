"""Deterministic mock flight results -- clearly labeled is_mock=True.
Same (origin, destination, date, cabin) always yields the same options,
which keeps tests and caching behavior reproducible."""
from __future__ import annotations
import datetime as dt
import random
from app.schemas.domain import FlightOptionModel

_AIRLINES = ["Air India", "IndiGo", "ANA", "Japan Airlines", "Emirates", "Qatar Airways", "Singapore Airlines", "Vistara"]


class MockFlightProvider:
    async def search_flights(
        self, origin: str, destination: str,
        depart_date: dt.date | None = None, return_date: dt.date | None = None,
        adults: int = 1, cabin: str = "economy",
    ) -> list[FlightOptionModel]:
        seed = abs(hash((origin.lower(), destination.lower(), str(depart_date), cabin))) % (2**32)
        rng = random.Random(seed)
        base_price = rng.randint(18000, 55000)
        options = []
        for _ in range(4):
            stops = rng.choice([0, 0, 1, 1, 2])
            price = max(base_price - stops * rng.randint(500, 3000) + rng.randint(-2000, 4000), 8000)
            options.append(FlightOptionModel(
                provider="mock", origin=origin, destination=destination,
                depart_at=f"{depart_date or 'TBD'}T{rng.randint(5, 22):02d}:{rng.choice(['00', '15', '30', '45'])}",
                return_at=(f"{return_date}T{rng.randint(5, 22):02d}:00" if return_date else None),
                airline=rng.choice(_AIRLINES), price=float(price), currency="INR",
                duration_minutes=rng.randint(240, 900), stops=stops, cabin=cabin,
                baggage="1 checked bag (23kg) included", is_mock=True,
            ))
        return options
