"""Real hotel-provider adapter interface (e.g. Booking.com Demand API /
a GDS aggregator). NOT implemented against a live API in this session --
most hotel-search APIs require a signed partner agreement, not just an API
key, so there is no generic drop-in the way Amadeus offers for flights.

Fill in `search_hotels` against whatever real provider you contract with;
the FlightProvider/AmadeusFlightProvider pair in tools/flights/ shows the
expected shape (auth -> request -> normalize into HotelOptionModel)."""
from __future__ import annotations
import datetime as dt
from app.core.config import Settings
from app.schemas.domain import HotelOptionModel
from app.tools.base import ProviderError


class BookingComHotelProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def search_hotels(
        self, destination: str, check_in: dt.date | None = None, check_out: dt.date | None = None,
        adults: int = 1, rooms: int = 1, query: str | None = None,
    ) -> list[HotelOptionModel]:
        raise ProviderError(
            "booking_com",
            "Real hotel provider not wired to a live API in this build -- "
            "implement against your contracted provider here, or set "
            "HOTELS_PROVIDER=mock.",
            retriable=False,
        )
