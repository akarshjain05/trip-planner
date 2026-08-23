from __future__ import annotations
from typing import Protocol


class WebSearchProvider(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[dict]: ...
