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

## Non-Goals (DO NOT)

- ❌ No concrete implementations (use `omnibase_infra`)
- ❌ No "helpful" abstractions beyond what's requested
- ❌ No speculative refactors
- ❌ No silent schema changes
- ❌ No backwards compatibility shims, deprecation warnings, or compatibility layers
- ❌ No versioned directories (`v1/`, `v2/`) - version through contract fields only

## Patterns to Avoid

- Business logic in nodes (put it in handlers)
- `datetime.now()` in models (inject timestamps explicitly)
- Dynamic runtime behavior not declared in contracts
- Mutable default arguments in Pydantic models (use `default_factory`)
- `# type: ignore` without explanation and ticket reference

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
