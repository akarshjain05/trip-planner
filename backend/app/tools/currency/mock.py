"""Deterministic mock FX rates -- fixed, roughly realistic table, clearly
not live rates. Good enough for demo budget math; do not use for real money."""
from __future__ import annotations

_RATES_TO_USD = {
    "USD": 1.0, "INR": 1 / 83.0, "EUR": 1.08, "GBP": 1.27,
    "JPY": 1 / 150.0, "AUD": 0.66, "CAD": 0.73, "SGD": 0.74,
}


class MockCurrencyProvider:
    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        f = _RATES_TO_USD.get(from_currency.upper(), 1.0)
        t = _RATES_TO_USD.get(to_currency.upper(), 1.0)
        return f / t

    async def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        rate = await self.get_rate(from_currency, to_currency)
        return round(amount * rate, 2)
