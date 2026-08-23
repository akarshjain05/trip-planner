"""Deterministic mock weather -- raw daily records, clearly demo data.
The weather_season agent node turns this into a WeatherOutlook."""
from __future__ import annotations
import datetime as dt
import random


class MockWeatherProvider:
    async def get_forecast(self, destination: str, start_date: dt.date | None, days: int) -> list[dict]:
        seed = abs(hash((destination.lower(), str(start_date)))) % (2**32)
        rng = random.Random(seed)
        conditions = ["Sunny", "Partly cloudy", "Sunny", "Light rain", "Partly cloudy", "Overcast"]
        out = []
        for i in range(max(days, 1)):
            cond = rng.choice(conditions)
            out.append({
                "date": str(start_date + dt.timedelta(days=i)) if start_date else None,
                "day_number": i + 1,
                "condition": cond,
                "temp_high_c": round(rng.uniform(18, 30), 1),
                "temp_low_c": round(rng.uniform(10, 18), 1),
                "rain_chance_pct": rng.randint(50, 85) if cond == "Light rain" else rng.randint(5, 25),
                "is_mock": True,
            })
        return out
