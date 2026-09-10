"""Import every model so Base.metadata is fully populated for Alembic
autogenerate and for create_all() in tests."""
from app.models.agent import AgentEvent, AgentRun  # noqa: F401
from app.models.itinerary import (  # noqa: F401
    Itinerary,
    ItineraryActivity,
    ItineraryDay,
    TripBudget,
)
from app.models.research import (  # noqa: F401
    Destination,
    FlightOption,
    HotelOption,
    Place,
    ResearchSource,
    Restaurant,
)
from app.models.trip import Trip, TripFeedback, TripRequirement  # noqa: F401
from app.models.user import User, UserPreferences  # noqa: F401

__all__ = [
    "User",
    "UserPreferences",
    "Trip",
    "TripRequirement",
    "TripFeedback",
    "Destination",
    "FlightOption",
    "HotelOption",
    "Place",
    "Restaurant",
    "ResearchSource",
    "Itinerary",
    "ItineraryDay",
    "ItineraryActivity",
    "TripBudget",
    "AgentRun",
    "AgentEvent",
]
from app.models.audit import AuditLog  # noqa: F401
__all__.append("AuditLog")
