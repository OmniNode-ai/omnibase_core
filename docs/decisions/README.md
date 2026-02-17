> **Navigation**: [Home](../INDEX.md) > Decisions (ADRs)

# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant design decisions in omnibase_core.

> **Note**: ADRs explain *why* decisions were made. For the resulting coding rules and standards, see [CLAUDE.md](../../CLAUDE.md) which is the authoritative source for all development guidelines.

## What is an ADR?

An ADR captures:
- **Context**: The situation that led to needing a decision
- **Decision**: What was decided
- **Consequences**: The trade-offs and implications

ADRs are immutable once accepted. Superseded decisions are marked but not deleted.

## ADR Index

| ID | Title | Status | Date | Category | Key Topics |
|----|-------|--------|------|----------|------------|
| [ADR-001](ADR-001-protocol-based-di-architecture.md) | Protocol-Based Dependency Injection Architecture | Implemented | 2025-10-30 | Architecture | DI, ServiceRegistry, Protocols, Pydantic |
| [ADR-002](ADR-002-field-limit-constants.md) | Centralized Field Limit Constants | Accepted | 2025-12-27 | Validation | Field Limits, Constants, Pydantic |
| [ADR-003](ADR-003-reducer-output-exception-consistency.md) | Reducer Output Exception Consistency | Implemented | 2025-12-16 | Error Handling | Validation, Sentinel Pattern |
| [ADR-004](ADR-004-registration-trigger-architecture.md) | Registration Trigger Architecture | Accepted | 2025-12-19 | Architecture | Registration, Events, Commands, Orchestrator |
| [ADR-005](ADR-005-core-infra-dependency-boundary.md) | Core-Infra Dependency Boundary | Implemented | 2025-12-26 | Architecture | Dependency Inversion, Transport Libraries |
| [ADR-006](ADR-006-status-taxonomy.md) | Status Taxonomy and Categorical Organization | Accepted | 2026-01-12 | Type System | Status Enums, Taxonomy, Severity, Health |
| [ADR-007](ADR-007-context-mutability-design-decision.md) | Context Mutability Design Decision | Implemented | 2025-12-15 | API Design | Immutability, Workflow State, FSM Snapshots |
| [ADR-012](ADR-012-VALIDATOR-ERROR-HANDLING.md) | Validator Error Handling with ModelOnexError | Accepted | 2026-01-18 | Error Handling | Pydantic Validators, ModelOnexError |

## Risk Records

| ID | Title | Status | Date | Category | Key Topics |
|----|-------|--------|------|----------|------------|
| [RISK-009](RISK-009-ci-workflow-modification-risk.md) | CI Workflow Modification Risk | Mitigated | 2025-12-10 | Security | CI/CD, Transport Imports, Dependency Inversion |

## Categories

| Category | Description | Count |
|----------|-------------|-------|
| **Architecture** | Node types, handlers, protocols, dependency boundaries | 3 |
| **Error Handling** | Error patterns, validation, exception handling | 2 |
| **Type System** | Type safety, enums, status taxonomy | 1 |
| **Validation** | Field limits, validation rules | 1 |
| **API Design** | Context mutability, immutability patterns | 1 |
| **Security** | CI/CD security, risk mitigation | 1 |

## ADR Quick Reference by Topic

### Dependency Injection & Architecture
- [ADR-001](ADR-001-protocol-based-di-architecture.md): Protocol-Based DI Architecture - Establishes protocol-based dependency injection via `ServiceRegistry`
- [ADR-005](ADR-005-core-infra-dependency-boundary.md): Core-Infra Dependency Boundary - Forbids transport libraries in omnibase_core

### Error Handling & Validation
- [ADR-003](ADR-003-reducer-output-exception-consistency.md): Reducer Output Exception Consistency - Sentinel value validation pattern
- [ADR-012](ADR-012-VALIDATOR-ERROR-HANDLING.md): Validator Error Handling - Use `ModelOnexError` in Pydantic validators

### Status & Type Architecture
- [ADR-006](ADR-006-status-taxonomy.md): Status Taxonomy - Six canonical status categories

### State Management & Immutability
- [ADR-007](ADR-007-context-mutability-design-decision.md): Context Mutability - Convention-based immutability for context dicts

### Node Registration & Discovery
- [ADR-004](ADR-004-registration-trigger-architecture.md): Registration Trigger Architecture - Event-driven vs command-driven registration

### Field Constraints
- [ADR-002](ADR-002-field-limit-constants.md): Centralized Field Limit Constants - `constants_field_limits.py` module

## Writing ADRs

New ADRs should:
1. Use kebab-case filename: `ADR-NNN-descriptive-title.md`
2. Include standard sections: Status, Context, Decision, Consequences
3. Be reviewed before merging
4. Never be deleted (mark superseded instead)
5. Follow the [ADR Best Practices Guide](ADR_BEST_PRACTICES.md)

### ADR Numbering

When creating a new ADR:
1. Check this index for the next available number (currently: **ADR-014**; note ADR-013 was superseded and merged into ADR-006)
2. Use format: `ADR-NNN-descriptive-title.md`
3. Update this README with your new ADR
4. Follow the template in [ADR_BEST_PRACTICES.md](ADR_BEST_PRACTICES.md)

### Template

```markdown
# ADR-NNN: <Title>

## Status

Accepted | Superseded by ADR-XXX | Deprecated

## Context

What is the situation that requires a decision?

## Decision

What was decided?

## Consequences

### Positive
- Benefit 1
- Benefit 2

### Negative
- Trade-off 1
- Trade-off 2

### Neutral
- Side effect 1
```

## Status Indicators

- **Implemented**: Decision is fully implemented and active
- **Accepted**: Decision approved, implementation may be in progress
- **Superseded**: Decision replaced by newer ADR (includes link)
- **Rejected**: Decision was considered but not adopted
- **Mitigated**: Risk has been addressed with controls in place

## Supporting Documents

- [ADR Best Practices Guide](ADR_BEST_PRACTICES.md) - How to write and maintain ADRs
- [ADR Fixes Summary](ADR_FIXES_SUMMARY.md) - Summary of fixes applied to ADR documents (PR #205)

---

**Last Updated**: 2026-02-14
**Total ADRs**: 8
**Total Risk Records**: 1
