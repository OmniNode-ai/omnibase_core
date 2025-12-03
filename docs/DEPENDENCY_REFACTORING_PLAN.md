# Dependency Refactoring Plan: Fixing Core/SPI Inversion

**Version**: 1.2.0
**Status**: Draft
**Created**: 2025-12-02
**Repository**: omnibase_core
**Related Documents**:
- [Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md)
- [Effect Nodes Specification](/Users/jonah/Code/omniintelligence/docs/specs/DECLARATIVE_EFFECT_NODES_SPEC.md)
- [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md)

---

## Naming Convention

**IMPORTANT**: As of v1.1.0, declarative nodes are the DEFAULT implementation pattern:

| Old Name (Deprecated) | New Name (Default) | Description |
|----------------------|-------------------|-------------|
| `NodeEffectDeclarative` | `NodeEffect` | Effect node runtime |
| `NodeComputeDeclarative` | `NodeCompute` | Compute node runtime |
| `NodeReducerDeclarative` | `NodeReducer` | Reducer node runtime |
| `NodeOrchestratorDeclarative` | `NodeOrchestrator` | Orchestrator node runtime |

Legacy imperative nodes use the `Legacy` suffix:

| Legacy Name | Description |
|-------------|-------------|
| `NodeEffectLegacy` | Old imperative effect base class |
| `NodeComputeLegacy` | Old imperative compute base class |
| `NodeReducerLegacy` | Old imperative reducer base class |
| `NodeOrchestratorLegacy` | Old imperative orchestrator base class |

**Deprecation Timeline**:
- **v0.4.0**: Legacy nodes marked deprecated with warnings
- **v0.5.0**: Legacy nodes moved to `omnibase_core.legacy` namespace
- **v1.0.0**: Legacy nodes removed

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Correct Architecture](#2-correct-architecture)
3. [Current State Analysis](#3-current-state-analysis)
4. [What Must Move](#4-what-must-move)
5. [What Stays in Core](#5-what-stays-in-core)
6. [Refactoring Tasks](#6-refactoring-tasks)
7. [Backward Compatibility Strategy](#7-backward-compatibility-strategy)
8. [Timeline](#8-timeline)
9. [Risk Assessment](#9-risk-assessment)
10. [Success Criteria](#10-success-criteria)

---

## 1. Problem Statement

### 1.1 Current Dependency Direction (INCORRECT)

```
omnibase_core                    omnibase_spi
===============                  =============
pyproject.toml:
  dependencies:
    - omnibase-spi>=0.2.0  ---> [Protocol definitions]

Models + Infrastructure          Pure Interfaces
DEPENDS ON SPI                   (no dependencies)
```

**Evidence from `pyproject.toml`**:
```toml
dependencies = [
    "omnibase-spi>=0.2.0,<0.3.0",  # <-- INCORRECT: Core depends on SPI
    ...
]
```

### 1.2 Why This Is Wrong

The Service Provider Interface (SPI) pattern establishes that:

1. **Core** provides foundational types, models, and primitives that have **zero dependencies** on interfaces
2. **SPI** provides pure Protocol interfaces that **USE** Core's types in their signatures
3. **Implementations** depend on BOTH Core (for types) and SPI (for interfaces to implement)

Currently, `omnibase_core` imports from `omnibase_spi` in 27+ files:

```python
# Examples of incorrect imports in omnibase_core:
from omnibase_spi.protocols.container import ProtocolServiceRegistry
from omnibase_spi.protocols.event_bus import ProtocolEventBus
from omnibase_spi.protocols.validation import ProtocolValidator
```

This creates a **circular conceptual dependency** where:
- Core needs SPI for Protocol definitions
- SPI should need Core for type definitions (but cannot without circular import)

### 1.3 Consequences

| Issue | Impact |
|-------|--------|
| Circular dependency risk | Future changes may create import cycles |
| Unclear architecture | Developers don't know which package is foundational |
| Testing complexity | Cannot test Core in isolation |
| Publishing order | Must publish SPI before Core (backwards) |
| Type safety gaps | SPI cannot reference Core types in Protocol signatures |

---

## 2. Correct Architecture

### 2.1 Target Dependency Direction

```
omnibase_core (Models + Primitives)     omnibase_spi (Pure Interfaces)
===================================     ===============================

ModelEffectContract                     ProtocolHandler(Protocol)
ModelProtocolConfig                       def execute(request: ModelProtocolRequest)
ModelConnectionConfig
ModelOperationConfig                    IEffectNode(Protocol)
ModelResilienceConfig                     def execute_effect(input: ModelInput)

RetryPolicy                             IComputeNode(Protocol)
CircuitBreaker                            def execute_compute(input: ModelInput)
RateLimiter
                                        IReducerNode(Protocol)
CapabilityDescriptor                      def execute_reduction(state: ModelState)
NodeId, ContractId, ErrorCode
                                        IContractCompiler(Protocol)
EnumProtocolType                          def compile(contract: ModelEffectContract)
EnumAuthType
EnumHttpMethod                          Uses Core models in signatures
                                        ==============================

DEPENDS ON: Nothing                     DEPENDS ON: omnibase_core
```

### 2.2 Correct Import Flow

```python
# In omnibase_spi (CORRECT - uses Core types)
from omnibase_core.models import ModelEffectContract, ModelProtocolRequest
from typing import Protocol, runtime_checkable

@runtime_checkable
class ProtocolHandler(Protocol):
    async def execute(
        self,
        request: ModelProtocolRequest,  # Type from Core
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:  # Type from Core
        ...
```

```python
# In omniintelligence/omnibase_infra (CORRECT - implements interfaces)
from omnibase_core.models import ModelEffectContract
from omnibase_spi.protocols import ProtocolHandler

class HttpRestHandler(ProtocolHandler):  # Implements SPI interface
    async def execute(self, request: ModelProtocolRequest, ...):
        ...
```

### 2.3 Package Responsibility Matrix

| Package | Contains | Depends On |
|---------|----------|------------|
| `omnibase_core` | Pydantic models, enums, primitives, **NodeRuntime**, **NodeInstance**, resilience algorithms, domain libraries | pydantic, standard library |
| `omnibase_spi` | Pure `typing.Protocol` interfaces for handlers, event bus, system services | `omnibase_core` |
| `omnibase_infra` | **Concrete handler implementations** (HTTP, Bolt, Postgres, Kafka, Vault), **runtime host entrypoints**, wire-up code | `omnibase_core`, `omnibase_spi` |
| `omniintelligence` | Node contracts, Pydantic IO models, domain logic | `omnibase_core`, `omnibase_spi` |

### 2.4 Core I/O Invariant

**Critical Rule**: No code in `omnibase_core` may initiate network I/O, database I/O, file I/O, or external process execution.

This invariant:
- Protects the layering
- Prevents accidental future regressions
- Ensures reproducibility and portability of the runtime
- Allows Core to be tested without mocking infrastructure

---

## 3. Current State Analysis

### 3.1 Files in Core That Import from SPI

| Category | Files | Import Pattern |
|----------|-------|----------------|
| **Container** | `service_registry.py`, `model_registry_*.py`, `model_service_*.py`, `model_onex_container.py` | `from omnibase_spi.protocols.container import ...` |
| **Mixins** | `mixin_event_bus.py`, `mixin_event_driven_node.py`, `mixin_discovery_responder.py`, `mixin_canonical_serialization.py`, `__init__.py` | `from omnibase_spi.protocols.event_bus import ...` |
| **Infrastructure** | `node_base.py` | `from omnibase_spi.protocols.workflow_orchestration import ...` |
| **Validation** | `contract_validator.py`, `auditor_protocol.py` | `from omnibase_spi.protocols.validation import ...` |
| **Types** | `core_types.py`, `constraints.py` | `from omnibase_spi.protocols.types import ...` |
| **Models** | `model_state.py`, `model_protocol_action.py`, `model_node_workflow_result.py`, `model_value_container.py`, `model_protocol_metadata.py` | Various protocol imports |
| **Utils** | `util_bootstrap.py` | `from omnibase_spi.spi_registry import ...` |

**Total: 27 files with SPI imports**

### 3.2 What Core Currently Uses from SPI

| SPI Import | Usage in Core | Should Be |
|------------|---------------|-----------|
| `ProtocolServiceRegistry` | Implement service registration | Move Protocol to SPI, keep impl in Core |
| `ProtocolEventBus` | Event bus mixin | Move Protocol to SPI, keep mixin base |
| `ProtocolEventEnvelope` | Event handling | Move to Core as Pydantic model |
| `ProtocolValidator` | Validation framework | Move Protocol to SPI, keep impl |
| `ProtocolCanonicalSerializer` | Serialization mixin | Move Protocol to SPI |
| `ProtocolConfigurable`, `ProtocolExecutable`, etc. | Type constraints | Move to Core as base protocols or ABCs |
| `ContextValue`, `LiteralOperationStatus` | Type definitions | Move to Core |
| `ProtocolSchemaValue` | Type constraint | Move to Core |

---

## 4. What Must Move

### 4.1 Types That Should Move FROM SPI TO Core

These are **data types** (not interfaces) that belong in Core:

```python
# Currently in omnibase_spi/protocols/types/
# Should move to omnibase_core/types/

ContextValue              # Dictionary value type
LiteralOperationStatus    # Literal type for status
ServiceHealthStatus       # Enum for health status
ProtocolSchemaValue       # Should be a Pydantic model
ProtocolLogEmitter        # Should be abstract base
```

### 4.2 Protocols That Should Stay in SPI

These are **pure interfaces** that should remain in SPI:

```python
# Correctly in omnibase_spi (but need Core type imports)

ProtocolServiceRegistry      # Interface - implementations in Core/Infra
ProtocolEventBus             # Interface - implementations provide behavior
ProtocolEventBusAdapter      # Interface - backend-specific
ProtocolValidator            # Interface - validation strategy
ProtocolWorkflowReducer      # Interface - workflow FSM
ProtocolHandler              # Interface - protocol handling (HTTP, Bolt, etc.)

# New handler protocols from mixin migration
ProtocolVaultHandler         # Interface for Vault operations
ProtocolConsulHandler        # Interface for Consul operations
ProtocolDbHandler            # Interface for database operations
ProtocolLlmHandler           # Interface for LLM operations
ProtocolCacheHandler         # Interface for caching operations
```

### 4.3 Models That Should Be Created in Core

The [Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md) already specifies these models for Core:

```python
# New Pydantic models for omnibase_core/nodes/effect/models/

ModelEffectContract        # Root contract model
ModelProtocolConfig        # Protocol configuration
ModelConnectionConfig      # Connection settings
ModelAuthConfig            # Authentication configuration
ModelOperationConfig       # Operation definitions
ModelRequestConfig         # Request configuration
ModelResponseConfig        # Response mapping
ModelResilienceConfig      # Resilience policies
ModelEventsConfig          # Kafka event configuration
ModelObservabilityConfig   # Metrics/tracing configuration

# Supporting models
ModelVersion               # Semantic versioning
ModelMetadata              # Contract metadata
ModelPoolConfig            # Connection pool settings
ModelTlsConfig             # TLS/SSL configuration
ModelRetryConfig           # Retry policy
ModelCircuitBreakerConfig  # Circuit breaker settings
ModelRateLimitConfig       # Rate limiting
ModelProtocolRequest       # Protocol-agnostic request
ModelProtocolResponse      # Protocol-agnostic response
```

### 4.4 Handler Protocols from Mixin Migration

The [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) identifies handler-level mixins that must become SPI protocols. These protocols define interfaces for external system interactions:

| Protocol | Description | Current Mixin |
|----------|-------------|---------------|
| `ProtocolVaultHandler` | HashiCorp Vault secret management | `MixinVaultClient` |
| `ProtocolConsulHandler` | Consul service discovery and KV | `MixinConsulClient` |
| `ProtocolDbHandler` | Database connection and query execution | `MixinDbHandler` |
| `ProtocolLlmHandler` | LLM provider abstraction (OpenAI, Anthropic, etc.) | `MixinLlmHandler` |
| `ProtocolCacheHandler` | Caching operations (Redis, Memcached, etc.) | `MixinCacheHandler` |

**Key Points**:
- These protocols are **separate from** existing protocols like `ProtocolEventBus` or `ProtocolHandler`
- Protocols define the interface contract in `omnibase_spi`
- Implementations live in `omnibase_infra` (not Core)
- Nodes consume these handlers via dependency injection, not inheritance
- This enables testing with mock handlers and swapping implementations

---

## 5. What Stays in Core

### 5.1 Existing Core Content (KEEP)

| Category | Examples | Rationale |
|----------|----------|-----------|
| **Enums** | `EnumProtocolType`, `EnumAuthType`, `EnumHttpMethod`, `EnumCircuitBreakerState` | Pure value types, no behavior |
| **Pydantic Models** | All `Model*` classes | Data validation and serialization |
| **Primitives** | `NodeId`, `ContractId`, `ErrorCode` | Type-safe identifiers |
| **Utilities** | Path handling, string manipulation | Pure functions |
| **Constants** | Configuration constants | Static values |

### 5.2 Base Classes (KEEP but Decouple from SPI)

These should remain in Core but NOT import SPI protocols:

```python
# omnibase_core/infrastructure/node_base.py
# Currently imports: ProtocolWorkflowReducer from SPI
# Solution: Use structural typing or define base class without Protocol reference

class NodeBase:
    """Base class for all nodes - no SPI imports."""
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
```

### 5.3 Resilience Components (KEEP)

As specified in the implementation plan, resilience **algorithms** (pure logic, no I/O) stay in Core:

```python
# omnibase_core/nodes/effect/resilience/

retry_policy.py       # Exponential backoff with jitter
circuit_breaker.py    # Three-state fault tolerance
rate_limiter.py       # Token bucket algorithm
```

These are pure algorithms that compute retry delays, track circuit breaker state, and manage rate limit tokens. They do NOT perform any I/O themselves.

### 5.4 NodeRuntime and NodeInstance (KEEP in Core)

The node runtime and instance classes stay in Core because they are pure coordination logic:

```python
# omnibase_core/nodes/

node_runtime.py       # Orchestrates node lifecycle (pure algorithm)
node_instance.py      # Represents a node instance (pure data + logic)
```

These classes coordinate node execution but delegate all I/O to injected handlers.

### 5.5 Handler Implementations (MOVE TO INFRA)

While resilience *algorithms* (RetryPolicy, CircuitBreaker, RateLimiter) stay in Core, the concrete *handler implementations* that perform I/O must move to `omnibase_infra`:

```python
# omnibase_infra/handlers/

http_rest_handler.py     # HTTP REST implementation (performs network I/O)
bolt_handler.py          # Neo4j/Memgraph Bolt (performs network I/O)
postgres_handler.py      # PostgreSQL (performs database I/O)
kafka_handler.py         # Kafka (performs message queue I/O)
vault_handler.py         # HashiCorp Vault (performs network I/O)
handler_registry.py      # Handler factory/registry
```

**Key Distinction**:
- **Core**: Algorithms, models, runtime coordination (no I/O)
- **Infra**: Handler implementations that actually perform I/O

---

## 6. Refactoring Tasks

### Phase 1: Prepare Core (No Breaking Changes)

**Duration**: 3-5 days

| Task | Description | Files Affected |
|------|-------------|----------------|
| 1.1 | Create `omnibase_core/types/literals.py` with type literals | New file |
| 1.2 | Create `omnibase_core/types/primitives.py` for `ContextValue`, etc. | New file |
| 1.3 | Implement effect models per implementation plan | `nodes/effect/models/` |
| 1.4 | Implement resilience components | `nodes/effect/resilience/` |
| 1.5 | Implement protocol handlers | `nodes/effect/handlers/` |
| 1.6 | Add deprecation warnings to files that import from SPI | 27 files |

### Phase 2: Update SPI to Use Core Types

**Duration**: 2-3 days

| Task | Description | Files Affected |
|------|-------------|----------------|
| 2.1 | Add `omnibase_core` as dependency in SPI's `pyproject.toml` | `omnibase_spi/pyproject.toml` |
| 2.2 | Update Protocol signatures to use Core models | All protocol files in SPI |
| 2.3 | Remove duplicate type definitions from SPI | `protocols/types/` |
| 2.4 | Update SPI exports in `__init__.py` | `omnibase_spi/__init__.py` |
| 2.5 | Create handler protocols for mixin migration (VaultHandler, ConsulHandler, DbHandler, LlmHandler, CacheHandler) | New protocol files in SPI |

### Phase 3: Migrate Core Imports

**Duration**: 5-7 days

| Task | Description | Files Affected |
|------|-------------|----------------|
| 3.1 | Replace SPI protocol imports with Core base classes | Container files |
| 3.2 | Update mixins to use Core types only | Mixin files |
| 3.3 | Update infrastructure to use Core base classes | `node_base.py` |
| 3.4 | Update validation to use Core types | Validation files |
| 3.5 | Update type constraints to use Core primitives | `types/constraints.py` |
| 3.6 | Remove `omnibase-spi` from Core's dependencies | `pyproject.toml` |

### Phase 4: Update Consuming Repositories

**Duration**: 3-5 days

| Task | Description | Repositories |
|------|-------------|--------------|
| 4.1 | Update omniintelligence to import from correct packages | omniintelligence |
| 4.2 | Update omnibase_infra to import from correct packages | omnibase_infra |
| 4.3 | Update omnibuild to import from correct packages | omnibuild |
| 4.4 | Run full test suites on all repositories | All |

### Phase 5: Cleanup and Documentation

**Duration**: 2 days

| Task | Description |
|------|-------------|
| 5.1 | Remove deprecated re-exports |
| 5.2 | Update architecture documentation |
| 5.3 | Update import examples in docstrings |
| 5.4 | Verify type safety with mypy |
| 5.5 | Final integration testing |

---

## 7. Backward Compatibility Strategy

### 7.1 Deprecation Approach

Use Python's `warnings` module with `DeprecationWarning`:

```python
# In files that currently import from SPI
import warnings

# At module level or in functions that use SPI types
warnings.warn(
    "Importing from omnibase_spi in omnibase_core is deprecated. "
    "Use omnibase_core types directly. This will be removed in v0.4.0.",
    DeprecationWarning,
    stacklevel=2
)
```

### 7.2 Re-export Strategy

During transition, Core can re-export SPI protocols:

```python
# omnibase_core/compat/__init__.py (temporary module)
"""
Backward compatibility layer for SPI imports.
DEPRECATED: Import directly from omnibase_spi instead.
"""

import warnings
warnings.warn(
    "omnibase_core.compat is deprecated. Import from omnibase_spi.",
    DeprecationWarning
)

# Re-exports (to be removed in v0.4.0)
from omnibase_spi.protocols.container import ProtocolServiceRegistry
from omnibase_spi.protocols.event_bus import ProtocolEventBus
# ... etc
```

### 7.3 Version Pinning

| Version | State |
|---------|-------|
| v0.3.x | Current (incorrect dependency) |
| v0.3.6+ | Add deprecation warnings |
| v0.4.0 | Remove SPI dependency from Core |
| v0.5.0 | Remove compat module |

### 7.4 Migration Guide for Consumers

```python
# Before (v0.3.x)
from omnibase_core.validation import contract_validator  # Pulls in SPI internally

# After (v0.4.0+)
from omnibase_core.models import ModelEffectContract  # Core types
from omnibase_spi.protocols import ProtocolValidator   # SPI interfaces

# Implement your validator
class MyValidator(ProtocolValidator):
    def validate(self, contract: ModelEffectContract) -> ValidationResult:
        ...
```

---

## 8. Timeline

### Overview

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Prepare Core | 5 days | Week 1 | Week 1 |
| Phase 2: Update SPI | 3 days | Week 2 | Week 2 |
| Phase 3: Migrate Core | 7 days | Week 2-3 | Week 3 |
| Phase 4: Update Consumers | 5 days | Week 3-4 | Week 4 |
| Phase 5: Cleanup | 2 days | Week 4 | Week 4 |
| **Total** | **~4 weeks** | | |

### Detailed Schedule

**Week 1 (Phase 1)**:
- Day 1-2: Create new Core types and literals
- Day 3-4: Implement declarative effect models
- Day 5: Implement resilience components

**Week 2 (Phases 1-3)**:
- Day 1-2: Implement protocol handlers
- Day 3-4: Update SPI to depend on Core
- Day 5: Begin migrating Core imports

**Week 3 (Phase 3-4)**:
- Day 1-3: Complete Core import migration
- Day 4-5: Update omniintelligence

**Week 4 (Phases 4-5)**:
- Day 1-2: Update remaining consumers
- Day 3: Final testing
- Day 4-5: Documentation and cleanup

### Milestones

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| M1 | End Week 1 | Core models and resilience complete |
| M2 | Mid Week 2 | SPI updated to use Core types |
| M3 | End Week 3 | Core no longer depends on SPI |
| M4 | End Week 4 | All consumers updated |

---

## 9. Risk Assessment

### 9.1 High Risk

| Risk | Mitigation |
|------|------------|
| Breaking changes in consuming repos | Comprehensive deprecation warnings, migration guide |
| Circular import during transition | Careful import ordering, use `TYPE_CHECKING` |
| Test failures | Run tests after each phase, revert if needed |

### 9.2 Medium Risk

| Risk | Mitigation |
|------|------------|
| Type checking errors | Run mypy incrementally, fix as discovered |
| Missing Protocol implementations | Audit all Protocol usages before migration |
| Documentation drift | Update docs in same PR as code changes |

### 9.3 Low Risk

| Risk | Mitigation |
|------|------------|
| Performance regression | Benchmark critical paths before/after |
| Import time increase | Use lazy loading where appropriate |

---

## 10. Success Criteria

### 10.1 Technical Criteria

- [ ] `omnibase_core` has ZERO imports from `omnibase_spi`
- [ ] `omnibase_spi` depends on `omnibase_core>=0.4.0`
- [ ] All Protocol signatures use Core types
- [ ] No circular import errors
- [ ] `mypy --strict` passes on both packages
- [ ] All existing tests pass

### 10.2 Architecture Criteria

- [ ] Clear separation: Core = Types, SPI = Interfaces
- [ ] Dependency direction matches SPI pattern
- [ ] Consuming repos compile without errors
- [ ] Import statements follow documented patterns

### 10.3 Quality Criteria

- [ ] Deprecation warnings in v0.3.6+
- [ ] Migration guide published
- [ ] Architecture diagrams updated
- [ ] All docstrings reflect new structure

---

## Appendix A: File-by-File Migration Plan

### Container Files

| File | Current SPI Imports | Migration Strategy |
|------|---------------------|-------------------|
| `service_registry.py` | `ProtocolServiceRegistry`, `ProtocolDIServiceInstance`, etc. | Keep impl, remove Protocol type hints |
| `model_registry_status.py` | `ProtocolServiceRegistryStatus`, `LiteralOperationStatus` | Move literal to Core |
| `model_service_registration.py` | `ProtocolServiceRegistration`, `ProtocolDIServiceMetadata` | Use Core model |
| `model_service_instance.py` | `ProtocolDIServiceInstance`, `ProtocolDIServiceMetadata` | Use Core model |
| `model_onex_container.py` | (TODO comments only) | No changes needed |

### Mixin Files

| File | Current SPI Imports | Migration Strategy |
|------|---------------------|-------------------|
| `mixin_event_bus.py` | `ProtocolEventEnvelope` | Create Core model |
| `mixin_event_driven_node.py` | `ProtocolEventBus`, `ProtocolSchemaLoader` | Use structural typing |
| `mixin_discovery_responder.py` | `ProtocolEventBus` | Use structural typing |
| `mixin_canonical_serialization.py` | `ProtocolCanonicalSerializer`, `ContextValue` | Move types to Core |

### Infrastructure Files

| File | Current SPI Imports | Migration Strategy |
|------|---------------------|-------------------|
| `node_base.py` | `ProtocolWorkflowReducer` | Use ABC or structural typing |

### Validation Files

| File | Current SPI Imports | Migration Strategy |
|------|---------------------|-------------------|
| `contract_validator.py` | `ProtocolComplianceValidator`, `ProtocolValidator`, etc. | Keep impl, use structural typing |
| `auditor_protocol.py` | `ProtocolQualityValidator`, `ProtocolValidator` | Remove Protocol type hints |

### Type Files

| File | Current SPI Imports | Migration Strategy |
|------|---------------------|-------------------|
| `core_types.py` | `ProtocolSchemaValue` | Create Core version |
| `constraints.py` | `ProtocolConfigurable`, `ProtocolExecutable`, etc. | Create Core ABCs |

---

## Appendix B: Integration with Effect Nodes

The [Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md) specifies new models and components for Core. This refactoring plan is a **prerequisite** for that implementation because:

1. **Models must exist before Protocols reference them**: SPI's `ProtocolHandler` signature needs `ModelProtocolRequest` from Core
2. **Clean architecture enables clean contracts**: YAML contracts compile to Core models, validated by SPI interfaces
3. **Testing isolation**: Core components can be unit tested without SPI dependencies

### Alignment Points

| Implementation Plan Section | This Plan Phase |
|----------------------------|-----------------|
| Section 3: Pydantic Models | Phase 1 (Task 1.3) |
| Section 5: Resilience Components | Phase 1 (Task 1.4) |
| Section 4: Protocol Handlers | Phase 1 (Task 1.5) |
| Section 9: Dependencies | Phase 3 (Task 3.6) |

### Handler Protocols from Mixin Migration

The [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) provides the complete list of mixins that must become handler protocols. These protocols **must be created in SPI before** handler implementations can be developed in `omnibase_infra`.

The migration identifies several handler-level mixins (e.g., `MixinVaultClient`, `MixinConsulClient`, `MixinDbHandler`, `MixinLlmHandler`, `MixinCacheHandler`) that currently provide external system integration through inheritance. Under the refactored architecture:

1. **SPI defines the protocol**: Each handler type gets a `Protocol*Handler` interface in `omnibase_spi`
2. **Core stays clean**: No handler implementations or external dependencies in Core
3. **Infra implements**: Concrete handler implementations live in `omnibase_infra`
4. **Nodes consume via DI**: Effect nodes receive handlers through dependency injection

This aligns with the declarative effect node pattern where YAML contracts specify required capabilities, and the runtime injects appropriate handler implementations.

---

## Appendix C: Reference Links

- [ONEX Architecture Documentation](./architecture/)
- [SPI Pattern Reference](./patterns/)
- [Effect Nodes Specification](/Users/jonah/Code/omniintelligence/docs/specs/DECLARATIVE_EFFECT_NODES_SPEC.md)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- [typing.Protocol PEP 544](https://peps.python.org/pep-0544/)
