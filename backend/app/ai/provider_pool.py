"""
Multi-provider LLM pool with rate-limit-aware fallback.

Tries each configured provider in order (LLM_PROVIDER_CHAIN). On a 429 /
quota error, marks that provider on cooldown for the rest of the day and
moves to the next one -- this is what actually lets you "combine"
providers instead of hand-switching LLM_PROVIDER every time one runs dry.

State lives in Redis (same store as app/tools/cache.py) so cooldowns and
the rolling daily-request counters survive process restarts and are
shared across every worker, not just the process that hit the limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from app.ai.factory import build_chat_model
from app.core.config import Settings
from app.core.logging import get_logger
from app.tools.cache import get_redis

T = TypeVar("T", bound=BaseModel)
logger = get_logger("provider_pool")

_RATE_LIMIT_MARKERS = ("429", "rate_limit", "rate limit", "resource_exhausted", "quota")
_TRANSIENT_MARKERS = ("503", "502", "500", "timeout", "connection", "404")


def _is_rate_limited(err: Exception) -> bool:
    s = str(err).lower()
    return any(m in s for m in _RATE_LIMIT_MARKERS)


def _is_transient(err: Exception) -> bool:
    s = str(err).lower()
    return any(m in s for m in _TRANSIENT_MARKERS)


@dataclass
class ProviderAttempt:
    provider: str
    model: str
    error: str | None = None
    used: bool = False


class ProviderExhaustedError(Exception):
    """Every provider in the chain was on cooldown, over its daily cap, or failed."""
    def __init__(self, attempts: list[ProviderAttempt]):
        self.attempts = attempts
        summary = "; ".join(f"{a.provider}: {a.error or 'ok'}" for a in attempts)
        super().__init__(f"All LLM providers exhausted -- {summary}")


class ProviderPool:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._chain = settings.llm_provider_chain
        if not self._chain:
            raise ValueError(
                "LLM_PROVIDER_CHAIN (or LLM_PROVIDER) resolved to no configured "
                "provider -- check that at least one *_API_KEY is set."
            )
        self._models: dict[str, object] = {}

    def _model_for(self, provider: str, cheap: bool = False):
        key = f"{provider}_cheap" if cheap else provider
        if key not in self._models:
            self._models[key] = build_chat_model(
                self.settings, provider=provider, model=self.settings.model_for_provider(provider, cheap=cheap), cheap=cheap
            )
        return self._models[key]

    def _cooldown_key(self, provider: str) -> str:
        return f"trip_planner:llm_cooldown:{provider}"

    def _count_key(self, provider: str) -> str:
        return f"trip_planner:llm_daily_count:{provider}"

    async def _on_cooldown(self, provider: str) -> bool:
        try:
            return bool(await get_redis().get(self._cooldown_key(provider)))
        except Exception:
            return False  # Redis down -- fail open rather than block every provider

    async def _set_cooldown(self, provider: str, seconds: int) -> None:
        try:
            await get_redis().set(self._cooldown_key(provider), "1", ex=seconds)
        except Exception:
            pass

    async def _daily_count(self, provider: str) -> int:
        try:
            raw = await get_redis().get(self._count_key(provider))
            return int(raw) if raw else 0
        except Exception:
            return 0

    async def _bump_daily_count(self, provider: str) -> None:
        try:
            r = get_redis()
            key = self._count_key(provider)
            if await r.incr(key) == 1:
                await r.expire(key, 24 * 3600)  # rolling 24h, not aligned to provider's own reset clock
        except Exception:
            pass

    async def ainvoke_structured(self, schema_cls: type[T], messages: list[BaseMessage], cheap: bool = False):
        """Returns (parsed_value, raw_response, provider_used, model_used)."""
        import asyncio
        attempts: list[ProviderAttempt] = []
        caps = self.settings.llm_daily_caps

        for provider in self._chain:
            model_name = self.settings.model_for_provider(provider, cheap=cheap)

            if await self._on_cooldown(provider):
                attempts.append(ProviderAttempt(provider, model_name, error="on cooldown"))
                continue

            cap = caps.get(provider)
            if cap is not None and await self._daily_count(provider) >= cap:
                attempts.append(ProviderAttempt(provider, model_name, error=f"daily cap ({cap}) reached"))
                continue

            try:
                if provider == "nvidia":
                    import json
                    import asyncio
                    from openai import AsyncOpenAI
                    from langchain_core.messages import SystemMessage, HumanMessage
                    
                    sys_msg = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
                    hum_msg = next((m.content for m in messages if isinstance(m, HumanMessage)), "")
                    
                    client = AsyncOpenAI(
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=self.settings.NVIDIA_API_KEY,
                        timeout=60.0
                    )
                    
                    schema_str = json.dumps(schema_cls.model_json_schema())
                    
                    max_retries = 2
                    parsed = None
                    for attempt in range(max_retries):
                        try:
                            completion = await client.chat.completions.create(
                                model=model_name,
                                messages=[
                                    {"role": "system", "content": sys_msg},
                                    {"role": "user", "content": hum_msg + f"\n\nIMPORTANT: Return ONLY valid JSON matching this schema:\n{schema_str}"}
                                ],
                                response_format={"type": "json_object"},
                                stream=True,
                                extra_body={"chat_template_kwargs": {"enable_thinking": not cheap}}
                            )
                            
                            full_content = ""
                            async for chunk in completion:
                                if not chunk.choices: continue
                                delta = chunk.choices[0].delta
                                if delta.content:
                                    full_content += delta.content
                            
                            import re
                            json_str = full_content.strip()
                            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
                            if match:
                                json_str = match.group(1)
                                    
                            parsed = schema_cls.model_validate_json(json_str)
                            break
                        except Exception as e:
                            logger.error(f"NVIDIA API failed attempt {attempt}: {e}\nContent: {full_content[:200]}")
                            if attempt == max_retries - 1:
                                raise
                            await asyncio.sleep(2 * (attempt + 1))
                            
                    class MockRaw:
                        usage_metadata = {"input_tokens": 0, "output_tokens": 0}
                    
                    await self._bump_daily_count(provider)
                    return parsed, MockRaw(), provider, model_name

                chat_model = self._model_for(provider, cheap=cheap)
                structured = chat_model.with_structured_output(schema_cls, include_raw=True)
                
                # Retry loop inside the provider pool for non-NVIDIA providers
                max_retries = 2
                result = None
                for attempt in range(max_retries):
                    try:
                        result = await structured.ainvoke(messages)
                        break
                    except Exception as e:
                        if "400" in str(e) and "tool calling" in str(e).lower():
                            raise # Fast fail on unsupported schema so we fall back provider
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(2 * (attempt + 1))
                        
                parsed = result.get("parsed")
                if parsed is None:
                    raise ValueError(f"parsing_error: {result.get('parsing_error')}")

                await self._bump_daily_count(provider)
                attempts.append(ProviderAttempt(provider, model_name, used=True))
                logger.info("llm_call", provider=provider, model=model_name, schema=schema_cls.__name__)
                return parsed, result["raw"], provider, model_name

            except Exception as e:
                attempts.append(ProviderAttempt(provider, model_name, error=str(e)[:200]))
                if _is_rate_limited(e):
                    await self._set_cooldown(provider, 24 * 3600)   # confirmed exhausted -- skip all day
                elif _is_transient(e) or "400" in str(e):
                    await self._set_cooldown(provider, 60)          # probably a blip or missing model
                else:
                    await self._set_cooldown(provider, 300)         # real error -- don't hammer it
                continue

        raise ProviderExhaustedError(attempts)
