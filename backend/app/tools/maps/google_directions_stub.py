"""Real adapter interface for Google Routes API (Directions). NOT exercised
in this session (no network egress, no key). Reuses GOOGLE_PLACES_API_KEY
if your Google Cloud project has Routes API enabled on the same key."""
from __future__ import annotations
from app.core.config import Settings
from app.tools.base import ProviderError


class GoogleDirectionsProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def estimate_travel_time(self, origin: str, destination: str, mode: str = "transit") -> dict:
        if not self._settings.GOOGLE_PLACES_API_KEY:
            raise ProviderError("google_directions", "GOOGLE_PLACES_API_KEY not configured", retriable=False)
        raise ProviderError("google_directions", "Adapter interface only -- implement the Routes API call here.", retriable=False)
