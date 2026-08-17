# Architecture

## Decisions

- **Modular monolith first.** One FastAPI codebase owns the domain, API, worker tasks, and scheduler entry points. This keeps transactions and refactoring simple while packages enforce boundaries. Independently scalable processes can later be extracted without redesigning the domain.
- **PostgreSQL is authoritative.** Projects, tasks, schedules, approvals, memories, agent checkpoints, costs, and audit events are durable database records. Redis never becomes a source of truth.
- **At-least-once jobs.** Celery jobs must be idempotent, use stable execution IDs, and checkpoint progress. Database row locking prevents two workers from advancing the same task concurrently.
- **Provider-neutral AI.** Agents depend on `LLMProvider` capabilities (`generate`, `stream`, `generate_structured`, `embed`), not vendor SDKs. A deterministic mock provider supports local tests.
- **Tools are plugins.** Every tool declares typed input/output schemas, permissions, risk, and approval policy. The runtime selects through a registry rather than tool-specific planner branches.
- **Durable agent state.** Agent and task state transitions are validated and persisted. Runs are bounded by time, iterations, calls, retries, and cost.
- **SSE before WebSockets.** Server-Sent Events are sufficient for one-way activity updates and simpler to operate. WebSockets remain an option for future interactive control.

## Domain boundaries

| Package | Owns | Must not own |
| --- | --- | --- |
| `agents` | orchestration, run state, recovery | HTTP, vendor SDK details |
| `planners` | goal decomposition contracts | task persistence |
| `tools` | discovery and typed execution | approval decisions |
| `memory` | selection, retrieval, retention | conversation transport |
| `scheduler` | schedule calculation and dispatch | agent reasoning |
| `security` | identity, policy, risk, approvals | tool implementation |
| `database` | models, migrations, repositories | business orchestration |
| `services` | transactional use cases | framework-specific views |

Dependencies point inward: API and worker adapters call services; services coordinate domain packages and repositories; infrastructure adapters implement domain protocols.

## Execution lifecycle

`UNDERSTANDING -> PLANNING -> WAITING_APPROVAL? -> EXECUTING -> VERIFYING -> MEMORY_UPDATE -> COMPLETED`

Failures enter `RECOVERY`; a bounded policy may retry or choose another registered tool. Exhaustion produces `BLOCKED` and a user notification. Every transition writes an append-only audit event in the same transaction as the state change.

## Data model scope for Phase 2

The initial migration will introduce users, conversations, messages, projects, goals, tasks, dependencies, tool definitions/executions, permissions, approvals, memories/embeddings, documents, notifications, scheduled jobs, agent runs, audit logs, integrations, and user settings. Credential material will store only an encrypted reference or secret-manager identifier.

## Deployment units

- `frontend`: Next.js web UI
- `api`: FastAPI REST API and SSE stream
- `worker`: Celery task execution
- `scheduler`: Celery beat with a database-backed schedule adapter
- `postgres`: PostgreSQL with pgvector
- `redis`: broker, result backend, rate-limit counters, and short-lived coordination

All units are stateless except PostgreSQL and Redis volumes. Production deployments should use managed equivalents where appropriate, TLS at ingress, a secret manager, and separate worker queues by risk class.
