# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI REST API that manages projects and extracts deliverables from email threads using Anthropic AI. Deployed on Google App Engine, with PostgreSQL for storage and Google Cloud Secret Manager for secrets.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn main:app --reload

# Run all tests
pytest -v

# Run tests by marker
pytest -m user -v
pytest -m project -v
pytest -m cost -v

# Run a single test file
pytest tests/api/test_user_router.py -v
```

## Architecture

**Layered structure per module** in `src/project_context/`:
- `router.py` — FastAPI route definitions
- `service.py` — Business logic and database operations
- `models.py` — Data structures
- `schemas.py` — Pydantic request/response validation

**Key modules:** `auth/`, `user/`, `projects/`, `costs/`, `ai/`, `anthropic/`, `gmail/`, `postgres/`, `gcloud_secrets/`

**API base path:** `/api/v1/` with X-API-Key header authentication.

**Database:** PostgreSQL via `psycopg` async driver with connection pooling (`AsyncConnectionPool`). Raw SQL queries, no ORM.

**AI pipeline:** Gmail messages → Anthropic API analysis → deliverable extraction. Prompt templates live in `ai/prompts/`. Every API call is cost-tracked.

## Testing

- pytest with `pytest-asyncio` (async mode: auto)
- Tests use a real PostgreSQL database (Supabase) with per-test rollback
- Fixtures in `tests/conftest.py` provide `db_conn`, `client`, `create_user`, `create_project`
- The `app` fixture overrides `get_db_conn` dependency and stubs `commit()` to prevent writes
- Integration tests use `httpx.AsyncClient` with ASGITransport

## Deployment

Google App Engine Standard (Python 3.12) configured in `app.yaml`. Entry point: `uvicorn main:app --host 0.0.0.0 --port $PORT`. Auto-scales 0-1 instances.

## Key Details

- Python 3.13+ required
- Secrets come from Google Cloud Secret Manager in production, `.env` locally
- Auth uses Fernet encryption for API key validation
- Production error responses are masked (404/500) when no valid API key is present
- FastAPI lifespan manages PostgreSQL connection pool init/teardown
- `main.py` at repo root re-exports the app from `src/project_context/main.py`
