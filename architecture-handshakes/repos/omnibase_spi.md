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

## Non-Goals (DO NOT)

- ❌ No concrete implementations
- ❌ No business logic
- ❌ No I/O operations
- ❌ No backwards compatibility shims

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
