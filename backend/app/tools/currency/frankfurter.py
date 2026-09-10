"""Real FX-rate adapter (e.g. exchangerate-api.com or Frankfurter.app).
NOT exercised in this session -- no network egress to either host from this
sandbox. Frankfurter.app needs no API key; exchangerate-api.com needs a
free-tier key -- set EXCHANGE_RATE_API_KEY (add to Settings if you use it)
and CURRENCY_PROVIDER=exchange_rate_api."""
from __future__ import annotations
import httpx
from app.tools.base import ProviderError

_BASE_URL = "https://api.frankfurter.dev/latest"


class FrankfurterCurrencyProvider:
    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(_BASE_URL, params={"from": from_currency.upper(), "to": to_currency.upper()})
        if resp.status_code != 200:
            raise ProviderError("frankfurter", f"rate lookup failed: {resp.text}", retriable=True)
        
        rates = resp.json().get("rates", {})
        if to_currency.upper() not in rates:
            raise ProviderError("frankfurter", f"Currency '{to_currency}' not supported.", retriable=False)
            
        return rates[to_currency.upper()]

    async def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        rate = await self.get_rate(from_currency, to_currency)
        return round(amount * rate, 2)
