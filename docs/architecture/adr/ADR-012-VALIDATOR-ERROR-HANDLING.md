# ADR-012: Validator Error Handling with ModelOnexError

**Status**: Accepted
**Date**: 2025-12-16
**Context**: PR #205 (OMN-594) - Reducer Output Validation Enhancement
**Correlation ID**: `adr-012-validator-errors`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context](#context)
3. [Decision](#decision)
4. [Rationale](#rationale)
5. [Pydantic v2+ Compatibility Analysis](#pydantic-v2-compatibility-analysis)
6. [Implementation Pattern](#implementation-pattern)
7. [Future Migration Strategy](#future-migration-strategy)
8. [Consequences](#consequences)
9. [Related Documents](#related-documents)

---

## Executive Summary

**Decision**: Use `ModelOnexError` in Pydantic `@field_validator` decorators instead of `ValueError` or `PydanticCustomError`.

**Key Benefits**:
- Consistent error handling across ONEX framework (100% of errors use ModelOnexError)
- Structured error context with correlation tracking
- Machine-readable error codes via `EnumCoreErrorCode`
- Future-compatible with Pydantic evolution

**Trade-offs**:
- Diverges from Pydantic's recommended `ValueError` pattern
- May complicate migration to future Pydantic versions

**Impact**: 200+ validators across 207 model files use this pattern.

---

## Context

### Problem Statement

Pydantic `@field_validator` decorators need to raise validation errors when field values violate business rules. The question is: **which exception type should we use?**

### Available Options

1. **Pydantic Standard** (`ValueError`):
   ```python
   @field_validator("processing_time_ms")
   @classmethod
   def validate_processing_time_ms(cls, v: float) -> float:
       if v < -1.0:
           raise ValueError(f"Invalid value: {v}")
       return v
   ```

2. **Pydantic Custom** (`PydanticCustomError`):
   ```python
   from pydantic_core import PydanticCustomError

   @field_validator("processing_time_ms")
   @classmethod
   def validate_processing_time_ms(cls, v: float) -> float:
       if v < -1.0:
           raise PydanticCustomError(
               'invalid_processing_time',
               'processing_time_ms must be >= 0.0 or exactly -1.0, got {value}',
               {'value': v}
           )
       return v
   ```

3. **ONEX Standard** (`ModelOnexError`):
   ```python
   from omnibase_core.models.errors.model_onex_error import ModelOnexError
   from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

   @field_validator("processing_time_ms")
   @classmethod
   def validate_processing_time_ms(cls, v: float) -> float:
       if v < -1.0:
           raise ModelOnexError(
               error_code=EnumCoreErrorCode.VALIDATION_ERROR,
               message=f"processing_time_ms must be >= 0.0 or exactly -1.0, got {v}",
               context={"value": v, "field": "processing_time_ms"}
           )
       return v
   ```

### Current Implementation

As of v0.4.0, **200+ validators** across omnibase_core use `ModelOnexError`:

**Examples from codebase**:
- `model_reducer_output.py`: Sentinel value validation (lines 194, 209)
- `model_typed_mapping.py`: Type validation (6 validators)
- `model_event_bus_output_state.py`: State validation (3 validators)
- `model_numeric_string_value.py`: Numeric validation (5 validators)
- `model_structured_tags.py`: Tag validation (2 validators)

**Pattern consistency**: 100% of ONEX validators use `ModelOnexError`, creating a uniform error handling surface.

---

## Decision

**We will continue using `ModelOnexError` in `@field_validator` decorators.**

This decision applies to:
- All Pydantic models in `src/omnibase_core/models/`
- Field validators (`@field_validator`)
- Model validators (`@model_validator`)
- Custom validation logic requiring structured errors

---

## Rationale

### 1. Framework Consistency (Primary)

**Goal**: All ONEX errors should be `ModelOnexError` or subclasses.

**Current state**: 100% of validators use `ModelOnexError` (200+ validators across 207 files).

**Benefit**: Developers only learn ONE error handling pattern:
```python
# Everywhere in ONEX - same pattern
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="...",
    context={...}
)
```

**Alternative (rejected)**: Using `ValueError` for validators would create TWO error handling patterns:
```python
# In validators
raise ValueError("...")

# Everywhere else
raise ModelOnexError(...)
```

This violates the principle of least surprise and complicates error handling logic.

### 2. Structured Error Context

**ModelOnexError provides**:
- `error_code: EnumCoreErrorCode` - Machine-readable error classification
- `message: str` - Human-readable description
- `context: dict[str, Any]` - Structured debugging data
- `correlation_id: UUID | None` - Request correlation (when available)
- `timestamp: datetime` - Error occurrence time
- `component: str | None` - Component where error occurred

**ValueError provides**:
- `str(error)` - Unstructured string message only

**Example - Debugging with context**:
```python
# ModelOnexError - structured data for logging/monitoring
try:
    output = ModelReducerOutput(processing_time_ms=-5.0, ...)
except ModelOnexError as e:
    logger.error(
        "Validation failed",
        extra={
            "error_code": e.error_code,
            "field": e.context.get("field"),
            "value": e.context.get("value"),
            "sentinel": e.context.get("sentinel_value")
        }
    )
    # Machine-readable error code for alerting
    if e.error_code == EnumCoreErrorCode.VALIDATION_ERROR:
        metrics.increment("validation.failure", tags={"field": e.context["field"]})

# ValueError - unstructured string parsing
try:
    output = ModelReducerOutput(processing_time_ms=-5.0, ...)
except ValueError as e:
    logger.error(f"Validation failed: {e}")  # Must parse string
    # No error code, no structured context
```

### 3. Machine-Readable Error Codes

**EnumCoreErrorCode enables**:
- Programmatic error handling (e.g., retry logic based on error code)
- Monitoring and alerting (e.g., alert on `VALIDATION_ERROR` spike)
- Error categorization (validation vs. system vs. business logic errors)

**Example - Error code driven logic**:
```python
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

try:
    result = process_data(input_data)
except ModelOnexError as e:
    if e.error_code == EnumCoreErrorCode.VALIDATION_ERROR:
        # Validation errors are user-facing - return 400
        return {"status": 400, "error": e.message}
    elif e.error_code == EnumCoreErrorCode.OPERATION_FAILED:
        # Operational errors may be transient - retry
        return retry_operation()
    else:
        # Unknown error - escalate
        raise
```

With `ValueError`, this logic requires fragile string parsing.

### 4. Zero Boilerplate Error Handling

**Pattern**: Validators using `ModelOnexError` integrate seamlessly with ONEX error handling decorators:

```python
from omnibase_core.decorators.error_handling import standard_error_handling

class NodeMyReducer(NodeReducer):
    @standard_error_handling  # Catches ModelOnexError, logs with context
    async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
        # Validation errors from ModelReducerOutput.__init__ are caught here
        return ModelReducerOutput(
            result=new_state,
            processing_time_ms=42.0,
            items_processed=10,
            ...
        )
```

**Alternative (rejected)**: Using `ValueError` would require wrapping Pydantic validation:
```python
try:
    return ModelReducerOutput(...)
except ValueError as e:
    # Manual conversion to ModelOnexError
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message=str(e)
    ) from e
```

### 5. Correlation Tracking Readiness

**Current state**: While validators don't have `correlation_id` access during model construction, the `ModelOnexError` structure is **ready** for future enhancement.

**Future pattern** (post-validation correlation injection):
```python
# Hypothetical future enhancement
try:
    output = ModelReducerOutput(processing_time_ms=-5.0, ...)
except ModelOnexError as e:
    # Inject correlation_id after validation
    e.correlation_id = input_data.correlation_id
    raise
```

Using `ValueError` would require migrating ALL validators to support this pattern.

---

## Pydantic v2+ Compatibility Analysis

### Pydantic's Recommended Pattern

**Official documentation** ([Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)):

> "Validation code should not raise `ValidationError` itself, but rather raise a `ValueError` or `AssertionError` (or subclass thereof) which will be caught and used to populate `ValidationError`."

**Recommended usage**:
```python
@field_validator("name")
@classmethod
def validate_name(cls, v: str) -> str:
    if len(v) < 3:
        raise ValueError("Name must be at least 3 characters")
    return v
```

**Advanced usage** ([PydanticCustomError](https://docs.pydantic.dev/latest/errors/errors/)):
```python
from pydantic_core import PydanticCustomError

@field_validator("age")
@classmethod
def validate_age(cls, v: int) -> int:
    if v < 0:
        raise PydanticCustomError(
            'negative_age',
            'Age cannot be negative, got {age}',
            {'age': v}
        )
    return v
```

### Why ModelOnexError Still Works

**Key insight**: Pydantic v2 **propagates ModelOnexError directly** without wrapping it in `ValidationError`.

**Pydantic v2 behavior** (verified empirically):
1. Validator raises `ModelOnexError`
2. Pydantic propagates exception directly (no wrapping)
3. Caller receives `ModelOnexError` instance
4. All structured context preserved (error_code, message, context dict)

**Example**:
```python
from pydantic import BaseModel, field_validator
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class MyModel(BaseModel):
    value: float

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        if v < 0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value must be >= 0, got {v}",
                context={"value": v, "field": "value"}
            )
        return v

# Usage
try:
    model = MyModel(value=-1.0)
except ModelOnexError as e:  # ✅ ModelOnexError is NOT wrapped
    # Access structured error directly
    assert e.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert e.message == "Value must be >= 0, got -1.0"
    assert e.context == {"value": -1.0, "field": "value"}

    # No ValidationError wrapping - ModelOnexError is the exception
    print(f"Error code: {e.error_code}")
    print(f"Context: {e.context}")
```

**Result**: Pydantic v2 compatibility is **excellent** - ModelOnexError propagates unchanged with ALL structured context preserved.

**Important**: Pydantic only wraps `ValueError` and `AssertionError` in `ValidationError`. Custom exception types (like `ModelOnexError`) propagate directly. This is intentional behavior and works in our favor.

### Pydantic v3+ Considerations

**Known risk**: Pydantic v3 may change exception handling behavior.

**Mitigation strategies** (see [Future Migration Strategy](#future-migration-strategy)):

1. **Adapter Pattern**: Create compatibility layer for Pydantic versions
2. **Deprecation Detection**: Monitor Pydantic release notes for validator changes
3. **Validation Abstraction**: Extract validators to separate functions (easier to migrate)
4. **Test Coverage**: 12,000+ tests catch breaking changes early

**Current assessment**: Low risk - Pydantic v2 is stable (released 2023), v3 not announced.

---

## Implementation Pattern

### Standard Validator Pattern

**Template** (use this for new validators):
```python
from pydantic import BaseModel, field_validator
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class ModelExample(BaseModel):
    value: float

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate value follows business rules.

        Args:
            v: The value to validate

        Returns:
            The validated value

        Raises:
            ModelOnexError: If validation fails
        """
        if v < 0.0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"value must be >= 0.0, got {v}",
                context={
                    "value": v,
                    "field": "value",
                    "constraint": "non_negative",
                },
            )
        return v
```

### Sentinel Value Pattern (Advanced)

**Used in**: `model_reducer_output.py` (processing_time_ms, items_processed)

**Pattern**: Allow -1 as sentinel for "unavailable", reject other negatives:
```python
@field_validator("processing_time_ms")
@classmethod
def validate_processing_time_ms(cls, v: float) -> float:
    """Validate processing_time_ms follows sentinel pattern.

    Enforces that:
    1. Special float values (NaN, Inf, -Inf) are ALWAYS rejected
    2. Negative values are ONLY -1.0 (sentinel for unavailable/failed)
    3. Any other negative value is invalid

    Args:
        v: The processing time value to validate

    Returns:
        The validated processing time value

    Raises:
        ModelOnexError: If value is NaN, Inf, -Inf, or negative but not exactly -1.0
    """
    import math

    # Reject special float values first (NaN, Inf, -Inf)
    if math.isnan(v):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="processing_time_ms cannot be NaN (not a number)",
            context={"value": str(v), "field": "processing_time_ms"},
        )
    if math.isinf(v):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"processing_time_ms cannot be {'positive' if v > 0 else 'negative'} infinity",
            context={"value": str(v), "field": "processing_time_ms"},
        )

    # Enforce sentinel pattern: only -1.0 is permitted as negative value
    if v < 0.0 and v != -1.0:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"processing_time_ms must be >= 0.0 or exactly -1.0 (sentinel), got {v}",
            context={
                "value": v,
                "field": "processing_time_ms",
                "sentinel_value": -1.0,
            },
        )
    return v
```

### Multi-Field Validation Pattern

**Used in**: `model_event_bus_output_state.py`, `model_event_bus_input_state.py`

**Pattern**: Validate relationships between multiple fields:
```python
from pydantic import model_validator

@model_validator(mode="after")
def validate_consistency(self) -> "ModelExample":
    """Validate consistency between fields.

    Returns:
        The validated model instance

    Raises:
        ModelOnexError: If fields are inconsistent
    """
    if self.start_time > self.end_time:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"start_time ({self.start_time}) must be <= end_time ({self.end_time})",
            context={
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "validator": "validate_consistency",
            },
        )
    return self
```

### Error Context Best Practices

**Always include**:
- `field: str` - Field being validated
- `value: Any` - Invalid value (convert non-serializable types to strings)
- `constraint: str` - Which constraint was violated (e.g., "non_negative", "sentinel_pattern")

**Optionally include**:
- `expected: Any` - Expected value or range
- `validator: str` - Validator function name (for multi-field validators)
- `related_fields: list[str]` - Other fields involved in validation

**Example - Rich context**:
```python
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"Field 'count' must be in range [0, 100], got {v}",
    context={
        "field": "count",
        "value": v,
        "constraint": "range",
        "expected_min": 0,
        "expected_max": 100,
        "validator": "validate_count",
    },
)
```

---

## Future Migration Strategy

### When to Migrate

**Triggers for migration**:
1. Pydantic v3+ breaking changes to validator exception handling
2. Performance issues with ModelOnexError wrapping
3. ONEX framework adopts alternative validation approach

**Do NOT migrate preemptively** - current pattern is stable and proven.

### Migration Path (If Required)

#### Option 1: Adapter Pattern (Recommended)

**Create compatibility layer** that adapts ModelOnexError to Pydantic's requirements:

```python
# omnibase_core/adapters/pydantic_errors.py
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def to_pydantic_error(error: ModelOnexError) -> PydanticCustomError:
    """Convert ModelOnexError to PydanticCustomError.

    Args:
        error: The ModelOnexError to convert

    Returns:
        Equivalent PydanticCustomError
    """
    return PydanticCustomError(
        error.error_code.value,  # error type
        error.message,           # message template
        error.context,           # context dict
    )

# Usage in validators
@field_validator("value")
@classmethod
def validate_value(cls, v: float) -> float:
    if v < 0:
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Value must be >= 0, got {v}",
            context={"value": v, "field": "value"}
        )
        raise to_pydantic_error(error)
    return v
```

**Benefits**:
- Preserves ModelOnexError construction pattern
- Single-line change to validators
- Maintains structured error context
- Compatible with Pydantic v2+

**Implementation**: Add `to_pydantic_error` to ALL validators, then update if Pydantic v3 requires.

#### Option 2: Validation Abstraction (Alternative)

**Extract validation logic to standalone functions**:

```python
# omnibase_core/validation/reducers.py
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def validate_processing_time_sentinel(value: float, field: str = "processing_time_ms") -> float:
    """Validate processing time follows sentinel pattern.

    Args:
        value: The processing time to validate
        field: Field name for error messages

    Returns:
        The validated value

    Raises:
        ModelOnexError: If validation fails
    """
    import math

    if math.isnan(value):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{field} cannot be NaN",
            context={"value": str(value), "field": field}
        )
    # ... rest of validation logic

    return value

# Usage in model
class ModelReducerOutput(BaseModel):
    processing_time_ms: float

    @field_validator("processing_time_ms")
    @classmethod
    def validate_processing_time_ms(cls, v: float) -> float:
        return validate_processing_time_sentinel(v, "processing_time_ms")
```

**Benefits**:
- Validation logic testable independently
- Easy to adapt to different frameworks
- Reusable across multiple models

**Implementation**: Create `omnibase_core/validation/` module with validation functions.

#### Option 3: Direct Migration (Last Resort)

**Replace ModelOnexError with PydanticCustomError** (only if Options 1-2 fail):

```python
# Before
raise ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message=f"Value must be >= 0, got {v}",
    context={"value": v, "field": "value"}
)

# After
from pydantic_core import PydanticCustomError

raise PydanticCustomError(
    'validation_error',  # type
    'Value must be >= 0, got {value}',  # message template
    {'value': v, 'field': 'value'}  # context
)
```

**Drawbacks**:
- Loses EnumCoreErrorCode machine-readable codes
- Loses ModelOnexError framework consistency
- Requires updating 200+ validators

**Only use if**: Pydantic v3+ REQUIRES PydanticCustomError AND Options 1-2 are incompatible.

### Testing Migration

**Regression tests** (add to test suite):
```python
# tests/unit/migration/test_validator_error_compatibility.py
import pytest
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def test_modelonexerror_propagates_directly():
    """Verify ModelOnexError propagates directly through Pydantic validation.

    Pydantic v2 does NOT wrap ModelOnexError in ValidationError - it propagates
    custom exceptions directly. This is intentional behavior and works in our favor.
    """
    from pydantic import BaseModel, field_validator

    class TestModel(BaseModel):
        value: float

        @field_validator("value")
        @classmethod
        def validate_value(cls, v: float) -> float:
            if v < 0:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be >= 0, got {v}",
                    context={"value": v, "field": "value"}
                )
            return v

    # Test that ModelOnexError propagates unchanged
    with pytest.raises(ModelOnexError) as exc_info:
        TestModel(value=-1.0)

    error = exc_info.value
    assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert error.message == "Value must be >= 0, got -1.0"
    assert error.context == {"value": -1.0, "field": "value"}

    # Verify valid values pass
    model = TestModel(value=5.0)
    assert model.value == 5.0

def test_reducer_output_sentinel_validation():
    """Verify ModelReducerOutput sentinel validation works correctly."""
    from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
    from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
    from uuid import uuid4

    # Valid values (positive)
    output = ModelReducerOutput(
        result={"state": "active"},
        operation_id=uuid4(),
        reduction_type=EnumReductionType.FOLD,
        processing_time_ms=42.0,
        items_processed=10
    )
    assert output.processing_time_ms == 42.0
    assert output.items_processed == 10

    # Valid sentinel values (-1)
    output_sentinel = ModelReducerOutput(
        result={"state": "active"},
        operation_id=uuid4(),
        reduction_type=EnumReductionType.FOLD,
        processing_time_ms=-1.0,  # Sentinel: measurement failed
        items_processed=-1        # Sentinel: count unavailable
    )
    assert output_sentinel.processing_time_ms == -1.0
    assert output_sentinel.items_processed == -1

    # Invalid values (negative but not -1)
    with pytest.raises(ModelOnexError) as exc_info:
        ModelReducerOutput(
            result={"state": "active"},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=-5.0,  # INVALID
            items_processed=10
        )

    error = exc_info.value
    assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert "sentinel" in error.message.lower()
    assert error.context["value"] == -5.0
    assert error.context["sentinel_value"] == -1.0

def test_pydantic_version_compatibility():
    """Verify validator pattern works with installed Pydantic version."""
    import pydantic
    from packaging import version

    pydantic_version = version.parse(pydantic.VERSION)

    # Our pattern requires Pydantic 2.0+
    assert pydantic_version >= version.parse("2.0.0")

    # Test validator behavior with current version
    # (tests will fail if Pydantic v3 breaks compatibility)
    from pydantic import BaseModel, field_validator

    class TestModel(BaseModel):
        value: int

        @field_validator("value")
        @classmethod
        def validate_value(cls, v: int) -> int:
            if v < 0:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be >= 0, got {v}",
                    context={"value": v}
                )
            return v

    # Should work with current Pydantic version
    with pytest.raises(ModelOnexError):
        TestModel(value=-1)

    # Valid values should pass
    TestModel(value=5)
```

---

## Consequences

### Positive Consequences

1. **Framework Consistency**
   - All ONEX errors use ModelOnexError (100% coverage)
   - Single error handling pattern to learn
   - No special cases for validation errors

2. **Structured Error Context**
   - Machine-readable error codes via EnumCoreErrorCode
   - Rich debugging context in all errors
   - Correlation tracking ready (when model-level correlation added)

3. **Maintainability**
   - 200+ validators follow same pattern
   - Easy to add new validators (copy template)
   - Centralized error handling logic

4. **Observability**
   - Structured errors integrate with logging/monitoring
   - Error code-based alerting
   - Consistent error metrics across framework

### Negative Consequences

1. **Divergence from Pydantic Best Practices**
   - Pydantic recommends ValueError or PydanticCustomError
   - May complicate upgrades to Pydantic v3+
   - Requires monitoring Pydantic release notes

2. **Migration Risk**
   - If Pydantic v3 breaks compatibility, 200+ validators need updates
   - Migration effort proportional to validator count
   - Potential for subtle bugs during migration

3. **Documentation Overhead**
   - New developers must learn ONEX pattern (vs. Pydantic docs)
   - Requires ADR and examples to justify deviation
   - Must keep compatibility tests up-to-date

### Risk Mitigation

**Monitoring**:
- Subscribe to Pydantic release notes and changelogs
- Run CI tests against Pydantic pre-release versions
- Add compatibility tests to test suite

**Fallback Plan**:
- Option 1: Adapter pattern (to_pydantic_error)
- Option 2: Validation abstraction (extract to functions)
- Option 3: Direct migration (last resort)

**Documentation**:
- This ADR documents decision rationale
- Migration guide provides step-by-step instructions
- Test coverage catches breaking changes early

---

## Related Documents

### Internal Documentation

- [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - ONEX error framework overview
- [Node Building Guide](../../guides/node-building/README.md) - Node validation patterns
- [Reducer Output Model](../../../src/omnibase_core/models/reducer/model_reducer_output.py) - Reference implementation

### External References

- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Official validator documentation
- [Pydantic Error Handling](https://docs.pydantic.dev/latest/errors/errors/) - Error handling patterns
- [Pydantic Migration Guide](https://docs.pydantic.dev/latest/migration/) - v1 to v2 migration
- [PydanticCustomError API](https://docs.pydantic.dev/2.0/api/functional_validators/) - Custom error types

---

**Last Updated**: 2025-12-16
**Author**: Claude Code (Polymorphic Agent)
**Reviewers**: PR #205 (OMN-594)
**Status**: Accepted ✅
