"""Real web-search adapter interface for Tavily (LLM-oriented search API).
NOT exercised in this session -- no network egress to api.tavily.com and no
key provided. Set TAVILY_API_KEY and WEB_SEARCH_PROVIDER=tavily to use."""
from __future__ import annotations
import httpx
from app.core.config import Settings
from app.tools.base import ProviderError

_SEARCH_URL = "https://api.tavily.com/search"


class TavilyWebSearchProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        if not self._settings.TAVILY_API_KEY:
            raise ProviderError("tavily", "TAVILY_API_KEY not configured", retriable=False)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(_SEARCH_URL, json={
                "api_key": self._settings.TAVILY_API_KEY, "query": query,
                "max_results": max_results, "include_answer": False,
            })
        if resp.status_code != 200:
            raise ProviderError("tavily", f"search failed: {resp.text}", retriable=resp.status_code >= 500)
        results = resp.json().get("results", [])
        return [
            {"url": r["url"], "title": r.get("title"), "source": "tavily",
             "extracted_facts": r.get("content", "")[:500], "confidence": r.get("score", 0.5)}
            for r in results
        ]
