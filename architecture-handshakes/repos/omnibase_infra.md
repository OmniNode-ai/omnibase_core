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

## Rules the Agent Must Obey

1. **Nodes MUST be declarative** - `node.py` extends base class with NO custom logic
2. **Handlers own ALL business logic** - Nodes are thin coordination shells
3. **Reducers are pure** - No I/O in reducer handlers
4. **Orchestrators emit, never return** - Cannot return `result`
5. **Contracts are source of truth** - YAML contracts define behavior
6. **Container injection required** - All services via `ModelONEXContainer`
7. **Never block on Kafka** - Kafka is optional; operations must succeed without it

## Non-Goals (DO NOT)

- ❌ No backwards compatibility - change freely, no deprecation periods
- ❌ No versioned directories (`v1_0_0/`, `v2/`) - version through contract.yaml fields only
- ❌ No convenience over correctness - contract violations fail loudly
- ❌ No business logic in nodes - nodes coordinate, handlers compute
- ❌ No implicit state - all state transitions explicit and auditable

## Patterns to Avoid

- Custom logic in `node.py` beyond base class extension
- Error handling in nodes (belongs in handlers)
- Direct Kafka/Postgres calls in nodes (use effect handlers)
- Leaving deprecated code "for reference" - DELETE IT

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
