from __future__ import annotations
from typing import Protocol
from app.schemas.domain import RestaurantModel


class RestaurantProvider(Protocol):
    async def search_restaurants(self, destination: str, cuisine_preferences: list[str]) -> list[RestaurantModel]: ...
