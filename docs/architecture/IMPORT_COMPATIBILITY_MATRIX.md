# Import Compatibility Matrix

> **Version**: 0.4.0
> **Status**: Phase 0 - Repository Stabilization (OMN-151)
> **Last Updated**: 2025-12-09
> **Purpose**: Document all current import paths for compatibility during v0.4.0 migration

---

## Table of Contents

1. [Overview](#overview)
2. [Primary Public Imports](#primary-public-imports)
3. [omnibase_core.nodes Module](#omnibase_corenodes-module)
4. [omnibase_core.infrastructure Module](#omnibase_coreinfrastructure-module)
5. [omnibase_core.enums Module](#omnibase_coreenums-module)
6. [omnibase_core.errors Module](#omnibase_coreerrors-module)
7. [omnibase_core.protocols Module](#omnibase_coreprotocols-module)
8. [omnibase_core.mixins Module](#omnibase_coremixins-module)
9. [omnibase_core.decorators Module](#omnibase_coredecorators-module)
10. [omnibase_core.validation Module](#omnibase_corevalidation-module)
11. [omnibase_core.models Module](#omnibase_coremodels-module)
12. [Consumer Repositories](#consumer-repositories)
13. [Compatibility Shims Required](#compatibility-shims-required)
14. [Migration Notes](#migration-notes)

---

## Overview

This document provides a comprehensive compatibility matrix for all public import paths in `omnibase_core`. These imports represent the public API contract that MUST be maintained during the v0.4.0 migration to avoid breaking consumer code.

### Import Path Stability Guarantees

| Stability Level | Description | Breaking Change Policy |
|----------------|-------------|------------------------|
| **STABLE** | Frozen API - must not change without deprecation | Major version bump required |
| **RECOMMENDED** | Current best practice - preferred for new code | Minor version may add functionality |
| **DEPRECATED** | Will be removed in future version | Deprecation warning, migration path provided |
| **INTERNAL** | Implementation detail - may change | No stability guarantee |

---

## Primary Public Imports

### Top-Level Package (`omnibase_core`)

```python
from omnibase_core import (
    # Error classes (commonly used)
    EnumCoreErrorCode,
    ModelOnexError,
    # Validation tools (main exports for other repositories)
    ServiceValidationSuite,
    ModelValidationResult,
    validate_all,
    validate_architecture,
    validate_contracts,
    validate_patterns,
    validate_union_usage,
)
```

| Export | Type | Stability | Notes |
|--------|------|-----------|-------|
| `EnumCoreErrorCode` | Enum | STABLE | Core error code enumeration |
| `ModelOnexError` | Class | STABLE | Structured error model |
| `ServiceValidationSuite` | Class | STABLE | Validation suite runner |
| `ModelValidationResult` | Class | STABLE | Validation result container |
| `validate_all` | Function | STABLE | Run all validations |
| `validate_architecture` | Function | STABLE | Architecture validation |
| `validate_contracts` | Function | STABLE | Contract validation |
| `validate_patterns` | Function | STABLE | Pattern validation |
| `validate_union_usage` | Function | STABLE | Union usage validation |

---

## omnibase_core.nodes Module

### RECOMMENDED Import Pattern (v0.4.0+)

```python
from omnibase_core.nodes import (
    # Node implementations (inherit from these)
    NodeCompute,
    NodeEffect,
    NodeOrchestrator,
    NodeReducer,
    # Input/Output models (use these for process() calls)
    ModelComputeInput,
    ModelComputeOutput,
    ModelEffectInput,
    ModelEffectOutput,
    ModelEffectTransaction,  # For rollback failure callback type hints
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    ModelReducerInput,
    ModelReducerOutput,
    # Public enums (use these for configuration)
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
```

### Full Export Matrix

| Export | Type | Stability | Category | Notes |
|--------|------|-----------|----------|-------|
| `NodeCompute` | Class | STABLE | Node Implementation | Data processing node |
| `NodeEffect` | Class | STABLE | Node Implementation | External I/O node |
| `NodeReducer` | Class | STABLE | Node Implementation | FSM-driven state management (formerly `NodeReducerDeclarative`) |
| `NodeOrchestrator` | Class | STABLE | Node Implementation | Workflow-driven coordination (formerly `NodeOrchestratorDeclarative`) |
| `ModelComputeInput` | Model | STABLE | I/O Model | Input for COMPUTE nodes |
| `ModelComputeOutput` | Model | STABLE | I/O Model | Output from COMPUTE nodes |
| `ModelEffectInput` | Model | STABLE | I/O Model | Input for EFFECT nodes |
| `ModelEffectOutput` | Model | STABLE | I/O Model | Output from EFFECT nodes |
| `ModelEffectTransaction` | Model | STABLE | I/O Model | For rollback failure callback type hints |
| `ModelReducerInput` | Model | STABLE | I/O Model | Input for REDUCER nodes |
| `ModelReducerOutput` | Model | STABLE | I/O Model | Output from REDUCER nodes |
| `ModelOrchestratorInput` | Model | STABLE | I/O Model | Input for ORCHESTRATOR nodes |
| `ModelOrchestratorOutput` | Model | STABLE | I/O Model | Output from ORCHESTRATOR nodes |
| `EnumActionType` | Enum | STABLE | Orchestrator Enum | Action types for orchestrator |
| `EnumBranchCondition` | Enum | STABLE | Orchestrator Enum | Branch conditions |
| `EnumExecutionMode` | Enum | STABLE | Orchestrator Enum | Execution modes |
| `EnumWorkflowState` | Enum | STABLE | Orchestrator Enum | Workflow states |
| `EnumConflictResolution` | Enum | STABLE | Reducer Enum | Conflict resolution strategies |
| `EnumReductionType` | Enum | STABLE | Reducer Enum | Reduction types |
| `EnumStreamingMode` | Enum | STABLE | Reducer Enum | Streaming modes |

### Direct File Imports (Supported but not recommended)

```python
# These work but the top-level import is preferred
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
```

---

## omnibase_core.infrastructure Module

### Public Exports

```python
from omnibase_core.infrastructure import (
    # Node bases
    NodeBase,
    NodeCoreBase,
    # Infrastructure classes
    ModelCircuitBreaker,
    ModelComputeCache,
    ModelEffectTransaction,
)
```

### Full Export Matrix

| Export | Type | Stability | Notes |
|--------|------|-----------|-------|
| `NodeBase` | Class | STABLE | Workflow-oriented node base with LlamaIndex integration |
| `NodeCoreBase` | Class | STABLE | Foundation for 4-node architecture (inherits from ABC) |
| `ModelCircuitBreaker` | Model | STABLE | Circuit breaker pattern for fault tolerance |
| `ModelComputeCache` | Model | STABLE | Caching for compute operations |
| `ModelEffectTransaction` | Model | STABLE | Transaction support for effect operations |

### Class Relationship Notes

- `NodeBase` and `NodeCoreBase` are **INDEPENDENT** base classes (sibling classes)
- `NodeCoreBase` inherits from `ABC` and is recommended for 4-node architecture
- `NodeBase` provides LlamaIndex workflow integration with observable state transitions
- Neither inherits from the other

---

## omnibase_core.enums Module

### Comprehensive Enum Exports

The `omnibase_core.enums` module exports 100+ enums organized by domain. Key exports include:

```python
from omnibase_core.enums import (
    # Error code domain
    EnumCLIExitCode,
    EnumOnexErrorCode,
    EnumCoreErrorCode,
    EnumRegistryErrorCode,
    CORE_ERROR_CODE_TO_EXIT_CODE,
    get_core_error_description,
    get_exit_code_for_core_error,

    # Node domain
    EnumNodeKind,              # Architectural classification (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)
    EnumNodeType,              # Implementation type (TRANSFORMER, AGGREGATOR, etc.)
    EnumNodeStatus,
    EnumNodeHealthStatus,

    # Effect domain
    EnumCircuitBreakerState,
    EnumEffectHandlerType,
    EnumEffectType,
    EnumTransactionState,

    # Orchestrator domain
    EnumActionType,
    EnumBranchCondition,
    EnumWorkflowState,

    # Reducer domain
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,

    # Execution domain
    EnumExecutionMode,
    EnumExecutionTrigger,

    # Validation domain
    EnumValidationLevel,
    EnumValidationMode,
    EnumValidationRuleType,

    # Health and status domain
    EnumHealthCheckType,
    EnumHealthDetailType,
    EnumHealthStatusType,
    EnumOperationStatus,

    # Many more...
)
```

### Key Enum Categories

| Category | Examples | Notes |
|----------|----------|-------|
| Error Codes | `EnumCoreErrorCode`, `EnumOnexErrorCode`, `EnumCLIExitCode` | Structured error handling |
| Node Classification | `EnumNodeKind`, `EnumNodeType`, `EnumNodeStatus` | Node architecture |
| Effect Types | `EnumEffectType`, `EnumCircuitBreakerState`, `EnumTransactionState` | Effect node configuration |
| Orchestrator Types | `EnumActionType`, `EnumBranchCondition`, `EnumWorkflowState` | Workflow orchestration |
| Reducer Types | `EnumConflictResolution`, `EnumReductionType`, `EnumStreamingMode` | FSM state management |

---

## omnibase_core.errors Module

### Public Exports

```python
from omnibase_core.errors import (
    # Exception classes
    ComputePipelineError,
    ContractValidationError,
    EventBusError,
    HandlerExecutionError,
    InvalidOperationError,
    RuntimeHostError,

    # Error enums
    EnumCLIExitCode,
    EnumCoreErrorCode,
    EnumRegistryErrorCode,

    # Error models
    ModelCLIAdapter,
    ModelOnexError,       # Also aliased as OnexError
    ModelOnexWarning,
    ModelRegistryError,
    OnexError,            # Alias for ModelOnexError

    # Error helper functions
    get_core_error_description,
    get_error_codes_for_component,
    get_exit_code_for_core_error,
    get_exit_code_for_status,
    list_registered_components,
    register_error_codes,
)
```

### Export Matrix

| Export | Type | Stability | Notes |
|--------|------|-----------|-------|
| `ModelOnexError` | Class | STABLE | Primary structured error class |
| `OnexError` | Alias | STABLE | Alias for `ModelOnexError` |
| `EnumCoreErrorCode` | Enum | STABLE | Core error code enumeration |
| `ComputePipelineError` | Exception | STABLE | Compute pipeline errors |
| `ContractValidationError` | Exception | STABLE | Contract validation errors |
| `EventBusError` | Exception | STABLE | Event bus errors |
| `RuntimeHostError` | Exception | STABLE | Runtime host errors |

---

## omnibase_core.protocols Module

### Public Exports

The protocols module provides Core-native protocol definitions (replacing SPI protocol dependencies).

```python
from omnibase_core.protocols import (
    # Container protocols
    ProtocolServiceRegistry,
    ProtocolServiceRegistration,
    ProtocolServiceFactory,
    ProtocolDependencyGraph,
    ProtocolInjectionContext,

    # Event bus protocols
    ProtocolEventBus,
    ProtocolAsyncEventBus,
    ProtocolSyncEventBus,
    ProtocolEventEnvelope,
    ProtocolEventBusRegistry,

    # Type protocols
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolIdentifiable,
    ProtocolValidatable,
    ProtocolSerializable,
    ProtocolLogEmitter,

    # Validation protocols
    ProtocolValidator,
    ProtocolValidationResult,
    ProtocolComplianceValidator,
    ProtocolQualityValidator,

    # Type variables and literals
    T,
    T_co,
    TInterface,
    TImplementation,
    LiteralLogLevel,
    LiteralNodeType,
    LiteralHealthStatus,
    # ... many more
)
```

### Migration from SPI

```python
# Before (SPI import - DEPRECATED):
from omnibase_spi.protocols.container import ProtocolServiceRegistry

# After (Core-native - RECOMMENDED):
from omnibase_core.protocols import ProtocolServiceRegistry
```

---

## omnibase_core.mixins Module

### Public Exports

```python
from omnibase_core.mixins import (
    # Core mixins
    MixinCanonicalYAMLSerializer,
    MixinComputeExecution,
    MixinDiscoveryResponder,
    MixinEventBus,
    MixinEventHandler,
    MixinEventListener,
    MixinFailFast,
    MixinFSMExecution,
    MixinHealthCheck,
    MixinNodeLifecycle,
    MixinNodeExecutor,
    MixinWorkflowExecution,

    # Protocol aliases
    ProtocolEventBusRegistry,
    ProtocolRegistryWithBus,  # DEPRECATED: Use ProtocolEventBusRegistry
    LogEmitter,
    RegistryWithBus,

    # Health check utilities
    check_postgresql_health,
    check_kafka_health,
    check_redis_health,
    check_http_service_health,
)
```

### Full Mixin Export List

| Mixin | Stability | Purpose |
|-------|-----------|---------|
| `MixinCanonicalYAMLSerializer` | STABLE | YAML serialization |
| `MixinCLIHandler` | STABLE | CLI handling |
| `MixinComputeExecution` | STABLE | Compute execution logic |
| `MixinContractMetadata` | STABLE | Contract metadata access |
| `MixinContractStateReducer` | STABLE | Contract state reduction |
| `MixinDebugDiscoveryLogging` | STABLE | Debug logging for discovery |
| `MixinDiscoveryResponder` | STABLE | Service discovery responses |
| `MixinEventBus` | STABLE | Event bus integration |
| `MixinEventDrivenNode` | STABLE | Event-driven node behavior |
| `MixinEventHandler` | STABLE | Event handling |
| `MixinEventListener` | STABLE | Event listening |
| `MixinFailFast` | STABLE | Fail-fast behavior |
| `MixinFSMExecution` | STABLE | FSM execution logic |
| `MixinHashComputation` | STABLE | Hash computation |
| `MixinHealthCheck` | STABLE | Health check capabilities |
| `MixinHybridExecution` | STABLE | Hybrid execution |
| `MixinIntentPublisher` | STABLE | Intent publishing |
| `MixinIntrospectFromContract` | STABLE | Contract introspection |
| `MixinIntrospectionPublisher` | STABLE | Introspection publishing |
| `MixinLazyEvaluation` | STABLE | Lazy evaluation |
| `ModelLogData` | STABLE | Log data handling |
| `MixinNodeExecutor` | STABLE | Node execution |
| `MixinNodeIdFromContract` | STABLE | Node ID from contract |
| `MixinNodeIntrospection` | STABLE | Node introspection |
| `MixinNodeLifecycle` | STABLE | Node lifecycle management |
| `MixinNodeSetup` | STABLE | Node setup |
| `MixinNodeTypeValidator` | STABLE | Node type validation |
| `MixinRequestResponseIntrospection` | STABLE | Request/response inspection |
| `MixinSensitiveFieldRedaction` | STABLE | Sensitive data redaction |
| `MixinSerializable` | STABLE | Serialization support |
| `MixinServiceRegistry` | STABLE | Service registry integration |
| `MixinToolExecution` | STABLE | Tool execution |
| `MixinWorkflowExecution` | STABLE | Workflow execution |
| `MixinYAMLSerialization` | STABLE | YAML serialization |

---

## omnibase_core.decorators Module

### Public Exports

```python
from omnibase_core.decorators import (
    # Error handling decorators
    io_error_handling,
    standard_error_handling,
    validation_error_handling,

    # Pattern exclusion decorators
    allow_any_type,
    allow_dict_str_any,
    allow_legacy_pattern,
    allow_mixed_types,
    exclude_from_onex_standards,
)
```

| Decorator | Stability | Purpose |
|-----------|-----------|---------|
| `standard_error_handling` | STABLE | Eliminates try/catch boilerplate |
| `io_error_handling` | STABLE | I/O-specific error handling |
| `validation_error_handling` | STABLE | Validation error handling |
| `allow_any_type` | STABLE | Exclude from `Any` type checks |
| `allow_dict_str_any` | STABLE | Exclude from dict[str, Any] checks |
| `allow_legacy_pattern` | STABLE | Mark legitimate legacy patterns |
| `allow_mixed_types` | STABLE | Allow mixed type patterns |
| `exclude_from_onex_standards` | STABLE | Exclude from ONEX standard checks |

---

## omnibase_core.validation Module

### Public Exports

```python
from omnibase_core.validation import (
    # Core classes
    CircularImportValidator,
    CircularImportValidationResult,
    ModelValidationResult,
    ServiceValidationSuite,
    ModelContractValidationResult,
    ModelModuleImportResult,
    ServiceProtocolAuditor,
    ModelProtocolInfo,
    ServiceContractValidator,

    # Enums
    EnumImportStatus,

    # Exceptions
    ExceptionConfigurationError,
    ExceptionInputValidationError,
    ExceptionValidationFrameworkError,

    # Main validation functions
    validate_all,
    validate_architecture,
    validate_contracts,
    validate_patterns,
    validate_union_usage,

    # Detailed validation functions
    validate_architecture_directory,
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_one_model_per_file,
    validate_patterns_directory,
    validate_patterns_file,
    validate_union_usage_directory,
    validate_union_usage_file,
    validate_yaml_file,
)
```

---

## omnibase_core.models Module

### Submodule Organization

The models module is organized by domain. Import from specific submodules:

```python
# Container models (DI container)
from omnibase_core.models.container import (
    ModelONEXContainer,
    ModelServiceRegistration,
    ModelServiceInstance,
    ModelServiceMetadata,
    create_model_onex_container,
    get_model_onex_container,
)

# Common models
from omnibase_core.models.common import (
    ModelErrorContext,
    ModelValidationResult,
    ModelValidationIssue,
    ModelSchemaValue,
)

# Error models
from omnibase_core.models.errors import ModelOnexError

# Event models
from omnibase_core.models.events import (
    ModelEventPublishIntent,
    ModelIntentExecutionResult,
    TOPIC_EVENT_PUBLISH_INTENT,
)

# Core models
from omnibase_core.models.core import (
    ModelResultAccessor,
    ModelLogContext,
    ModelOnexEnvelope,
)

# Contract models
from omnibase_core.models.contracts import (
    ModelContractBase,
    ModelContractCompute,
    ModelContractEffect,
    ModelContractReducer,
    ModelContractOrchestrator,
)
```

### CRITICAL: Container Type Distinction

**ModelONEXContainer vs ModelContainer[T]**

| Type | Location | Purpose | Use in Node `__init__` |
|------|----------|---------|------------------------|
| `ModelONEXContainer` | `models.container.model_onex_container` | Dependency injection container | **ALWAYS** |
| `ModelContainer[T]` | `models.core.model_container` | Generic value wrapper | **NEVER** |

```python
# CORRECT - Use ModelONEXContainer for DI
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

# WRONG - ModelContainer is for wrapping values, not DI
from omnibase_core.models.core.model_container import ModelContainer  # NOT for nodes!
```

---

## Consumer Repositories

### Identified Consumers

| Repository | Relationship | Import Dependencies |
|------------|--------------|---------------------|
| `omnibase_spi` | SPI depends on Core | Models, enums, validation |
| `omnibase_infra` | Implements SPI protocols | Core models, protocols |
| `omniintelligence` | AI/ML nodes | Node base classes, mixins |

### Dependency Direction (v0.3.6+)

```
omnibase_infra  ──implements──►  omnibase_spi  ──imports──►  omnibase_core
```

**CRITICAL**: Core MUST NOT import from SPI. The `omnibase_spi` dependency was removed in v0.3.6 as part of dependency inversion.

### Consumer Import Patterns

#### omnibase_spi Imports

```python
# Models SPI needs from Core
from omnibase_core.models.* import ...
from omnibase_core.enums import ...
from omnibase_core.validation import ...
```

#### omniintelligence Imports

```python
# AI/ML nodes using Core base classes
from omnibase_core.nodes import NodeCompute, NodeEffect
from omnibase_core.models.container import ModelONEXContainer
from omnibase_core.mixins import MixinEventBus, MixinHealthCheck
```

---

## Compatibility Shims Required

### v0.4.0 Migration Shims

#### NodeReducer/NodeOrchestrator Rename

| Old Name | New Name | Status | Shim Required |
|----------|----------|--------|---------------|
| `NodeReducerDeclarative` | `NodeReducer` | Removed in v0.4.0 | **YES** - alias needed |
| `NodeOrchestratorDeclarative` | `NodeOrchestrator` | Removed in v0.4.0 | **YES** - alias needed |

**Shim Implementation:**

```python
# In omnibase_core/nodes/__init__.py (if needed for backwards compat)
NodeReducerDeclarative = NodeReducer  # DEPRECATED alias
NodeOrchestratorDeclarative = NodeOrchestrator  # DEPRECATED alias
```

#### Protocol Migration Shims

```python
# In omnibase_core/mixins/__init__.py (already implemented)
ProtocolRegistryWithBus = ProtocolEventBusRegistry  # Legacy name alias
```

### Required Pre-Migration Verification

Before v0.4.0 release, verify these import paths work:

1. All `from omnibase_core.nodes import X` patterns
2. All `from omnibase_core.infrastructure import X` patterns
3. Consumer repos compile without errors
4. Deprecation warnings are emitted for legacy patterns

---

## Migration Notes

### v0.4.0 Changes Summary

1. **Node Class Renames**
   - `NodeReducerDeclarative` -> `NodeReducer`
   - `NodeOrchestratorDeclarative` -> `NodeOrchestrator`

2. **Import Path Changes**
   - All nodes: `from omnibase_core.nodes import NodeCompute, NodeReducer, ...`
   - I/O models exported from `omnibase_core.nodes`
   - Public enums exported from `omnibase_core.nodes`

3. **Removed Dependencies**
   - `omnibase_spi` removed as dependency (dependency inversion)
   - Core-native protocols in `omnibase_core.protocols`

4. **New Exports**
   - `ModelEffectTransaction` from `omnibase_core.nodes`
   - All public orchestrator/reducer enums from `omnibase_core.nodes`

### Migration Checklist

- [ ] Update imports from `NodeReducerDeclarative` to `NodeReducer`
- [ ] Update imports from `NodeOrchestratorDeclarative` to `NodeOrchestrator`
- [ ] Replace SPI protocol imports with Core-native protocols
- [ ] Verify `ProtocolEventBusRegistry` instead of `ProtocolRegistryWithBus`
- [ ] Update any direct file imports to use top-level module imports

---

## References

- [Node Building Guide](../guides/node-building/README.md)
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Migrating to Declarative Nodes](../guides/MIGRATING_TO_DECLARATIVE_NODES.md)
- [Container Types](CONTAINER_TYPES.md)
- [Node Class Hierarchy](NODE_CLASS_HIERARCHY.md)

---

**Document History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-09 | OMN-151 | Initial creation for v0.4.0 migration |
