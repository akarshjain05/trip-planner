"""Real Google Places (Nearby Search / Text Search, New) adapter interface.
NOT exercised in this session (no network egress to Google from this
sandbox, no key provided). Set GOOGLE_PLACES_API_KEY and
PLACES_PROVIDER=google_places to use; implement the HTTP call against
https://places.googleapis.com/v1/places:searchText following Google's
current field-mask requirements, normalizing each result into PlaceModel."""
from __future__ import annotations
from app.core.config import Settings
from app.schemas.domain import PlaceModel
from app.tools.base import ProviderError


class GooglePlacesProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def search_places(self, destination: str, interests: list[str]) -> list[PlaceModel]:
        if not self._settings.GOOGLE_PLACES_API_KEY:
            raise ProviderError("google_places", "GOOGLE_PLACES_API_KEY not configured", retriable=False)
        raise ProviderError(
            "google_places",
            "Adapter interface only in this build -- implement the Places API "
            "(New) Text Search call here, or set PLACES_PROVIDER=mock.",
            retriable=False,
        )
