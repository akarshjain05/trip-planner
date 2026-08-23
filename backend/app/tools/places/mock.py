"""Deterministic mock places/attractions, is_mock=True.

Uses real, publicly-known attraction names for a handful of common demo
destinations (factual place names, not creative/copyrighted content) and
falls back to clearly-generic templated names for anything else."""
from __future__ import annotations
import random
from app.schemas.domain import PlaceModel

_CURATED: dict[str, list[dict]] = {
    "japan": [
        {"name": "Fushimi Inari Shrine", "category": "culture", "crowd": "high", "rating": 4.8, "cost": 0, "minutes": 120},
        {"name": "Arashiyama Bamboo Grove", "category": "nature", "crowd": "medium", "rating": 4.6, "cost": 0, "minutes": 60},
        {"name": "Kyoto International Manga Museum", "category": "anime", "crowd": "low", "rating": 4.5, "cost": 900, "minutes": 90},
        {"name": "Kiyomizu-dera Temple", "category": "culture", "crowd": "high", "rating": 4.7, "cost": 400, "minutes": 90},
        {"name": "Gion District Evening Walk", "category": "photography", "crowd": "medium", "rating": 4.5, "cost": 0, "minutes": 75},
        {"name": "Nara Deer Park", "category": "nature", "crowd": "medium", "rating": 4.6, "cost": 0, "minutes": 120},
        {"name": "teamLab Digital Art Museum", "category": "photography", "crowd": "high", "rating": 4.7, "cost": 3200, "minutes": 150},
        {"name": "Nishiki Market", "category": "food", "crowd": "high", "rating": 4.4, "cost": 1000, "minutes": 60},
        {"name": "Philosopher's Path", "category": "nature", "crowd": "low", "rating": 4.5, "cost": 0, "minutes": 60},
        {"name": "Kyoto Railway Museum", "category": "culture", "crowd": "low", "rating": 4.3, "cost": 1200, "minutes": 90},
        {"name": "Otagi Nenbutsu-ji Temple", "category": "photography", "crowd": "low", "rating": 4.6, "cost": 300, "minutes": 60},
        {"name": "Kurama Onsen Day Trip", "category": "nature", "crowd": "low", "rating": 4.5, "cost": 2000, "minutes": 150},
        {"name": "Pontocho Alley Food Walk", "category": "food", "crowd": "medium", "rating": 4.4, "cost": 0, "minutes": 60},
        {"name": "Kyoto Manga & Anime Fan Event Hall", "category": "anime", "crowd": "medium", "rating": 4.2, "cost": 1500, "minutes": 90},
        {"name": "Kodai-ji Temple Garden", "category": "nature", "crowd": "low", "rating": 4.4, "cost": 600, "minutes": 60},
        {"name": "Kyoto Botanical Gardens", "category": "nature", "crowd": "low", "rating": 4.3, "cost": 200, "minutes": 90},
        {"name": "Sagano Scenic Railway", "category": "photography", "crowd": "medium", "rating": 4.5, "cost": 880, "minutes": 60},
        {"name": "Uji Green Tea Farm Tour", "category": "food", "crowd": "low", "rating": 4.6, "cost": 1800, "minutes": 120},
    ],
    "kyoto": [],  # aliases resolved to japan below
    "bali": [
        {"name": "Tegallalang Rice Terraces", "category": "nature", "crowd": "medium", "rating": 4.5, "cost": 250, "minutes": 90},
        {"name": "Uluwatu Temple", "category": "culture", "crowd": "high", "rating": 4.6, "cost": 500, "minutes": 90},
        {"name": "Sekumpul Waterfall", "category": "nature", "crowd": "low", "rating": 4.7, "cost": 300, "minutes": 120},
        {"name": "Ubud Art Market", "category": "shopping", "crowd": "high", "rating": 4.1, "cost": 0, "minutes": 60},
    ],
    "paris": [
        {"name": "Louvre Museum", "category": "museum", "crowd": "high", "rating": 4.7, "cost": 1700, "minutes": 180},
        {"name": "Montmartre & Sacré-Cœur", "category": "photography", "crowd": "high", "rating": 4.6, "cost": 0, "minutes": 120},
        {"name": "Seine River Evening Cruise", "category": "nightlife", "crowd": "medium", "rating": 4.5, "cost": 1500, "minutes": 60},
    ],
}
_CURATED["kyoto"] = _CURATED["japan"]
_CURATED["tokyo"] = _CURATED["japan"]

_GENERIC_CATEGORIES = ["nature", "culture", "food", "photography", "adventure", "shopping", "nightlife", "museum"]


class MockPlacesProvider:
    async def search_places(self, destination: str, interests: list[str]) -> list[PlaceModel]:
        key = destination.split(",")[0].strip().lower()
        curated = _CURATED.get(key)
        if curated:
            return [
                PlaceModel(
                    name=p["name"], category=p["category"], description=f"Popular {p['category']} spot in {destination} (demo data).",
                    rating=p["rating"], estimated_visit_minutes=p["minutes"], estimated_cost=p["cost"],
                    opening_hours="09:00-18:00", crowd_level=p["crowd"], is_mock=True,
                )
                for p in curated
            ]

        seed = abs(hash(key)) % (2**32)
        rng = random.Random(seed)
        cats = list(dict.fromkeys([*(i.lower() for i in interests), *_GENERIC_CATEGORIES]))[:8]
        results = []
        for i, cat in enumerate(cats):
            results.append(PlaceModel(
                name=f"{destination.split(',')[0]} {cat.title()} Experience #{i + 1}",
                category=cat, description=f"A well-reviewed {cat} experience in {destination} (demo data).",
                rating=round(rng.uniform(3.9, 4.9), 1), estimated_visit_minutes=rng.choice([45, 60, 90, 120]),
                estimated_cost=float(rng.choice([0, 300, 800, 1500])),
                opening_hours="09:00-18:00", crowd_level=rng.choice(["low", "medium", "high"]), is_mock=True,
            ))
        return results
