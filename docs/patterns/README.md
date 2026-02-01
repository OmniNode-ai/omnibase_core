> **Navigation**: [Home](../index.md) > Patterns

# ONEX Patterns Documentation

This section documents approved patterns, anti-patterns, and architectural guidelines for ONEX development. For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

## Pattern Categories

### Core Architecture Patterns

| Pattern | Description |
|---------|-------------|
| [Pure FSM Reducer Pattern](./PURE_FSM_REDUCER_PATTERN.md) | Deterministic, side-effect-free state transformation for REDUCER nodes |
| [Lease Management Pattern](./LEASE_MANAGEMENT_PATTERN.md) | Single-writer semantics for distributed workflows |
| [Event-Driven Architecture](./EVENT_DRIVEN_ARCHITECTURE.md) | Event patterns using ModelEventEnvelope and Intent emission |

### Resilience Patterns

| Pattern | Description |
|---------|-------------|
| [Circuit Breaker Pattern](./CIRCUIT_BREAKER_PATTERN.md) | Fault tolerance and cascading failure prevention for external dependencies |

### Configuration Patterns

| Pattern | Description |
|---------|-------------|
| [Configuration Management](./CONFIGURATION_MANAGEMENT.md) | Environment-based configuration with type conversion and validation |

### Type Safety Patterns

| Pattern | Description |
|---------|-------------|
| [Approved Union Patterns](./APPROVED_UNION_PATTERNS.md) | Approved union patterns for type-safe discriminated unions |
| [Custom Bool Pattern](./CUSTOM_BOOL_PATTERN.md) | Custom `__bool__` implementation for result models |

### Anti-Patterns

| Document | Description |
|----------|-------------|
| [Anti-Patterns](./ANTI_PATTERNS.md) | Prohibited patterns that compromise type safety, consistency, or maintainability |

## Quick Reference

### When to Use Each Pattern

- **Pure FSM Reducer**: All REDUCER node implementations - ensures testability and determinism
- **Lease Management**: Distributed workflows requiring single-writer semantics
- **Circuit Breaker**: External API calls, database connections, or any unreliable dependency
- **Event-Driven**: Inter-service communication and loose coupling
- **Custom Bool**: Result models where semantic truthiness differs from instance existence

### Pattern Selection Guide

```text
Need fault tolerance for external calls?
  -> Circuit Breaker Pattern

Building a REDUCER node?
  -> Pure FSM Reducer Pattern

Need environment-based configuration?
  -> Configuration Management

Need distributed workflow coordination?
  -> Lease Management Pattern

Building result/match models?
  -> Custom Bool Pattern

Using Union types?
  -> Approved Union Patterns
```

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [ONEX Terminology Guide](../standards/onex_terminology.md)

---

**Last Updated**: 2026-01-18 | **Maintainer**: ONEX Core Team
