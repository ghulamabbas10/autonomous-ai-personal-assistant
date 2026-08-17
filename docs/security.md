# Security baseline

## Trust boundaries

User instructions are authenticated input. Webpages, documents, emails, tool results, and retrieved memories are untrusted data and can never grant permission or modify system policy. Provider prompts will keep instructions and external content in distinct, labelled fields.

## Action policy

- Low risk: may run when the user has granted the declared permission.
- Medium risk: follows the user's per-tool policy (`always_ask`, `ask_once`, or `auto_approve`).
- High risk: requires a fresh explicit approval unless a deliberately configured, narrowly scoped exception exists.

Approval records bind the user, action fingerprint, sanitized parameters, expiry, and single-use execution. Changing parameters invalidates approval.

## Required controls

- Server-managed, secure, HTTP-only sessions with CSRF protection.
- Argon2id password hashing and rate-limited authentication.
- Tenant/user scoping in every repository query, backed by tests.
- Secrets loaded only by backend processes and redacted from logs.
- Append-only audit records for state transitions, policy decisions, and tool use.
- Schema validation at API, model-provider, and tool boundaries.
- Network and filesystem isolation for code execution; never execute arbitrary code in an API or worker host process.
- Egress allowlists and explicit destination approval for sensitive data.
- Per-user cost, time, iteration, and tool-call budgets.

## Non-goals for Phase 1

This scaffold does not yet implement authentication, encryption, sandboxing, or permissions. It documents mandatory constraints so later implementations and reviews have an explicit acceptance baseline.
