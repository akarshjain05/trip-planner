from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import oauth
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import admin, agent_runs, auth, planning, trips, users
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup", demo_mode=settings.DEMO_MODE, llm_provider=settings.LLM_PROVIDER,
        using_mock_llm=settings.use_mock_llm,
    )
    yield
    logger.info("shutdown")


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Agentic Itinero -- a LangGraph-orchestrated multi-agent "
        "travel planning system. See /docs for the interactive OpenAPI UI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY or "dev_secret")
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    resource = Resource.create({"service.name": "ai-trip-planner"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')}/v1/traces"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from app.tools.cache import get_redis

@app.get("/health")
async def health() -> dict:
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
        
    redis_ok = False
    try:
        r = get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    if not db_ok or not redis_ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "error", "db": db_ok, "redis": redis_ok})

    return {"status": "ok", "db": "ok", "redis": "ok", "demo_mode": settings.DEMO_MODE, "using_mock_llm": settings.use_mock_llm}


app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(trips.router, prefix=settings.API_PREFIX)
app.include_router(planning.router, prefix=settings.API_PREFIX)
app.include_router(agent_runs.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)
app.include_router(oauth.router, prefix=settings.API_PREFIX)
