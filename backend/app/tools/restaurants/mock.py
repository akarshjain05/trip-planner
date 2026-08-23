"""Deterministic mock restaurant/food results, is_mock=True."""
from __future__ import annotations
import random
from app.schemas.domain import RestaurantModel

_CUISINES = ["local", "street food", "japanese", "italian", "seafood", "vegetarian", "cafe", "fine dining"]
_PRICE_LEVELS = ["$", "$$", "$$$", "$$$$"]


class MockRestaurantProvider:
    async def search_restaurants(self, destination: str, cuisine_preferences: list[str]) -> list[RestaurantModel]:
        dest = destination.split(",")[0]
        seed = abs(hash(dest.lower())) % (2**32)
        rng = random.Random(seed)
        cuisines = list(dict.fromkeys([*(c.lower() for c in cuisine_preferences), *_CUISINES]))[:7]
        results = []
        for i, cuisine in enumerate(cuisines):
            results.append(RestaurantModel(
                name=f"{dest} {cuisine.title()} House #{i + 1}",
                cuisine=cuisine, price_level=rng.choice(_PRICE_LEVELS),
                description=f"Locally loved spot for {cuisine} food in {dest} (demo data).",
                rating=round(rng.uniform(3.8, 4.9), 1), is_mock=True,
            ))
        return results
