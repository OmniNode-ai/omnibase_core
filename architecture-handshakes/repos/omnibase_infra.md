# OmniNode Architecture – Constraint Map (omnibase_infra)

> **Role**: Infrastructure layer – concrete implementations, Kafka, Postgres
> **Handshake Version**: 0.1.0

## Core Principles

- Declarative nodes, imperative handlers
- All behavior contract-defined
- Container-based dependency injection
- Unidirectional data flow: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR

## This Repo Contains

- Concrete node implementations
- Kafka/Postgres integrations
- Handler implementations
- Infrastructure adapters

## Platform-Wide Rules

1. **No backwards compatibility** - Breaking changes always acceptable. No deprecation periods, shims, or migration paths.
2. **Delete old code immediately** - Never leave deprecated code "for reference." If unused, delete it.
3. **No speculative refactors** - Only make changes that are directly requested or clearly necessary.
4. **No silent schema changes** - All schema changes must be explicit and deliberate.
5. **Frozen event schemas** - All models crossing boundaries (events, intents, actions, envelopes, projections) must use `frozen=True`. Internal mutable state is fine.
6. **Explicit timestamps** - Never use `datetime.now()` defaults. Inject timestamps explicitly.
7. **No hardcoded configuration** - All config via `.env` or Pydantic Settings. No localhost defaults.
8. **Kafka is required infrastructure** - Use async/non-blocking patterns. Never block the calling thread waiting for Kafka acks.
9. **No `# type: ignore` without justification** - Requires explanation comment and ticket reference.

## Rules the Agent Must Obey

1. **Nodes MUST be declarative** - `node.py` extends base class with NO custom logic
2. **Handlers own ALL business logic** - Nodes are thin coordination shells
3. **Reducers are pure** - No I/O in reducer handlers
4. **Orchestrators emit, never return** - Cannot return `result`
5. **Contracts are source of truth** - YAML contracts define behavior
6. **Container injection required** - All services via `ModelONEXContainer`

## Non-Goals (DO NOT)

- ❌ No versioned directories (`v1_0_0/`, `v2/`) - version through contract.yaml fields only
- ❌ No convenience over correctness - contract violations fail loudly
- ❌ No business logic in nodes - nodes coordinate, handlers compute
- ❌ No implicit state - all state transitions explicit and auditable

## Patterns to Avoid

- Custom logic in `node.py` beyond base class extension
- Error handling in nodes (belongs in handlers)
- Direct Kafka/Postgres calls in nodes (use effect handlers)

## Layer Boundaries

```
omnibase_core (contracts, models)
    ↑ imported by
omnibase_spi (protocols)
    ↑ imported by
omnibase_infra (YOU ARE HERE)
```

**Infra → Core**: allowed (imports models)
**Infra → SPI**: allowed (implements protocols)
