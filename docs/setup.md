# Local setup

## Fastest path: Docker Compose

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

Frontend at `:5173`, backend at `:8000` (OpenAPI docs at `:8000/docs`),
Postgres at `:5432`, Redis at `:6379`. Nothing needs a key —
`DEMO_MODE=true` by default.

## Without Docker

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: point DATABASE_URL / REDIS_URL at a Postgres/Redis you have
# running locally (see below if you don't have them installed)

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

If you don't already have Postgres/Redis running locally:

```bash
# Debian/Ubuntu
sudo apt-get install postgresql redis-server
sudo service postgresql start
sudo service redis-server start
sudo -u postgres psql -c "CREATE USER trip_planner WITH PASSWORD 'trip_planner_dev' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE trip_planner OWNER trip_planner;"
```

(macOS: `brew install postgresql redis && brew services start postgresql redis`)

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL if your backend isn't on :8000
npm run dev
```

### Running tests

```bash
cd backend
# tests run against a real Postgres DB named trip_planner_test —
# create it once:
sudo -u postgres psql -c "CREATE DATABASE trip_planner_test OWNER trip_planner;"
python -m pytest tests/ -v
```

## Port collisions

If you run several local projects side by side, every port here is
overridable via `.env` — nothing is hardcoded:

| Variable | Default | Used by |
|---|---|---|
| `BACKEND_PORT` | 8000 | backend (`backend/.env`) |
| `POSTGRES_PORT` | 5432 | `docker-compose.yml` |
| `REDIS_PORT` | 6379 | `docker-compose.yml` |
| `FRONTEND_PORT` | 5173 | `docker-compose.yml` |

For the non-Docker path, change `DATABASE_URL`/`REDIS_URL` in
`backend/.env` to whatever host/port you're actually running on, and
`VITE_API_BASE_URL` in `frontend/.env` to match your backend's port.

## Enabling a real LLM

1. Set `DEMO_MODE=false` in `backend/.env`.
2. Set `LLM_PROVIDER` to `openai`, `anthropic`, `google`, or `openrouter`.
3. Set the matching `*_API_KEY`.
4. Optionally set `LLM_MODEL` to a specific model name for that provider.

Everything else (travel-data providers) stays on mock data unless you
also flip those individually — see `docs/providers.md`.
