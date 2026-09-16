# Contributing to Itinero

Thanks for your interest in contributing! This project is a portfolio
piece, but pull requests that improve code quality, fix bugs, or add
meaningful features are welcome.

## Getting started

```bash
git clone <this-repo> && cd ai-trip-planner
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Code quality

**Backend:** We use [Ruff](https://docs.astral.sh/ruff/) for linting and
formatting. Run `ruff check .` and `ruff format .` before committing, or
install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

**Frontend:** TypeScript strict mode is enabled. Run `npm run build` to
type-check, and `npm run lint` for linting.

## Running tests

```bash
# Backend (requires Postgres + Redis running)
cd backend && python -m pytest tests/ -v

# Frontend E2E (requires the full stack running)
cd frontend && npx playwright test
```

## Pull request guidelines

- Keep PRs focused — one feature or fix per PR
- Add tests for new functionality
- Update documentation if your change affects the public API or setup
- Run the full test suite before submitting
