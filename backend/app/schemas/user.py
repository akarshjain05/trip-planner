from __future__ import annotations

from pydantic import BaseModel


class UserPreferencesUpdate(BaseModel):
    home_city: str | None = None
    currency: str | None = None
    travel_style: str | None = None
    budget_range_min: float | None = None
    budget_range_max: float | None = None
    pace: str | None = None
    transportation_preference: str | None = None
    hotel_preferences: list[str] | None = None
    activity_preferences: list[str] | None = None
    food_preferences: list[str] | None = None
    favorite_destinations: list[str] | None = None
    dislikes: list[str] | None = None


class UserPreferencesRead(BaseModel):
    home_city: str | None
    currency: str
    travel_style: str | None
    budget_range_min: float | None
    budget_range_max: float | None
    pace: str | None
    transportation_preference: str | None
    hotel_preferences: list[str]
    activity_preferences: list[str]
    food_preferences: list[str]
    favorite_destinations: list[str]
    dislikes: list[str]

    model_config = {"from_attributes": True}
