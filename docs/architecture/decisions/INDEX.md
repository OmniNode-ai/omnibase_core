# Architecture Decision Records (ADR) Index

This directory contains all Architecture Decision Records (ADRs) for the omnibase_core project.

---

## What is an ADR?

Architecture Decision Records (ADRs) document significant architectural decisions made during the project lifecycle. They capture:
- **Context**: Why the decision was needed
- **Decision**: What was decided
- **Options Considered**: Alternative approaches evaluated
- **Trade-offs**: Benefits and drawbacks accepted
- **Implementation**: How it was implemented (with commit SHA references)

---

## ADR Status Indicators

- 🟢 **IMPLEMENTED** - Decision is fully implemented and active
- 🟡 **IN PROGRESS** - Implementation currently underway
- 🔴 **REJECTED** - Decision was considered but not adopted
- ⚪ **SUPERSEDED** - Decision replaced by newer ADR (includes link)

---

## ADR Registry

| Number | Title | Status | Date | Key Topics |
|--------|-------|--------|------|------------|
| [ADR-001](./ADR-001-protocol-based-di-architecture.md) | Protocol-Based Dependency Injection Architecture | 🟢 **IMPLEMENTED** | 2025-10-30 | DI, ServiceRegistry, Protocols, Pydantic |
| [ADR-002](./ADR-002-context-mutability-design-decision.md) | Context Mutability Design Decision | 🟢 **IMPLEMENTED** | 2025-12-15 | Immutability, Workflow State, FSM Snapshots |
| [ADR-003](./ADR-003-reducer-output-exception-consistency.md) | Reducer Output Exception Consistency | 🟢 **IMPLEMENTED** | 2025-12-16 | Error Handling, Validation, Sentinel Pattern |

---

## Risk Records

| Number | Title | Status | Date | Key Topics |
|--------|-------|--------|------|------------|
| [RISK-009](./RISK-009-ci-workflow-modification-risk.md) | CI Workflow Modification Risk | 🟢 **MITIGATED** | 2025-12-10 | CI/CD, Transport Imports, Dependency Inversion |

---

## Best Practices

- [ADR Best Practices Guide](./ADR_BEST_PRACTICES.md) - How to write and maintain ADRs

---

## Quick Navigation by Topic

### Dependency Injection & Architecture
- ADR-001: Protocol-Based DI Architecture
- RISK-009: CI Workflow Modification Risk

### State Management & Immutability
- ADR-002: Context Mutability Design Decision

### Error Handling & Validation
- ADR-003: Reducer Output Exception Consistency

---

## How to Use This Index

1. **Finding a Decision**: Use the registry tables above or search by topic
2. **Writing a New ADR**: Follow the [ADR Best Practices Guide](./ADR_BEST_PRACTICES.md)
3. **Understanding Status**: Check the status indicator for current implementation state
4. **Cross-References**: Each ADR links to related decisions and implementation files

---

## ADR Numbering Convention

- **ADR-NNN**: Architecture Decision Records (sequential numbering)
- **RISK-NNN**: Risk Assessment Records (separate numbering sequence)

When creating a new ADR:
1. Check this index for the next available number
2. Use format: `ADR-XXX-descriptive-title.md`
3. Update this index with your new ADR
4. Follow the template in ADR_BEST_PRACTICES.md

---

**Last Updated**: 2025-12-16
**Total ADRs**: 3 implemented
**Total Risk Records**: 1 mitigated
**Correlation ID**: `95cac850-05a3-43e2-9e57-ccbbef683f43`
