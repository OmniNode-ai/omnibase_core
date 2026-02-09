# OmniNode Architecture – Constraint Map (omnibase_core)

> **Role**: Foundation layer – contracts, models, invariants, enums
> **Handshake Version**: 0.1.0

## Core Principles

- Contract-driven execution
- Explicit schemas before behavior
- Deterministic, replayable workflows
- No hidden side effects

## This Repo Contains

- Pydantic models and contracts
- Enums and type definitions
- Protocols (interfaces)
- Validators and invariants
- Base node classes (NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator)

## Rules the Agent Must Obey

1. **Never introduce new behavior without a contract** - YAML contracts define behavior, not code
2. **Never bypass the registry or container** - All services use `ModelONEXContainer` for DI
3. **Never couple intelligence to infra directly** - Core has no I/O implementations
4. **All models must be serializable** - JSON/YAML compatible
5. **Use str-valued Enums** - For stable serialization
6. **Nodes are thin shells** - Nodes coordinate; handlers own business logic
7. **Reducers are pure** - `delta(state, event) -> (new_state, intents[])` with no I/O
8. **Orchestrators emit, never return** - Cannot return `result`, only `events[]` and `intents[]`

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

## Non-Goals (DO NOT)

- ❌ No concrete implementations (use `omnibase_infra`)
- ❌ No "helpful" abstractions beyond what's requested
- ❌ No versioned directories (`v1/`, `v2/`) - version through contract fields only

## Patterns to Avoid

- Business logic in nodes (put it in handlers)
- Dynamic runtime behavior not declared in contracts
- Mutable default arguments in Pydantic models (use `default_factory`)

## Layer Boundaries

```
omnibase_core (YOU ARE HERE)
    ↑ imported by
omnibase_spi (protocols)
    ↑ imported by
omnibase_infra (implementations)
```

**Core → SPI**: forbidden
**Core → Infra**: forbidden
