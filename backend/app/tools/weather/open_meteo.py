"""Real weather adapter using Open-Meteo (open, keyless forecast + geocoding
API). Written against Open-Meteo's documented REST contract. NOT exercised
in this session -- this sandbox has no network egress to api.open-meteo.com
-- but unlike the other real adapters this one needs no API key at all, so
it's the easiest to turn on: just set WEATHER_PROVIDER=open_meteo."""
from __future__ import annotations
import datetime as dt
import httpx
from app.tools.base import ProviderError

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoWeatherProvider:
    async def get_forecast(self, destination: str, start_date: dt.date | None, days: int) -> list[dict]:
        today = dt.date.today()
        target_date = start_date or today
        days_ahead = (target_date - today).days
        
        async with httpx.AsyncClient(timeout=10) as client:
            geo = await client.get(_GEOCODE_URL, params={"name": destination.split(",")[0], "count": 1})
            if geo.status_code != 200 or not geo.json().get("results"):
                raise ProviderError("open_meteo", f"could not geocode '{destination}'", retriable=False)
            loc = geo.json()["results"][0]

            params = {
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
            }
            
            # If the date is more than 16 days in the future, we cannot use the forecast API.
            # Instead, we pull historical data for the exact same dates from the previous year as a climate proxy!
            api_url = _FORECAST_URL
            
            if days_ahead > 16:
                api_url = "https://archive-api.open-meteo.com/v1/archive"
                # Shift back in 1-year increments until the date is in the past (must be at least 5 days in the past for archive API)
                historical_start = target_date
                while (historical_start - today).days > -5:
                    try:
                        historical_start = historical_start.replace(year=historical_start.year - 1)
                    except ValueError:
                        # Handle leap day (Feb 29) by moving to Feb 28
                        historical_start = historical_start.replace(year=historical_start.year - 1, day=28)
                
                params["start_date"] = str(historical_start)
                params["end_date"] = str(historical_start + dt.timedelta(days=min(days - 1, 15)))
            else:
                params["daily"] += ",precipitation_probability_max"
                if start_date:
                    params["start_date"] = str(start_date)
                    params["end_date"] = str(start_date + dt.timedelta(days=min(days - 1, 15)))
                else:
                    params["forecast_days"] = min(max(days, 1), 16)

            resp = await client.get(api_url, params=params)
            if resp.status_code != 200:
                raise ProviderError("open_meteo", f"weather API failed: {resp.text}", retriable=True)
            daily = resp.json()["daily"]

        out = []
        for i, date_str in enumerate(daily["time"]):
            rain_chance = None
            if "precipitation_probability_max" in daily and i < len(daily["precipitation_probability_max"]):
                rain_chance = daily["precipitation_probability_max"][i]
                
            out.append({
                "date": date_str, "day_number": i + 1,
                "condition": _decode_weathercode(daily["weathercode"][i]),
                "temp_high_c": daily["temperature_2m_max"][i], "temp_low_c": daily["temperature_2m_min"][i],
                "rain_chance_pct": rain_chance,
                "is_mock": False,
            })
        return out


def _decode_weathercode(code: int) -> str:
    # WMO weather interpretation codes (Open-Meteo docs), collapsed to labels.
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Fog"
    if 51 <= code <= 67:
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if 80 <= code <= 82:
        return "Rain showers"
    if 95 <= code <= 99:
        return "Thunderstorm"
    return "Unknown"
