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
        # Validate horizon
        today = dt.date.today()
        target_date = start_date or today
        days_ahead = (target_date - today).days
        
        # Open-Meteo free API only supports up to 16 days of forecast.
        # If it's too far in the future, we raise ProviderError instead of masking it.
        if days_ahead > 16:
            raise ProviderError("open_meteo", f"Forecast horizon too far for '{destination}' (max 16 days, requested {days_ahead})", retriable=False)
            
        async with httpx.AsyncClient(timeout=10) as client:
            geo = await client.get(_GEOCODE_URL, params={"name": destination.split(",")[0], "count": 1})
            if geo.status_code != 200 or not geo.json().get("results"):
                raise ProviderError("open_meteo", f"could not geocode '{destination}'", retriable=False)
            loc = geo.json()["results"][0]

            params = {
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto", "forecast_days": min(max(days, 1), 16),
            }
            if start_date:
                params["start_date"] = str(start_date)
                params["end_date"] = str(start_date + dt.timedelta(days=min(days - 1, 15)))
                # When start_date and end_date are provided, forecast_days is not used
                if "forecast_days" in params:
                    del params["forecast_days"]

            resp = await client.get(_FORECAST_URL, params=params)
            if resp.status_code != 200:
                raise ProviderError("open_meteo", f"forecast failed: {resp.text}", retriable=True)
            daily = resp.json()["daily"]

        out = []
        for i, date_str in enumerate(daily["time"]):
            out.append({
                "date": date_str, "day_number": i + 1,
                "condition": _decode_weathercode(daily["weathercode"][i]),
                "temp_high_c": daily["temperature_2m_max"][i], "temp_low_c": daily["temperature_2m_min"][i],
                "rain_chance_pct": daily.get("precipitation_probability_max", [None])[i],
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
