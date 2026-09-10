"""
Provider-agnostic chat-model factory.

This is the ONE place that knows about OpenAI/Anthropic/Google/OpenRouter
SDK wiring. Swapping the model used across the entire application is a
single .env change (LLM_PROVIDER, LLM_MODEL) -- nothing in app/agents/
imports a provider SDK directly.
"""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Construct the configured real LLM. Raises if misconfigured -- callers
    should check settings.use_mock_llm first and avoid calling this at all
    in demo mode."""
    provider = settings.LLM_PROVIDER

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.ANTHROPIC_API_KEY,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            google_api_key=settings.GOOGLE_API_KEY,
        )

    if provider == "openrouter":
        # OpenRouter speaks the OpenAI wire protocol at a different base_url.
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            max_tokens=60000,
        )

    
    if provider == "nvidia":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
        )

    raise ValueError(f"Unknown or unsupported LLM_PROVIDER: {provider!r}")
