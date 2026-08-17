# ADR 0001: Start with a modular monolith

- Status: accepted
- Date: 2026-08-17

## Context

The product needs independently running API, worker, and scheduler processes, but its early domain model will change quickly. Splitting business capabilities into networked services now would add distributed transactions and operational overhead without a demonstrated scaling need.

## Decision

Use one typed Python package with explicit domain modules and multiple process entry points. Share PostgreSQL models and application services while preventing framework and vendor dependencies from leaking into core protocols.

## Consequences

Development and transactional consistency stay simple. Workers can scale separately at the process/container level. A module may later become a service after its contract and scaling profile are stable.
