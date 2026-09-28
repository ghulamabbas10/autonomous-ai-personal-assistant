# Backend

Python 3.12 FastAPI modular monolith with async SQLAlchemy, PostgreSQL/pgvector, and Alembic.

Phase 3 adds durable opaque sessions, Argon2id password hashing, CSRF protection, Redis-backed authentication throttling, and authentication audit events. Raw session and CSRF tokens are never stored in PostgreSQL.

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

Package boundaries are documented in `docs/architecture.md`.

## Authentication API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout` with the `X-CSRF-Token` header

Registration and login return the CSRF token and set the opaque HTTP-only session cookie. Production and staging environments additionally mark authentication cookies as `Secure`.
## AI providers

`LLM_PROVIDER=mock` is the default and makes deterministic responses without network access or cost. For a real free local model, run Ollama and configure:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:3b
LLM_BASE_URL=http://ollama:11434
```

Then start the `ollama` Compose profile and pull the model:

```bash
docker compose --profile frontend --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:3b
docker compose --profile frontend up -d --force-recreate api
```

The provider contract supports normal generation, streaming, schema-constrained generation, and embeddings. Chat requests are persisted through `POST /api/v1/chat`; conversation reads are user-scoped.
