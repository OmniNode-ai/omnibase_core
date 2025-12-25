# ModelAction Typed Payloads

**Issue**: OMN-1008 - Replace `dict[str, Any]` in ModelAction with typed payloads

## Summary

This document explains the typed payload system for `ModelAction` and the design decision to leverage the existing semantic-category-based payload infrastructure rather than creating new EnumActionType-based payloads.

## Background

### The Problem

The original `ModelAction` class had an untyped payload field:

```python
class ModelAction(BaseModel):
    payload: dict[str, Any]  # Untyped - loses type safety
```

This pattern:
- Loses compile-time type checking
- Requires runtime validation
- Makes IDE autocomplete ineffective
- Increases risk of runtime errors

### Existing Infrastructure

The codebase already has a comprehensive typed payload system at `omnibase_core.models.core.model_action_payload_*`:

| Payload Type | Purpose | Example Actions |
|-------------|---------|-----------------|
| `ModelLifecycleActionPayload` | Node lifecycle management | health_check, initialize, shutdown |
| `ModelOperationalActionPayload` | Core operations | process, execute, run |
| `ModelDataActionPayload` | Data CRUD operations | read, write, create, update, delete |
| `ModelValidationActionPayload` | Validation operations | validate, verify, check |
| `ModelManagementActionPayload` | Administrative operations | configure, deploy, migrate |
| `ModelTransformationActionPayload` | Data transformation | transform, convert, parse |
| `ModelMonitoringActionPayload` | Monitoring/querying | monitor, collect, report |
| `ModelRegistryActionPayload` | Registry operations | register, unregister, discover |
| `ModelFilesystemActionPayload` | Filesystem operations | scan, watch, sync |
| `ModelCustomActionPayload` | Custom operations | any custom operation |

## Design Decision

### Approach: Use Existing Semantic Payloads

**Decision**: Use the existing `SpecificActionPayload` union type directly, rather than creating new COMPUTE/EFFECT/REDUCE/ORCHESTRATE-specific payloads.

### Why Semantic Categories are Superior

The existing payloads are organized by **what the operation does** (semantic meaning), not by **which node type executes it** (architectural role). This is the correct design because:

1. **Node types handle multiple operation types**:
   - A COMPUTE node might perform "transform" (transformation), "validate" (validation), or "aggregate" (operational)
   - An EFFECT node might perform "read" (data), "sync" (filesystem), or "register" (registry)

2. **Semantic payloads are more precise**:
   - `ModelDataActionPayload` has fields like `target_path`, `filters`, `limit`
   - `ModelTransformationActionPayload` has fields like `input_format`, `output_format`, `transformation_rules`
   - These fields directly match the operation being performed

3. **Code reuse**: The same payload type can be used across different node types performing similar operations

### Alternative Considered: Node-Type Payloads

Creating payloads like `ComputeActionPayload`, `EffectActionPayload`, etc. was considered but rejected because:

- Would duplicate field definitions across payloads
- Would lose semantic precision (what does a "compute payload" even contain?)
- Would require complex mapping logic anyway
- Would not leverage existing infrastructure

## Implementation

### Type Alias

A type alias `ActionPayloadType` is provided for use in `ModelAction`:

```python
from omnibase_core.models.orchestrator.payloads import ActionPayloadType

# In ModelAction (future):
class ModelAction(BaseModel):
    payload: ActionPayloadType  # Typed discriminated union
```

### Factory Functions

Two factory functions are provided:

1. **`create_action_payload()`** - Bridges EnumActionType with semantic payloads:

```python
from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.orchestrator.payloads import create_action_payload

# Create a typed payload for an EFFECT action
payload = create_action_payload(
    action_type=EnumActionType.EFFECT,
    semantic_action="read",
    target_path="/data/users.json",
    filters={"active": True},
)

# payload is now ModelDataActionPayload with full type safety
assert payload.target_path == "/data/users.json"
```

2. **`get_recommended_payloads_for_action_type()`** - Returns commonly used payloads for each action type:

```python
from omnibase_core.models.orchestrator.payloads import get_recommended_payloads_for_action_type

payloads = get_recommended_payloads_for_action_type(EnumActionType.COMPUTE)
# Returns [ModelTransformationActionPayload, ModelValidationActionPayload, ...]
```

### Payload Type Lookup

For validation or type checking, use `get_payload_type_for_semantic_action()`:

```python
from omnibase_core.models.orchestrator.payloads.model_action_typed_payload import (
    get_payload_type_for_semantic_action,
)

# Get expected type for a semantic action
payload_type = get_payload_type_for_semantic_action("read")
assert payload_type is ModelDataActionPayload
```

## Usage Guide

### Common Patterns by EnumActionType

#### COMPUTE Actions

```python
# Transformation
payload = create_action_payload(
    action_type=EnumActionType.COMPUTE,
    semantic_action="transform",
    input_format="json",
    output_format="yaml",
    transformation_rules=["flatten", "normalize"],
)

# Validation
payload = create_action_payload(
    action_type=EnumActionType.COMPUTE,
    semantic_action="validate",
    validation_rules=["schema", "business_rules"],
    strict_mode=True,
)
```

#### EFFECT Actions

```python
# Data operations
payload = create_action_payload(
    action_type=EnumActionType.EFFECT,
    semantic_action="read",
    target_path="/api/users",
    filters={"role": "admin"},
    limit=100,
)

# Filesystem operations
payload = create_action_payload(
    action_type=EnumActionType.EFFECT,
    semantic_action="sync",
    path="/data/backup",
    recursive=True,
)
```

#### REDUCE Actions

```python
# Aggregation
payload = create_action_payload(
    action_type=EnumActionType.REDUCE,
    semantic_action="aggregate",
    parameters={"method": "sum", "field": "amount"},
)

# Monitoring
payload = create_action_payload(
    action_type=EnumActionType.REDUCE,
    semantic_action="collect",
    metrics=["cpu_usage", "memory_usage"],
    interval_seconds=60,
)
```

#### ORCHESTRATE Actions

```python
# Management
payload = create_action_payload(
    action_type=EnumActionType.ORCHESTRATE,
    semantic_action="deploy",
    environment="production",
    dry_run=True,
)
```

## File Locations

### Source Files

- **Type alias and factory**: `/src/omnibase_core/models/orchestrator/payloads/model_action_typed_payload.py`
- **Package init**: `/src/omnibase_core/models/orchestrator/payloads/__init__.py`
- **Base payloads**: `/src/omnibase_core/models/core/model_action_payload_*.py`

### Test Files

- **Integration tests**: `/tests/unit/models/orchestrator/payloads/test_model_action_typed_payload.py`
- **Base payload tests**: `/tests/unit/models/core/test_model_action_payload_types.py`

## Migration Path

### Phase 1: Add Typed Payload Support (Current)

- Create `ActionPayloadType` type alias
- Add factory functions for payload creation
- Document usage patterns

### Phase 2: Update ModelAction (Separate Task)

- Replace `payload: dict[str, Any]` with `payload: ActionPayloadType`
- Update all callers to use typed payloads
- Add migration utilities if needed

### Phase 3: Deprecate Untyped Usage

- Add deprecation warnings for dict payloads
- Update all existing code
- Remove legacy support

## Semantic Action Reference

| Semantic Action | Payload Type | Category |
|-----------------|--------------|----------|
| read, write, create, update, delete, search, query | ModelDataActionPayload | Data |
| scan, watch, sync | ModelFilesystemActionPayload | Filesystem |
| register, unregister, discover | ModelRegistryActionPayload | Registry |
| health_check, initialize, shutdown, start, stop | ModelLifecycleActionPayload | Lifecycle |
| validate, verify, check, test | ModelValidationActionPayload | Validation |
| transform, convert, parse, serialize | ModelTransformationActionPayload | Transformation |
| configure, deploy, migrate | ModelManagementActionPayload | Management |
| monitor, collect, report, alert | ModelMonitoringActionPayload | Monitoring |
| custom | ModelCustomActionPayload | Custom |
| (any other) | ModelOperationalActionPayload | Operational |

## Related Documents

- [ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md)
- [dict[str, Any] Prevention Guide](./DICT_STR_ANY_PREVENTION.md)
- [Container Types](./CONTAINER_TYPES.md)
