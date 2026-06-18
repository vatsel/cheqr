# Cheqr

Cheqr reads Gmail threads and extracts what's been promised vs delivered, so that project managers can track commitments without combing through email by hand.

Built as a FastAPI server it ingests email threads to turn them into structured deliverables using the Anthropic API, backed by PostgreSQL and deployed on Google App Engine.

## Product Page 
https://cheqr.vatsel.com
(can't install yet)

## How it works

```
Gmail thread → prompt template → Anthropic API → structured deliverables → PostgreSQL
```

1. A Gmail thread is posted to the API.
2. The relevant messages are assembled and sent to the Anthropic API using a versioned prompt template (`ai/prompts/`).
3. The model's analysis is parsed into structured deliverables (title + specification) and persisted.
4. Every model call is cost-tracked, so token spend stays observable per project rather than being a black box.

## Architecture

A layered, module-per-domain structure under `src/project_context/`. Each domain follows the same four-file pattern:

| File | Responsibility |
| --- | --- |
| `router.py` | FastAPI route definitions |
| `service.py` | Business logic and database access |
| `schemas.py` | Pydantic request/response validation |
| `models.py` | Internal data structures |

Domains: `auth`, `user`, `projects`, `costs`, `ai`, `anthropic`, `gmail`, `postgres`, `gcloud_secrets`.

- **API** — versioned under `/api/v1/`, authenticated with an `X-API-Key` header.
- **Database** — PostgreSQL through the async `psycopg` driver with a connection pool (`AsyncConnectionPool`). Raw SQL, no ORM. The pool is initialised and torn down via the FastAPI lifespan.
- **Secrets** — Google Cloud Secret Manager in production, an untracked `.env` locally.

## Security

- API keys are validated with Fernet encryption.
- Production error responses are masked (404 / 500) when no valid API key is present, so the API surface can't be enumerated by unauthenticated callers.
- No secrets live in the repo — configuration comes from Secret Manager in production and an untracked `.env` in development.

## Testing

```bash
pytest -v                              # full suite
pytest -m user -v                      # by domain marker: user | project | cost
pytest tests/api/test_user_router.py -v
```

- `pytest` with `pytest-asyncio` (auto async mode).
- Integration tests run against a **real PostgreSQL database with per-test rollback**, so they exercise real SQL without leaking state between tests.
- The `app` fixture overrides the `get_db_conn` dependency and stubs `commit()`, guaranteeing tests never write.
- Endpoints are driven end to end through `httpx.AsyncClient` over `ASGITransport`.
- Shared fixtures (`db_conn`, `client`, `create_user`, `create_project`) live in `tests/conftest.py`.

## Running locally

```bash
# Python 3.12+
pip install -r requirements.txt

# create a local .env with the required secrets
# (Anthropic API key, database URL, etc.)

uvicorn main:app --reload
```

## Deployment

Google App Engine Standard (Python 3.12), configured in `app.yaml`, auto-scaling 0–1 instances. Entry point: `uvicorn main:app --host 0.0.0.0 --port $PORT`.

## Project layout

```
src/project_context/   # application code, one folder per domain
tests/                 # pytest suite (api/ integration tests, conftest fixtures)
main.py                # re-exports the app from src/project_context/main.py
app.yaml               # App Engine config
pyproject.toml
requirements.txt
```

## Stack

FastAPI · Python 3.12 · PostgreSQL (async `psycopg`) · Anthropic API · Google App Engine · Google Cloud Secret Manager


## Not included
- The Gmail client (which is an Appscript)
