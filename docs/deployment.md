# Deployment

## Docker Compose (as shipped)

```bash
docker compose up --build -d
```

This spins up seven services:
- `postgres`: Relational database for trips, users, and state.
- `redis`: Message broker for Celery and caching.
- `backend`: FastAPI server (runs `alembic upgrade head` on startup).
- `worker`: Celery worker that executes the LangGraph agent pipelines.
- `frontend`: React app built and served statically by NGINX.
- `flower`: Celery monitoring dashboard (`http://localhost:5555`).
- `jaeger`: OpenTelemetry distributed tracing dashboard (`http://localhost:16686`).

All services have healthchecks; `backend` and `worker` wait for `postgres` and `redis` to report healthy before starting.

## Production notes

- Set real values for `SECRET_KEY`, database credentials, and `CORS_ORIGINS`.
- Put a reverse proxy (NGINX, Caddy, or a managed load balancer) in front with TLS termination.
- The `backend` Dockerfile's `HEALTHCHECK` hits `/health` — wire your orchestrator's probes to the same endpoint.
- The `frontend` NGINX config is already configured for React Router (`try_files $uri $uri/ /index.html`).
- Migrations run automatically on the `backend` container start. For a multi-replica deployment (like Kubernetes), run migrations as a separate `Job` instead of letting every replica race to apply them.

## Environment-specific config

Everything that varies by environment is a `.env` variable — see `docs/environment-variables.md`. Nothing environment-specific is hardcoded in application code.
