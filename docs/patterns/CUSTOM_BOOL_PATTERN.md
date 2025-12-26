# Custom `__bool__` Pattern for Result Models

> **Version**: 1.0.0
> **Last Updated**: 2025-12-26
> **Status**: Complete
> **Purpose**: Document the custom `__bool__` pattern for Pydantic result models
> **Target Audience**: Node developers implementing result models

---

## Table of Contents

1. [Overview](#overview)
2. [When to Use This Pattern](#when-to-use-this-pattern)
3. [Implementation Guide](#implementation-guide)
4. [Pattern Categories](#pattern-categories)
5. [Known Implementations](#known-implementations)
6. [Docstring Requirements](#docstring-requirements)
7. [Common Pitfalls](#common-pitfalls)
8. [Testing](#testing)

---

## Overview

Result models may override `__bool__` to enable idiomatic Python conditional checks. This differs from standard Pydantic behavior where `bool(model)` always returns `True` regardless of the model's contents.

### Why This Pattern Exists

By default, Pydantic models are always truthy:

```python
# Default Pydantic behavior
result = ModelSomeResult(success=False, data=None)
if result:  # Always True - the model instance exists!
    process(result)  # This always executes, even for "failed" results
```

With custom `__bool__`, models can express semantic truthiness:

```python
# Custom __bool__ behavior
result = reducer.reduce(state, event)
if result:  # True only if there are intents to process
    execute_intents(result.intents)
```

### Key Principle

The `__bool__` method should return `True` when the result represents a **meaningful, actionable, or successful** state, and `False` otherwise.

---

## When to Use This Pattern

### ✅ Use This Pattern For

| Scenario | Example | `__bool__` Returns |
|----------|---------|-------------------|
| **Success/failure results** | `ModelResult[T, E]` | `self.success` |
| **Optional value containers** | `ModelOptionalInt` | `self.is_some()` |
| **Match results** | `ModelCategoryMatchResult` | `self.matched` |
| **Capability checks** | `ModelCanHandleResult` | `self.can_handle` |
| **Reducer execution results** | `ModelReducerExecutionResult` | `self.has_intents` |
| **Containers with content** | `ModelEnvelopePayload` | `any(self.fields)` |

### ❌ Do NOT Use This Pattern For

| Scenario | Reason |
|----------|--------|
| **Data transfer objects** | No semantic "success" concept |
| **Configuration models** | Always valid after construction |
| **Entity models** | Existence != truthiness |
| **Input/output state models** | Content varies, no boolean semantic |

---

## Implementation Guide

### Basic Pattern

```python
from pydantic import BaseModel, Field


class ModelOperationResult(BaseModel):
    """Result of an operation with custom truthiness.

    Warning:
        This model overrides ``__bool__`` to return the value of ``success``.
        Unlike standard Pydantic models, ``bool(instance)`` may return ``False``
        even when the instance exists. Always check explicitly if you need to
        distinguish between "no result" and "failed result".
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str | None = Field(default=None, description="Optional message")

    def __bool__(self) -> bool:
        """Return True if operation succeeded.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. Here, ``bool(result)`` returns the value
            of ``success``, enabling idiomatic conditional checks.

        Returns:
            bool: The value of the ``success`` field.

        Example:
            >>> result = ModelOperationResult(success=True)
            >>> if result:
            ...     print("Operation succeeded")
            Operation succeeded

            >>> failed = ModelOperationResult(success=False, message="Error")
            >>> if not failed:
            ...     print(f"Failed: {failed.message}")
            Failed: Error
        """
        return self.success
```

### Optional Container Pattern

```python
class ModelOptionalValue(BaseModel):
    """Container for an optional value.

    Warning:
        This model overrides ``__bool__`` to check value presence.
        ``bool(instance)`` returns ``False`` when ``value`` is ``None``.
    """

    value: int | None = Field(default=None)

    def __bool__(self) -> bool:
        """Return True if value is present (not None).

        Warning:
            Differs from standard Pydantic behavior. Returns ``False``
            when ``value`` is ``None``, enabling idiomatic presence checks.

        Returns:
            bool: True if value is not None, False otherwise.
        """
        return self.value is not None
```

### Composite Container Pattern

```python
class ModelPayload(BaseModel):
    """Container with multiple optional fields.

    Warning:
        This model overrides ``__bool__`` to check if any fields have data.
        An "empty" payload returns ``False`` from ``bool(instance)``.
    """

    event_type: str | None = None
    source: str | None = None
    data: dict[str, object] = Field(default_factory=dict)

    def __bool__(self) -> bool:
        """Return True if any payload fields have data.

        Warning:
            Unlike standard Pydantic models, an "empty" instance returns
            ``False``. Use this for idiomatic emptiness checks.

        Returns:
            bool: True if any field has data, False if all are empty/None.
        """
        return (
            self.event_type is not None
            or self.source is not None
            or bool(self.data)
        )
```

---

## Pattern Categories

### 1. Simple Flag Delegation

Directly return a boolean field's value.

```python
def __bool__(self) -> bool:
    return self.can_handle
```

**Use when**: Model has a single primary boolean indicator.

### 2. Success/Error Status

Return success state for Result-type models.

```python
def __bool__(self) -> bool:
    return self.success
```

**Use when**: Model represents operation outcome (success/failure).

### 3. Value Presence Check

Return whether an optional value exists.

```python
def __bool__(self) -> bool:
    return self.value is not None
```

**Use when**: Model wraps an optional value (Option/Maybe pattern).

### 4. Collection Emptiness

Return whether a collection has items.

```python
def __bool__(self) -> bool:
    return bool(self.items)
```

**Use when**: Model wraps a collection (list, dict, set).

### 5. Composite State Check

Check multiple fields for meaningful content using short-circuit evaluation.

```python
def __bool__(self) -> bool:
    # Use short-circuit evaluation for efficiency - stops at first True
    return (
        self.field_a is not None
        or self.field_b is not None
        or bool(self.collection)
    )
```

**Use when**: Model has multiple optional fields that indicate "emptiness".

**Note**: Prefer `or` chaining over `any([...])` for efficiency. The `or` operator
short-circuits (stops evaluating after the first `True`), while `any([...])`
with a list literal evaluates all conditions before checking.

---

## Known Implementations

### In omnibase_core

| Model | File | `__bool__` Returns |
|-------|------|-------------------|
| `ModelCanHandleResult` | `models/configuration/model_can_handle_result.py` | `self.can_handle` |
| `ModelResult[T, E]` | `models/infrastructure/model_result.py` | `self.success` |
| `ModelEnvelopePayload` | `models/common/model_envelope_payload.py` | `any(fields)` |
| `ModelQueryParameters` | `models/common/model_query_parameters.py` | `bool(self.items)` |
| `ModelOptionalInt` | `models/common/model_optional_int.py` | `self.is_some()` |
| `ModelOptionalString` | `models/core/model_optional_string.py` | `self.has_value()` |

### In omnibase_infra (External)

| Model | `__bool__` Returns |
|-------|-------------------|
| `ModelReducerExecutionResult` | `self.has_intents` |
| `ModelCategoryMatchResult` | `self.matched` |

---

## Docstring Requirements

### Class Docstring

Every model with custom `__bool__` **MUST** include a `Warning` section in the class docstring:

```python
class ModelMyResult(BaseModel):
    """Description of the model.

    Warning:
        This model overrides ``__bool__`` to return [specific behavior].
        Unlike standard Pydantic models, ``bool(instance)`` may return
        ``False`` even when the instance exists.
    """
```

### Method Docstring

The `__bool__` method **MUST** include:

1. **Brief description** of what it returns
2. **Warning section** explaining non-standard behavior
3. **Returns section** with type and description
4. **Example section** demonstrating usage (recommended)

```python
def __bool__(self) -> bool:
    """Return True if [condition].

    Warning:
        This differs from standard Pydantic behavior where ``bool(model)``
        always returns ``True``. [Explain specific behavior here].

    Returns:
        bool: [Description of what True/False mean].

    Example:
        >>> result = ModelMyResult(...)
        >>> if result:
        ...     print("Truthy case")
    """
    return self.some_condition
```

---

## Common Pitfalls

### ❌ Don't: Forget the Warning Docstring

```python
# WRONG - No warning about non-standard behavior
def __bool__(self) -> bool:
    return self.success
```

### ✅ Do: Always Include Warning

```python
# CORRECT - Documents non-standard behavior
def __bool__(self) -> bool:
    """Return True if operation succeeded.

    Warning:
        Unlike standard Pydantic models, ``bool(result)`` returns
        the ``success`` field value, not instance existence.
    """
    return self.success
```

---

### ❌ Don't: Use for Data Models

```python
# WRONG - UserProfile has no semantic "truthiness"
class UserProfile(BaseModel):
    name: str
    email: str

    def __bool__(self) -> bool:
        return bool(self.name)  # Confusing - what does False mean?
```

### ✅ Do: Use for Result Models

```python
# CORRECT - Clear semantic meaning
class UserLookupResult(BaseModel):
    found: bool
    user: UserProfile | None

    def __bool__(self) -> bool:
        """Return True if user was found."""
        return self.found
```

---

### ❌ Don't: Conflate None and False

```python
# Problematic - can't distinguish "not found" from "no search performed"
result = lookup_user(user_id)
if not result:
    # Is this "user not found" or "lookup failed"?
    handle_missing()
```

### ✅ Do: Consider Explicit Checks When Needed

```python
# When you need to distinguish states
result = lookup_user(user_id)
if result is None:
    handle_lookup_failure()
elif not result:
    handle_user_not_found()
else:
    process_user(result.user)
```

---

## Testing

### Test Both True and False Cases

```python
def test_model_bool_true_case() -> None:
    """Test that __bool__ returns True for successful result."""
    result = ModelOperationResult(success=True)
    assert bool(result) is True
    assert result  # Idiomatic check


def test_model_bool_false_case() -> None:
    """Test that __bool__ returns False for failed result."""
    result = ModelOperationResult(success=False)
    assert bool(result) is False
    assert not result  # Idiomatic check


def test_model_bool_in_conditional() -> None:
    """Test idiomatic usage in conditional."""
    success_result = ModelOperationResult(success=True)
    fail_result = ModelOperationResult(success=False)

    # These should work idiomatically
    if success_result:
        pass  # Expected path
    else:
        pytest.fail("Should have been truthy")

    if fail_result:
        pytest.fail("Should have been falsy")
```

### Test Edge Cases

```python
def test_model_bool_with_none_value() -> None:
    """Test __bool__ with None optional value."""
    empty = ModelOptionalInt(value=None)
    assert bool(empty) is False


def test_model_bool_with_zero_value() -> None:
    """Test __bool__ with zero (still a valid value)."""
    zero = ModelOptionalInt(value=0)
    assert bool(zero) is True  # 0 is a valid value, not None
```

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node types and result handling
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Result model patterns
- [Anti-Patterns](ANTI_PATTERNS.md) - What NOT to do

---

**Last Updated**: 2025-12-26 | **Version**: 1.0.0
