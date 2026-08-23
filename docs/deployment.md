# Deployment

## Docker Compose (as shipped)

```bash
docker compose up --build -d
```

Four services: `postgres`, `redis`, `backend` (runs `alembic upgrade head`
on startup, then `uvicorn`), `frontend` (built and served by nginx). All
have healthchecks; `backend` waits for `postgres`/`redis` to report
healthy before starting.

This compose file is written and YAML-validated but has not been run
end-to-end in the environment this project was built in (no
Docker-in-Docker, no Docker Hub egress available there) — the pieces it
wraps (backend boot, migrations, tests, frontend build) are each verified
independently; see the root README's "what's real" section.

## Production notes

- Set real values for `SECRET_KEY`, database credentials, and `CORS_ORIGINS`.
- Put a reverse proxy (nginx, Caddy, or a managed load balancer) in front
  with TLS termination; this build doesn't terminate TLS itself.
- The `backend` Dockerfile's `HEALTHCHECK` hits `/health` — wire your
  orchestrator's readiness/liveness probes to the same endpoint.
- `frontend`'s nginx config falls back to `index.html` for any unknown
  path (`try_files ... /index.html`), required for React Router's
  client-side routes to work on a hard refresh/direct link.
- Migrations run automatically on backend container start
  (`alembic upgrade head && uvicorn ...`). For a multi-replica deployment,
  run migrations as a separate one-off job instead of letting every
  replica race to apply them.
- Swap the asyncio-background-task planning execution for real Celery
  workers if you need to scale planning throughput independently of the
  API process — see `docs/architecture.md#background-execution` for the
  seam.

## Environment-specific config

Everything that varies by environment is a `.env` variable — see
`docs/environment-variables.md`. Nothing environment-specific is
hardcoded in application code.
