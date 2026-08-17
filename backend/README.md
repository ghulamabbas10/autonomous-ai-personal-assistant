# Backend

Python 3.12 FastAPI modular monolith with async SQLAlchemy, PostgreSQL/pgvector, and Alembic.

## Host development

From this directory:

```text
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload
.venv/Scripts/pytest
```

Set `DATABASE_URL` to a host-reachable PostgreSQL URL first. API documentation is available at `/api/docs` outside production. Liveness is `/api/v1/health/live`; readiness additionally checks PostgreSQL at `/api/v1/health/ready`.

## Containers

From the repository root, create `.env`, then run:

```text
docker compose --profile backend up --build
```

The one-shot `migrate` service must complete before the API starts.

Package boundaries are documented in `docs/architecture.md`. Authentication is intentionally deferred to Phase 3.
