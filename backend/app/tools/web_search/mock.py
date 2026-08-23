"""Deterministic mock web-research results with full source provenance
(url/title/source/extracted_facts/confidence) -- exercises the research
citation path (section 9 of the spec) without a live search API."""
from __future__ import annotations


class MockWebSearchProvider:
    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        slug = query.lower().replace(" ", "-")[:40]
        return [
            {
                "url": f"https://example-travel-guide.demo/{slug}-{i}",
                "title": f"Demo travel guide result for '{query}' #{i + 1}",
                "source": "demo_web_search",
                "extracted_facts": f"Simulated research snippet about '{query}' (demo data, not a live web result).",
                "confidence": 0.4,
            }
            for i in range(min(max_results, 3))
        ]
