# OmniNode Architecture – Constraint Map (omnibase_spi)

> **Role**: Service Provider Interface – protocol contracts and exceptions
> **Handshake Version**: 0.1.0

## Core Principles

- Protocols define contracts, not behavior
- Runtime-checkable interfaces
- Zero business logic
- Pure type definitions

## This Repo Contains

- Python `typing.Protocol` definitions
- Exception hierarchy (`SPIError` and subclasses)
- No Pydantic models (those live in `omnibase_core`)
- No implementations

## Rules the Agent Must Obey

1. **All protocols must be `@runtime_checkable`** - Required for isinstance checks
2. **No Pydantic models here** - Models belong in `omnibase_core`
3. **No business logic or I/O** - Pure protocol definitions only
4. **No state machines or workflow implementations** - Those belong in infra
5. **Never import from `omnibase_infra`** - Not even transitively
6. **SPI → Core imports allowed** - Runtime imports of models and contract types

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

- ❌ No concrete implementations
- ❌ No business logic
- ❌ No I/O operations

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Node protocols | `Protocol{Type}Node` | `ProtocolComputeNode` |
| Handler protocols | `Protocol{Type}Handler` | `ProtocolHandler` |
| Service protocols | `Protocol{Domain}Service` | `ProtocolDashboardService` |
| MCP protocols | `ProtocolMCP{Function}` | `ProtocolMCPRegistry` |

## Layer Boundaries

```
omnibase_core (contracts, models)
    ↑ imported by
omnibase_spi (YOU ARE HERE)
    ↑ imported by
omnibase_infra (implementations)
```

**SPI → Core**: allowed and required
**SPI → Infra**: forbidden (no imports, even transitively)
**Core → SPI**: forbidden
