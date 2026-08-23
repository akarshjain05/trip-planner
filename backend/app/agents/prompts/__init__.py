"""Loads prompt templates from this directory as plain text.

Keeping prompts as standalone .txt files (rather than inline Python
strings) is what makes them independently versionable/diffable and
editable by a non-engineer without touching node logic.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found at {path}")
    return path.read_text(encoding="utf-8").strip()
