"""Shared provider-abstraction primitives used by every tools/<category>/ package."""
from __future__ import annotations


class ProviderError(Exception):
    """Normalized error every adapter raises instead of leaking SDK-specific
    exceptions up into agent nodes. Nodes only ever need to catch this one
    type to trigger their retry/fallback logic."""

    def __init__(self, provider: str, message: str, retriable: bool = False):
        self.provider = provider
        self.retriable = retriable
        super().__init__(f"[{provider}] {message}")
