"""
Central application configuration.

Everything that varies between environments (dev / test / docker / prod)
lives here and is sourced from environment variables / .env, never
hard-coded. See backend/.env.example for the full list with comments.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    BACKGROUND_EXECUTOR: str = "fastapi"

    APP_NAME: str = "AI Trip Planner"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # Backend listens on this port locally (docker-compose maps host->container
    # via BACKEND_PORT so it won't collide with other projects on your machine).
    BACKEND_PORT: int = 8000

    # --- Security ---
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5183"]

    # --- Database ---
    # Async URL used by the app; a derived sync URL is used by Alembic.
    DATABASE_URL: str = (
        "postgresql+asyncpg://trip_planner:trip_planner_dev@localhost:5432/trip_planner"
    )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    # --- Redis (cache + pub/sub progress bus + background-task queue) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_ALWAYS_EAGER: bool = False


    # --- Demo / mock mode ---
    # When true (or when no provider API key is configured), the app runs
    # entirely on deterministic mock data: no travel API keys and no LLM
    # API key are required to see the full agentic workflow run end to end.
    DEMO_MODE: bool = True

    # --- LLM provider abstraction ---
    LLM_PROVIDER: Literal["openai", "anthropic", "google", "openrouter", "mock", "nvidia", "groq"] = "mock"
    LLM_MODEL: str = "gpt-4o"
    LLM_MODEL_CHEAP: str | None = None
    LLM_TEMPERATURE: float = 0.3

    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # --- Multi-provider LLM pool ---
    LLM_PROVIDER_CHAIN: list[str] = Field(default_factory=list)

    LLM_MODEL_GOOGLE: str | None = None
    LLM_MODEL_OPENROUTER: str | None = None
    LLM_MODEL_NVIDIA: str | None = None
    LLM_MODEL_OPENAI: str | None = None
    LLM_MODEL_ANTHROPIC: str | None = None
    LLM_MODEL_GROQ: str | None = None
    
    LLM_MODEL_CHEAP_GOOGLE: str | None = None
    LLM_MODEL_CHEAP_OPENROUTER: str | None = None
    LLM_MODEL_CHEAP_NVIDIA: str | None = None
    LLM_MODEL_CHEAP_OPENAI: str | None = None
    LLM_MODEL_CHEAP_ANTHROPIC: str | None = None
    LLM_MODEL_CHEAP_GROQ: str | None = None

    LLM_DAILY_CAP_GOOGLE: int | None = None
    LLM_DAILY_CAP_OPENROUTER: int | None = None
    LLM_DAILY_CAP_NVIDIA: int | None = None
    LLM_DAILY_CAP_OPENAI: int | None = None
    LLM_DAILY_CAP_ANTHROPIC: int | None = None
    LLM_DAILY_CAP_GROQ: int | None = None

    @property
    def llm_provider_chain(self) -> list[str]:
        chain = self.LLM_PROVIDER_CHAIN or [self.LLM_PROVIDER]
        return [p for p in chain if p in self.configured_providers]

    @property
    def configured_providers(self) -> set[str]:
        return {p for p, has_key in {
            "openai": bool(self.OPENAI_API_KEY),
            "anthropic": bool(self.ANTHROPIC_API_KEY),
            "google": bool(self.GOOGLE_API_KEY),
            "openrouter": bool(self.OPENROUTER_API_KEY),
            "nvidia": bool(self.NVIDIA_API_KEY),
            "groq": bool(self.GROQ_API_KEY),
        }.items() if has_key}

    def model_for_provider(self, provider: str, cheap: bool = False) -> str:
        if cheap:
            val = getattr(self, f"LLM_MODEL_CHEAP_{provider.upper()}", None)
            if val:
                return val
            if self.LLM_MODEL_CHEAP:
                return self.LLM_MODEL_CHEAP
        val = getattr(self, f"LLM_MODEL_{provider.upper()}", None)
        return val or self.LLM_MODEL

    @property
    def llm_daily_caps(self) -> dict[str, int]:
        caps = {}
        for p in ("google", "openrouter", "nvidia", "openai", "anthropic", "groq"):
            v = getattr(self, f"LLM_DAILY_CAP_{p.upper()}", None)
            if v is not None:
                caps[p] = v
        return caps

    # --- Travel data providers (mock-by-default; real adapters are opt-in) ---
    FLIGHTS_PROVIDER: str = "mock"
    HOTELS_PROVIDER: str = "mock"
    PLACES_PROVIDER: str = "mock"
    FOOD_PROVIDER: str = "mock"
    WEATHER_PROVIDER: str = "mock"
    CURRENCY_PROVIDER: str = "mock"
    WEB_SEARCH_PROVIDER: str = "mock"
    GEOAPIFY_API_KEY: str | None = None


    AMADEUS_API_KEY: str | None = None
    AMADEUS_API_SECRET: str | None = None
    GOOGLE_PLACES_API_KEY: str | None = None
    FOURSQUARE_API_KEY: str | None = None
    OPENWEATHER_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    RAPIDAPI_KEY: str | None = None
    SERPAPI_KEY: str | None = None

    # --- Agent cost / safety controls ---
    MAX_AGENT_ITERATIONS: int = 3
    MAX_TOOL_CALLS: int = 40
    MAX_LLM_COST_USD: float = 2.00
    MAX_TRIP_PLANNING_TIME_SECONDS: int = 600

    # --- Cache TTLs (seconds) ---
    CACHE_TTL_WEATHER: int = 3600
    CACHE_TTL_CURRENCY: int = 3600
    CACHE_TTL_PLACES: int = 86400
    CACHE_TTL_FLIGHTS: int = 86400
    CACHE_TTL_HOTELS: int = 86400
    CACHE_TTL_LLM: int = 3600

    @property
    def llm_key_configured(self) -> bool:
        """Whether the selected provider actually has credentials available."""
        return {
            "openai": bool(self.OPENAI_API_KEY),
            "anthropic": bool(self.ANTHROPIC_API_KEY),
            "google": bool(self.GOOGLE_API_KEY),
            "openrouter": bool(self.OPENROUTER_API_KEY),
            "nvidia": bool(self.NVIDIA_API_KEY),
            "groq": bool(self.GROQ_API_KEY),
            "mock": True,
        }.get(self.LLM_PROVIDER, False)

    @property
    def use_mock_llm(self) -> bool:
        return self.DEMO_MODE or self.LLM_PROVIDER == "mock" or not self.llm_key_configured


@lru_cache
def get_settings() -> Settings:
    return Settings()
