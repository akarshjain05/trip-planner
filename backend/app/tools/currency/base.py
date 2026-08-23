from __future__ import annotations
from typing import Protocol


class CurrencyProvider(Protocol):
    async def convert(self, amount: float, from_currency: str, to_currency: str) -> float: ...
    async def get_rate(self, from_currency: str, to_currency: str) -> float: ...
