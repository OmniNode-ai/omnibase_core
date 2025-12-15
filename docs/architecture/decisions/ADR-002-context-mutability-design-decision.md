# ADR-002: Context Mutability Design Decision

**Status**: Accepted
**Date**: 2025-12-15
**Deciders**: ONEX Framework Team
**Related**: ADR-001-protocol-based-di-architecture.md, model_workflow_state_snapshot.py, model_fsm_state_snapshot.py

---

## Context

The ONEX framework requires workflow and FSM state snapshots to be serializable and restorable for:
- Workflow replay and debugging
- State persistence across restarts
- Testing and verification
- Cross-service communication

These snapshots contain a `context` field that stores flexible runtime state as `dict[str, Any]`. The key design question is how to handle immutability for this context field, given Python's constraints.

### The Immutability Challenge

Python's `dict` type is fundamentally mutable. Even with Pydantic's `frozen=True` configuration:

```python
class ModelWorkflowStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    context: dict[str, Any] = Field(default_factory=dict)
```

While field reassignment is blocked (`snapshot.context = new_dict` raises error), the dict contents remain mutable:

```python
snapshot.context["key"] = "value"  # This STILL works with frozen=True!
```

### Design Options Considered

1. **MappingProxyType**: Use `types.MappingProxyType` for true immutability
2. **Deep Freeze**: Recursive freezing of nested structures
3. **Convention-Based**: Document contracts, trust developers
4. **Custom Immutable Dict**: Create custom immutable dict type

---

## Decision

We adopt **Convention-Based Immutability** with comprehensive documentation for context fields in state snapshot models.

### Core Principles

1. **Contractual Immutability**: Document that context MUST NOT be mutated after snapshot creation
2. **Defensive Programming**: Provide helper methods for safe snapshot updates (`with_step_completed()`)
3. **Deep Copy Guidance**: Document when and how to create isolated copies
4. **PII Awareness**: Provide sanitization utilities for safe logging/persistence

### Implementation Pattern

```python
class ModelWorkflowStateSnapshot(BaseModel):
    """
    Immutability Contract:
        - **Guaranteed immutable**: workflow_id (UUID), current_step_index (int), etc.
        - **Contractually immutable**: context (dict) - contents can be modified but MUST NOT be
        - Field reassignment is blocked by frozen=True
        - Workflow executors MUST create new snapshots rather than mutating existing ones
    """
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    context: dict[str, Any] = Field(default_factory=dict)

    def with_step_completed(self, step_id: UUID, *, new_context: dict | None = None):
        """Create new snapshot with updated state - preserves immutability contract."""
        updated_context = {**self.context, **(new_context or {})}
        return ModelWorkflowStateSnapshot(
            workflow_id=self.workflow_id,
            current_step_index=self.current_step_index + 1,
            completed_step_ids=(*self.completed_step_ids, step_id),
            context=updated_context,  # New dict, not mutation
        )
```

---

## Rationale

### Why Not MappingProxyType?

**Considered**:
```python
from types import MappingProxyType
context: MappingProxyType = Field(default_factory=lambda: MappingProxyType({}))
```

**Rejected Because**:
- **Serialization Complexity**: MappingProxyType is not JSON-serializable by default
- **Pydantic Incompatibility**: Requires custom validators and serializers
- **Nested Mutability**: Only protects the top-level dict; nested dicts remain mutable
- **API Friction**: All context manipulation requires explicit dict creation
- **Type Annotation Issues**: Generic type support is limited

### Why Not Deep Freeze?

**Considered**: Recursively freeze all nested structures using custom frozen types

**Rejected Because**:
- **Performance Overhead**: Deep traversal on every snapshot creation
- **Type Complexity**: Need frozen versions of list, dict, set, etc.
- **Compatibility Issues**: Third-party code may not handle frozen types
- **Overkill**: Most context usage is read-only after creation

### Why Not Custom Immutable Dict?

**Considered**: Create `ImmutableDict` class with `__setitem__` raising exceptions

**Rejected Because**:
- **Maintenance Burden**: Need to handle all dict operations correctly
- **Ecosystem Friction**: Type checkers and tools expect standard dict
- **Partial Solution**: Still doesn't solve nested mutability
- **Complexity**: Simple use case doesn't justify custom collection type

### Why Convention-Based Works

1. **Developer Trust**: ONEX developers understand immutability contracts
2. **Clear Documentation**: Comprehensive docstrings and warnings
3. **Safe Patterns**: Helper methods guide correct usage
4. **Testing Coverage**: Tests verify snapshot behavior
5. **Simplicity**: No complex type machinery to maintain

---

## Consequences

### Positive

- **Simplicity**: Standard Python dict with clear documentation
- **Performance**: No overhead from defensive copying or proxies
- **Compatibility**: Works with all JSON serializers, Pydantic, pytest-xdist
- **Flexibility**: Context can store any serializable value
- **Testability**: Easy to create test fixtures and verify behavior

### Neutral

- **Developer Discipline**: Requires developers to follow documented contracts
- **Code Review**: Mutations should be caught in review, not at runtime

### Negative

- **No Runtime Enforcement**: Accidental mutation won't raise exceptions
- **Debug Difficulty**: Mutation bugs may be subtle and hard to trace
- **Contract Violations**: Malicious or careless code can break invariants

### Mitigations for Negative Consequences

1. **Comprehensive Documentation**: Module, class, and method docstrings explain contracts
2. **Helper Methods**: `with_step_completed()`, `with_step_failed()` make correct usage easy
3. **PII Sanitization**: `sanitize_context_for_logging()` reduces risk of sensitive data exposure
4. **Size Validation**: `validate_context_size()` prevents performance issues
5. **Deep Copy Guidance**: Documented pattern for creating isolated copies when needed:
   ```python
   import copy
   isolated_snapshot = copy.deepcopy(node.snapshot_workflow_state())
   ```

---

## Implementation Notes

### Affected Models

- `ModelWorkflowStateSnapshot` (workflow execution state)
- `ModelFSMStateSnapshot` (FSM state machine state)
- Any future snapshot models with context fields

### Thread Safety Implications

The convention-based approach has thread safety implications:

- **Safe**: Passing snapshots between threads for read-only access
- **Safe**: Serializing via `model_dump()`
- **Unsafe**: Mutating context contents (violates contract AND causes race conditions)

Documentation explicitly warns about thread safety in all affected methods.

### Testing Considerations

Tests should verify:
1. Field reassignment is blocked (`frozen=True` works)
2. Helper methods create new instances (not mutations)
3. Serialization/deserialization roundtrips work correctly
4. pytest-xdist parallel execution works (`from_attributes=True`)

---

## Alternatives Record

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| MappingProxyType | True immutability at top level | Serialization issues, nested still mutable | Rejected |
| Deep Freeze | Complete immutability | Performance, complexity, compatibility | Rejected |
| Custom ImmutableDict | Runtime enforcement | Maintenance, ecosystem friction | Rejected |
| Convention-Based | Simple, performant, compatible | Requires developer discipline | **Accepted** |

---

## References

### Internal Documentation

- [CLAUDE.md](../../../CLAUDE.md) - Section "Pydantic from_attributes=True for Value Objects"
- [Threading Guide](../../guides/THREADING.md) - Thread safety patterns
- [model_workflow_state_snapshot.py](../../../src/omnibase_core/models/workflow/execution/model_workflow_state_snapshot.py) - Primary implementation

### External References

- [Pydantic Frozen Models](https://docs.pydantic.dev/latest/concepts/models/#model-configuration)
- [Python MappingProxyType](https://docs.python.org/3/library/types.html#types.MappingProxyType)
- [Immutability in Python](https://realpython.com/python-mutable-vs-immutable-types/)

---

## Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-15 | Initial ADR documenting context mutability design | ONEX Team |

---

**Next Review**: 2026-03-15 or when significant issues arise with convention-based approach
