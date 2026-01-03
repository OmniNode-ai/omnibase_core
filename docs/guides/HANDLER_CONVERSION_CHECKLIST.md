# Handler Conversion Checklist

**Purpose**: Track the conversion of mixins to composition-based handlers for the ONEX pipeline.

**Related Ticket**: OMN-1112 - First Pure Handler Conversions

**Last Updated**: 2026-01-02

---

## Status Legend

| Status | Meaning |
|--------|---------|
| Completed | Handler implemented and tested |
| In Progress | Currently being converted |
| Planned | Scheduled for conversion |
| Not Planned | Will remain as mixin (with reason) |

---

## Conversion Summary

| Phase | Status | Handlers | Notes |
|-------|--------|----------|-------|
| **Phase 1** | Completed | 2/2 | Performance/Resilience stubs |
| **Phase 2** | Planned | 0/3 | Core resilience patterns |
| **Phase 3** | Planned | 0/8 | Event & Discovery systems |
| **Phase 4** | Planned | 0/6 | Execution patterns |
| **Phase 5** | Planned | 0/5 | Contract & State management |
| **Phase 6** | Planned | 0/4 | Serialization patterns |
| **Phase 7** | Planned | 0/6 | Utility patterns |

**Total Progress**: 2/34 mixins converted (6%)

---

## Phase 1: Performance & Resilience Stubs (Completed)

First conversions demonstrating the mixin-to-handler pattern with stub implementations.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinMetrics` | `ModelCapabilityMetrics` | Completed | OMN-1112 | First conversion - stub impl |
| `MixinCaching` | `ModelCapabilityCaching` | Completed | OMN-1112 | First conversion - stub impl |

### MixinMetrics -> ModelCapabilityMetrics

- [x] Handler design documented
- [x] TDD tests written
- [x] Handler implemented
- [x] All original mixin tests pass
- [x] Handler works standalone (no inheritance)
- [x] Added to `pipeline/handlers/__init__.py`
- [x] Ticket closed: OMN-1112

**Location**: `src/omnibase_core/pipeline/handlers/model_capability_metrics.py`

### MixinCaching -> ModelCapabilityCaching

- [x] Handler design documented
- [x] TDD tests written
- [x] Handler implemented
- [x] All original mixin tests pass
- [x] Handler works standalone (no inheritance)
- [x] Added to `pipeline/handlers/__init__.py`
- [x] Ticket closed: OMN-1112

**Location**: `src/omnibase_core/pipeline/handlers/model_capability_caching.py`

---

## Phase 2: Core Resilience Patterns (Planned)

Production-ready resilience patterns with full implementations.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinHealthCheck` | `ModelCapabilityHealthCheck` | Planned | - | HTTP, Kafka, PostgreSQL, Redis checks |
| `MixinFailFast` | `ModelCapabilityFailFast` | Planned | - | Circuit breaker integration |
| (New) | `ModelCapabilityRetry` | Planned | - | Exponential backoff, jitter |
| (New) | `ModelCapabilityCircuitBreaker` | Planned | - | Failure threshold, recovery |

### MixinHealthCheck -> ModelCapabilityHealthCheck

- [ ] Handler design documented
- [ ] TDD tests written
- [ ] Handler implemented
- [ ] All original mixin tests pass
- [ ] Handler works standalone (no inheritance)
- [ ] Added to `pipeline/handlers/__init__.py`
- [ ] Utility functions migrated (`check_postgresql_health`, etc.)
- [ ] Ticket created and closed

**Original Location**: `src/omnibase_core/mixins/mixin_health_check.py`

### MixinFailFast -> ModelCapabilityFailFast

- [ ] Handler design documented
- [ ] TDD tests written
- [ ] Handler implemented
- [ ] All original mixin tests pass
- [ ] Handler works standalone (no inheritance)
- [ ] Added to `pipeline/handlers/__init__.py`
- [ ] Ticket created and closed

**Original Location**: `src/omnibase_core/mixins/mixin_fail_fast.py`

---

## Phase 3: Event & Discovery Systems (Planned)

Event-driven architecture and service discovery patterns.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinEventBus` | `ModelCapabilityEventBus` | Planned | - | Core event bus integration |
| `MixinEventDrivenNode` | `ModelCapabilityEventDrivenNode` | Planned | - | Event-driven node pattern |
| `MixinEventHandler` | `ModelCapabilityEventHandler` | Planned | - | Event handling |
| `MixinEventListener` | `ModelCapabilityEventListener` | Planned | - | Event subscription |
| `MixinDiscoveryResponder` | `ModelCapabilityDiscoveryResponder` | Planned | - | Discovery response |
| `MixinDiscovery` | `ModelCapabilityDiscovery` | Planned | - | Service discovery |
| `MixinDebugDiscoveryLogging` | `ModelCapabilityDebugDiscoveryLogging` | Planned | - | Debug logging |
| `MixinServiceRegistry` | `ModelCapabilityServiceRegistry` | Planned | - | Service registration |

---

## Phase 4: Execution Patterns (Planned)

Node execution and lifecycle patterns.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinComputeExecution` | `ModelCapabilityComputeExecution` | Planned | - | Compute node execution |
| `MixinEffectExecution` | `ModelCapabilityEffectExecution` | Planned | - | Effect node execution |
| `MixinFSMExecution` | `ModelCapabilityFSMExecution` | Planned | - | FSM-based execution |
| `MixinHybridExecution` | `ModelCapabilityHybridExecution` | Planned | - | Hybrid sync/async |
| `MixinNodeExecutor` | `ModelCapabilityNodeExecutor` | Planned | - | Generic node execution |
| `MixinNodeLifecycle` | `ModelCapabilityNodeLifecycle` | Planned | - | Lifecycle management |

---

## Phase 5: Contract & State Management (Planned)

Contract metadata and state management patterns.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinContractMetadata` | `ModelCapabilityContractMetadata` | Planned | - | Contract metadata extraction |
| `MixinContractStateReducer` | `ModelCapabilityContractStateReducer` | Planned | - | State reduction |
| `MixinIntentPublisher` | `ModelCapabilityIntentPublisher` | Planned | - | Intent publishing |
| `MixinNodeIdFromContract` | `ModelCapabilityNodeIdFromContract` | Planned | - | Node ID extraction |
| `MixinNodeSetup` | `ModelCapabilityNodeSetup` | Planned | - | Node initialization |

---

## Phase 6: Serialization Patterns (Planned)

Data serialization and transformation patterns.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinCanonicalYAMLSerializer` | `ModelCapabilityCanonicalSerializer` | Planned | - | Canonical YAML |
| `MixinYAMLSerialization` | `ModelCapabilityYAMLSerialization` | Planned | - | YAML serialization |
| `MixinSerializable` | `ModelCapabilitySerializable` | Planned | - | Generic serialization |
| `MixinHashComputation` | `ModelCapabilityHashComputation` | Planned | - | Hash computation |

---

## Phase 7: Utility & Specialized Patterns (Planned)

Utility mixins and specialized patterns.

| Mixin | Handler | Status | Ticket | Notes |
|-------|---------|--------|--------|-------|
| `MixinWorkflowExecution` | `ModelCapabilityWorkflowExecution` | Planned | - | Workflow orchestration |
| `MixinToolExecution` | `ModelCapabilityToolExecution` | Planned | - | Tool execution |
| `MixinLazyEvaluation` | `ModelCapabilityLazyEvaluation` | Planned | - | Lazy evaluation |
| `MixinLazyValue` | `ModelCapabilityLazyValue` | Planned | - | Lazy value wrapper |
| `MixinSensitiveFieldRedaction` | `ModelCapabilityRedaction` | Planned | - | PII/secret redaction |
| `MixinCLIHandler` | `ModelCapabilityCLIHandler` | Planned | - | CLI integration |

---

## Introspection Patterns (Not Planned)

These mixins are tightly coupled to node introspection protocols and will remain as mixins.

| Mixin | Status | Reason |
|-------|--------|--------|
| `MixinNodeIntrospection` | Not Planned | Core protocol implementation |
| `MixinIntrospectionPublisher` | Not Planned | Event bus protocol coupling |
| `MixinIntrospectFromContract` | Not Planned | Contract introspection protocol |
| `MixinRequestResponseIntrospection` | Not Planned | Request/Response protocol coupling |
| `MixinNodeTypeValidator` | Not Planned | Core validation protocol |

---

## Validation Commands

### Run Handler Tests

```bash
# Run all handler tests
poetry run pytest tests/unit/pipeline/handlers/ -v

# Run specific handler tests
poetry run pytest tests/unit/pipeline/handlers/test_capability_metrics.py -v
poetry run pytest tests/unit/pipeline/handlers/test_capability_caching.py -v
```

### Verify No Mixin Dependencies in Handlers

```bash
# Ensure handlers don't inherit from mixins
grep -r "MixinMetrics" src/omnibase_core/pipeline/handlers/
grep -r "MixinCaching" src/omnibase_core/pipeline/handlers/

# Should return no results - handlers should be standalone
```

### Check Handler Exports

```bash
# Verify handlers are exported
grep -r "ModelCapability" src/omnibase_core/pipeline/handlers/__init__.py
```

### Full Validation Suite

```bash
# Run all tests with coverage
poetry run pytest tests/ --cov=src/omnibase_core/pipeline/handlers -v

# Type checking
poetry run mypy src/omnibase_core/pipeline/handlers/
```

---

## Exit Criteria for Full Migration

### Per-Handler Criteria

- [ ] Handler design documented in this checklist
- [ ] TDD tests written before implementation
- [ ] Handler implemented without mixin inheritance
- [ ] All original mixin functionality preserved
- [ ] Handler works with composition (injected into nodes)
- [ ] Added to `pipeline/handlers/__init__.py`
- [ ] Documentation updated
- [ ] Linear ticket created and closed

### Full Migration Criteria

- [ ] All planned mixins converted to handlers
- [ ] No mixin inheritance in handler implementations
- [ ] All handler tests pass with >80% coverage
- [ ] Documentation complete (this file + API docs)
- [ ] Migration guide written for downstream consumers
- [ ] Deprecation warnings added to original mixins
- [ ] Performance benchmarks show no regression

---

## Architecture Guidelines

### Handler Design Principles

1. **Composition over Inheritance**: Handlers are injected, not inherited
2. **Single Responsibility**: Each handler provides one capability
3. **Stateless Where Possible**: Prefer stateless handlers for thread safety
4. **Protocol Compliance**: Implement capability protocols
5. **Testable in Isolation**: No node dependencies for unit tests

### Handler Structure

```python
from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr


class ModelCapabilityExample(BaseModel):
    """
    Example capability handler.

    Provides [capability description] for ONEX nodes.
    """

    model_config = ConfigDict(
        frozen=False,  # or True if stateless
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    # Configuration fields
    enabled: bool = True

    # Internal state (if needed) - use PrivateAttr for non-serialized state
    _internal_state: dict[str, Any] = PrivateAttr(default_factory=dict)

    def capability_method(self, input_data: Any) -> Any:
        """Implement capability logic."""
        pass
```

### Handler Registration

Handlers are registered in `pipeline/handlers/__init__.py`:

```python
from omnibase_core.pipeline.handlers.model_capability_example import (
    ModelCapabilityExample,
)

__all__ = [
    "ModelCapabilityExample",
    # ... other handlers
]
```

---

## Related Documentation

- [**HANDLER_CONVERSION_GUIDE.md**](./HANDLER_CONVERSION_GUIDE.md) - Step-by-step conversion guide with examples
- [PIPELINE_HOOK_REGISTRY.md](./PIPELINE_HOOK_REGISTRY.md) - Pipeline hook system
- [MIXINS_TO_HANDLERS_REFACTOR.md](../architecture/MIXINS_TO_HANDLERS_REFACTOR.md) - Architectural vision
- [MIXIN_SUBCONTRACT_MAPPING.md](./MIXIN_SUBCONTRACT_MAPPING.md) - Mixin to subcontract mapping
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node architecture
- [Node Building Guide](./node-building/README.md) - Building ONEX nodes
