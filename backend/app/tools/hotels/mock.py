"""Deterministic mock hotel results, is_mock=True."""
from __future__ import annotations
import datetime as dt
import random
from app.schemas.domain import HotelOptionModel

_TIERS = [
    ("{dest} Backpacker Hostel", 1200, 3.6, ["Free WiFi", "Shared kitchen"]),
    ("{dest} Budget Inn", 2600, 3.9, ["Free WiFi", "Breakfast included"]),
    ("{dest} Comfort Suites", 4800, 4.2, ["Free WiFi", "Breakfast", "Gym"]),
    ("{dest} Boutique Hotel", 7200, 4.5, ["Free WiFi", "Breakfast", "Spa", "Central location"]),
    ("Grand {dest} Palace", 13500, 4.8, ["Free WiFi", "Breakfast", "Spa", "Pool", "Concierge"]),
]


class MockHotelProvider:
    async def search_hotels(
        self, destination: str, check_in: dt.date | None = None, check_out: dt.date | None = None,
        adults: int = 1, rooms: int = 1,
    ) -> list[HotelOptionModel]:
        seed = abs(hash((destination.lower(), str(check_in), rooms))) % (2**32)
        rng = random.Random(seed)
        results = []
        for name_tpl, base_price, rating, amenities in _TIERS:
            jitter = rng.randint(-300, 400)
            results.append(HotelOptionModel(
                provider="mock", name=name_tpl.format(dest=destination.split(",")[0]),
                location=f"Central {destination.split(',')[0]}",
                price_per_night=float(max(base_price + jitter, 800)),
                currency="INR", rating=round(rating + rng.uniform(-0.1, 0.1), 1),
                distance_from_center_km=round(rng.uniform(0.3, 6.0), 1),
                amenities=amenities, is_mock=True,
            ))
        return results
