from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agent_runs, auth, planning, trips, users
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


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Agentic AI Trip Planner -- a LangGraph-orchestrated multi-agent "
        "travel planning system. See /docs for the interactive OpenAPI UI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "demo_mode": settings.DEMO_MODE, "using_mock_llm": settings.use_mock_llm}


app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(trips.router, prefix=settings.API_PREFIX)
app.include_router(planning.router, prefix=settings.API_PREFIX)
app.include_router(agent_runs.router, prefix=settings.API_PREFIX)
