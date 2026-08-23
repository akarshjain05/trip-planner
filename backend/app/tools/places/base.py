from __future__ import annotations
from typing import Protocol
from app.schemas.domain import PlaceModel


class PlacesProvider(Protocol):
    async def search_places(self, destination: str, interests: list[str]) -> list[PlaceModel]: ...
