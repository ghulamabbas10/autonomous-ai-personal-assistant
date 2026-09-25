# Autonomous AI Personal Assistant

A production-oriented monorepo for an autonomous personal AI employee: it turns goals into durable projects and tasks, executes approved work in background workers, remembers useful context, and reports what it accomplished.

## Current status

Phases 1–4 are complete: repository architecture, the FastAPI/database foundation, secure database-backed authentication, and the responsive Next.js chat interface.

## Architecture

```text
Browser -> Next.js web app -> FastAPI API -> PostgreSQL + pgvector
                              |          -> Redis
                              +-> Celery workers -> tools / LLM providers
                              +-> Celery beat    -> durable scheduled jobs
```

The API owns domain rules and authorization. Workers perform bounded agent runs. PostgreSQL is the source of truth; Redis is transport and ephemeral coordination only. External content is always treated as untrusted tool output. See [docs/architecture.md](docs/architecture.md) and [docs/security.md](docs/security.md).

## Repository layout

```text
frontend/                 Next.js application (Phase 4 onward)
backend/                  FastAPI application and worker packages
  app/api/                HTTP and live-activity interfaces
  app/agents/             agent runtime and state machine
  app/planners/           provider-neutral planning
  app/tools/              tool contracts and registry
  app/memory/             memory selection and retrieval
  app/scheduler/          durable scheduling
  app/workers/            asynchronous jobs
  app/security/           auth, permissions, approvals, safety
  app/database/           models, repositories, migrations
  app/services/           application use cases
infrastructure/docker/    container definitions
tests/                    cross-service integration and E2E tests
docs/                     architecture and engineering decisions
```

## Prerequisites

- Docker Desktop with Docker Compose v2
- For host development later: Python 3.12+, Node.js 22+, and pnpm 10+

## Local setup

1. Copy `.env.example` to `.env` and replace development secrets.
2. Start infrastructure with `docker compose up -d postgres redis`.
3. Check it with `docker compose ps`.

PostgreSQL is available on `localhost:5432`; Redis is available on `localhost:6379`. After creating `.env`, start the Phase 2 API with `docker compose --profile backend up --build`.

Stop local services with `docker compose down`. Add `-v` only when you deliberately want to erase local database and Redis data.

## Configuration

`.env.example` is the configuration contract. Secrets belong in a local `.env` or a production secret manager and must never be exposed through frontend environment variables. `LLM_PROVIDER=mock` allows development without external credentials.

## Delivery roadmap

1. Repository architecture (complete)
2. Database and backend foundation (complete)
3. Authentication and sessions (complete)
4. Chat interface (complete)
5. Agent runtime and provider abstraction
6. Planner and task engine
7. Background workers
8. Scheduler
9. Memory and pgvector retrieval
10. Tool registry, web research, and file tools
11. Permissions and approval queue
12. Dashboard and live activity
13. Notifications and morning briefing
14. Unit, integration, and E2E coverage
15. Production deployment documentation

Each phase must include focused tests and documentation before the next phase begins.

## License

No license has been selected yet.
