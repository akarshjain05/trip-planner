"""Deterministic mock travel-time estimates between two named locations."""
from __future__ import annotations
import random

_SPEED_KMH = {"walking": 4.5, "transit": 25, "driving": 30, "bicycling": 15}


class MockMapsProvider:
    async def estimate_travel_time(self, origin: str, destination: str, mode: str = "transit") -> dict:
        seed = abs(hash((origin.lower(), destination.lower(), mode))) % (2**32)
        rng = random.Random(seed)
        distance_km = round(rng.uniform(0.5, 18.0), 1)
        speed = _SPEED_KMH.get(mode, 20)
        minutes = max(round(distance_km / speed * 60), 3)
        return {"origin": origin, "destination": destination, "mode": mode,
                "distance_km": distance_km, "duration_minutes": minutes, "is_mock": True}
