> **Navigation**: [Home](../../index.md) > [Guides](../README.md) > [Mixin Development](README.md) > Pydantic Models

# Pydantic Models for Mixins

**Status**: Active
**Difficulty**: Intermediate
**Time**: 30-45 minutes
**Prerequisites**: [Creating Mixins](01_CREATING_MIXINS.md), Pydantic basics

## Overview

This guide teaches you how to create strongly-typed Pydantic backing models for your mixins. Pydantic models provide runtime validation, type safety, and IDE support for mixin configurations.

## Why Pydantic Models?

### Benefits

1. **Runtime Validation**: Catch configuration errors before execution
2. **Type Safety**: Strong typing with IDE autocomplete
3. **Documentation**: Self-documenting with field descriptions
4. **JSON Schema**: Automatic schema generation
5. **Serialization**: Easy conversion to/from JSON

### Relationship to YAML Contracts

```
YAML Contract (Definition)
    ↓ [Contract Loader]
Pydantic Model (Runtime)
    ↓ [Validation]
Node Implementation (Usage)
```

## Step 1: File Setup

### Create Model File

**Location**: `src/omnibase_core/model/subcontracts/`
**Naming**: `model_[capability_name]_subcontract.py`

```
cd /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/model/subcontracts/

# Create your model file
touch model_error_handling_subcontract.py
```

### Basic Imports

```
"""
Model backing for Error Handling Subcontract.
Generated from mixin_error_handling subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
```

## Step 2: Define Supporting Models

### Enumerations

Create enums for constrained string values:

```
class EnumErrorCategory(str, Enum):
    """Error category classification."""
    TRANSIENT = "transient"           # Temporary errors (retry possible)
    PERMANENT = "permanent"           # Permanent errors (no retry)
    CONFIGURATION = "configuration"   # Config-related errors
    VALIDATION = "validation"         # Input validation errors
    EXTERNAL = "external"             # External system errors
    INTERNAL = "internal"             # Internal system errors

class EnumCircuitBreakerState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

class EnumHandlingStrategy(str, Enum):
    """Error handling strategy."""
    RETRY = "retry"             # Retry operation
    FAIL_FAST = "fail_fast"     # Fail immediately
    FALLBACK = "fallback"       # Use fallback value
    IGNORE = "ignore"           # Log and continue
```

### Result Models

Create models for action outputs:

```
class ModelErrorHandlingResult(BaseModel):
    """Error handling result model."""

    error_category: EnumErrorCategory = Field(
        ...,
        description="Categorization of the error"
    )
    handling_action: EnumHandlingStrategy = Field(
        ...,
        description="Action taken to handle error"
    )
    recovery_possible: bool = Field(
        ...,
        description="Whether recovery is possible"
    )
    recovery_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested recovery actions"
    )
    error_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error_category": "transient",
                "handling_action": "retry",
                "recovery_possible": True,
                "recovery_suggestions": [
                    "Retry with exponential backoff",
                    "Check network connectivity"
                ]
            }
        }

class ModelCircuitBreakerStatus(BaseModel):
    """Circuit breaker status model."""

    status: EnumCircuitBreakerState = Field(
        ...,
        description="Current circuit breaker state"
    )
    failure_count: int = Field(
        default=0,
        ge=0,
        description="Number of consecutive failures"
    )
    failure_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Failure rate (0.0-1.0)"
    )
    last_failure_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last failure"
    )
    next_retry_time: Optional[datetime] = Field(
        default=None,
        description="When to attempt next retry"
    )

class ModelRetryDecision(BaseModel):
    """Retry decision model."""

    should_retry: bool = Field(
        ...,
        description="Whether operation should be retried"
    )
    retry_delay_ms: int = Field(
        default=1000,
        ge=0,
        description="Delay before retry in milliseconds"
    )
    retry_attempt: int = Field(
        default=1,
        ge=1,
        description="Current retry attempt number"
    )
    max_attempts_reached: bool = Field(
        default=False,
        description="Whether max retry attempts reached"
    )
```

## Step 3: Main Subcontract Model

### Basic Structure

```
class ModelErrorHandlingSubcontract(BaseModel):
    """
    Error handling subcontract Pydantic backing model.

    Provides runtime validation for error handling mixin configuration.
    Supports circuit breaker patterns, retry logic, and error categorization.
    """

    # === METADATA ===
    subcontract_name: str = Field(
        default="mixin_error_handling",
        description="Subcontract identifier"
    )
    subcontract_version: str = Field(
        default="1.0.0",
        description="Subcontract version"
    )
    applicable_node_types: List[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types where this mixin is applicable"
    )

    # === CIRCUIT BREAKER CONFIGURATION ===
    enable_circuit_breaker: bool = Field(
        default=True,
        description="Enable circuit breaker functionality"
    )
    circuit_failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of failures before opening circuit"
    )
    circuit_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Time to wait before half-open state (ms)"
    )
    circuit_half_open_max_calls: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Max calls allowed in half-open state"
    )

    # === RETRY CONFIGURATION ===
    error_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts"
    )
    error_retry_delay_ms: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Initial delay between retries (ms)"
    )
    error_retry_backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff multiplier"
    )
    max_retry_delay_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Maximum retry delay (ms)"
    )

    # === ERROR CATEGORIZATION ===
    retriable_error_types: List[str] = Field(
        default_factory=lambda: [
            "TimeoutError",
            "ConnectionError",
            "TemporaryFailure"
        ],
        description="Error types that can be retried"
    )
    fatal_error_types: List[str] = Field(
        default_factory=lambda: [
            "AuthenticationError",
            "ValidationError",
            "ConfigurationError"
        ],
        description="Error types that should not be retried"
    )

    # === MONITORING ===
    enable_error_metrics: bool = Field(
        default=True,
        description="Enable error metrics collection"
    )
    sensitive_data_scrubbing: bool = Field(
        default=True,
        description="Remove sensitive data from error messages"
    )
    error_log_level: str = Field(
        default="ERROR",
        description="Log level for errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enable_circuit_breaker": True,
                "circuit_failure_threshold": 5,
                "error_retry_attempts": 3,
                "error_retry_delay_ms": 1000,
                "retriable_error_types": [
                    "TimeoutError",
                    "ConnectionError"
                ]
            }
        }
```

### Adding Validators

```
    @field_validator("error_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("circuit_timeout_ms")
    @classmethod
    def validate_circuit_timeout(cls, v: int, info) -> int:
        """Ensure circuit timeout is reasonable."""
        retry_delay = info.data.get("error_retry_delay_ms", 1000)
        retry_attempts = info.data.get("error_retry_attempts", 3)

        # Circuit timeout should be longer than max retry time
        max_retry_time = retry_delay * retry_attempts * 2

        if v < max_retry_time:
            raise ValueError(
                f"Circuit timeout ({v}ms) should be >= max retry time ({max_retry_time}ms)"
            )

        return v

    @model_validator(mode='after')
    def validate_error_types(self):
        """Ensure no overlap between retriable and fatal error types."""
        retriable = set(self.retriable_error_types or [])
        fatal = set(self.fatal_error_types or [])

        overlap = retriable & fatal
        if overlap:
            raise ValueError(
                f"Error types cannot be both retriable and fatal: {overlap}"
            )

        return self

    @model_validator(mode='after')
    def validate_retry_config(self):
        """Validate retry configuration is coherent."""
        initial_delay = self.error_retry_delay_ms
        max_delay = self.max_retry_delay_ms

        if initial_delay > max_delay:
            raise ValueError(
                f"Initial retry delay ({initial_delay}ms) cannot exceed "
                f"max retry delay ({max_delay}ms)"
            )

        return self
```

### Helper Methods

```
    def is_error_retriable(self, error_type: str) -> bool:
        """Check if error type is retriable."""
        return error_type in self.retriable_error_types

    def is_error_fatal(self, error_type: str) -> bool:
        """Check if error type is fatal."""
        return error_type in self.fatal_error_types

    def calculate_retry_delay(self, attempt: int) -> int:
        """Calculate retry delay for given attempt with exponential backoff."""
        delay = self.error_retry_delay_ms * (self.error_retry_backoff_multiplier ** (attempt - 1))
        return min(int(delay), self.max_retry_delay_ms)

    def should_open_circuit(self, failure_count: int) -> bool:
        """Determine if circuit should open based on failures."""
        return (
            self.enable_circuit_breaker
            and failure_count >= self.circuit_failure_threshold
        )
```

## Step 4: Export Model

### Update __init__.py

```
# src/omnibase_core/model/subcontracts/__init__.py

from .model_error_handling_subcontract import (
    ModelErrorHandlingSubcontract,
    ModelErrorHandlingResult,
    ModelCircuitBreakerStatus,
    ModelRetryDecision,
    EnumErrorCategory,
    EnumCircuitBreakerState,
    EnumHandlingStrategy,
)

__all__ = [
    "ModelErrorHandlingSubcontract",
    "ModelErrorHandlingResult",
    "ModelCircuitBreakerStatus",
    "ModelRetryDecision",
    "EnumErrorCategory",
    "EnumCircuitBreakerState",
    "EnumHandlingStrategy",
]
```

## Step 5: Test Your Model

### Unit Tests

```
# tests/model/subcontracts/test_model_error_handling_subcontract.py

import pytest
from pydantic import ValidationError
from omnibase_core.model.subcontracts import (
    ModelErrorHandlingSubcontract,
    EnumErrorCategory,
    EnumCircuitBreakerState,
)

class TestModelErrorHandlingSubcontract:
    """Test error handling subcontract model."""

    def test_default_values(self):
        """Test model with default values."""
        model = ModelErrorHandlingSubcontract()

        assert model.subcontract_name == "mixin_error_handling"
        assert model.subcontract_version == "1.0.0"
        assert model.enable_circuit_breaker is True
        assert model.error_retry_attempts == 3
        assert len(model.retriable_error_types) > 0

    def test_custom_configuration(self):
        """Test model with custom configuration."""
        model = ModelErrorHandlingSubcontract(
            enable_circuit_breaker=True,
            circuit_failure_threshold=10,
            error_retry_attempts=5,
            error_retry_delay_ms=2000,
            retriable_error_types=["CustomError"]
        )

        assert model.circuit_failure_threshold == 10
        assert model.error_retry_attempts == 5
        assert "CustomError" in model.retriable_error_types

    def test_validation_threshold_too_high(self):
        """Test validation fails for threshold too high."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(circuit_failure_threshold=101)

        assert "circuit_failure_threshold" in str(exc_info.value)

    def test_validation_threshold_too_low(self):
        """Test validation fails for threshold too low."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(circuit_failure_threshold=0)

        assert "circuit_failure_threshold" in str(exc_info.value)

    def test_validation_invalid_log_level(self):
        """Test validation fails for invalid log level."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(error_log_level="INVALID")

        assert "Log level must be one of" in str(exc_info.value)

    def test_validation_overlapping_error_types(self):
        """Test validation fails for overlapping error types."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(
                retriable_error_types=["TimeoutError", "ValidationError"],
                fatal_error_types=["ValidationError", "AuthenticationError"]
            )

        assert "cannot be both retriable and fatal" in str(exc_info.value)

    def test_validation_invalid_retry_delays(self):
        """Test validation fails when initial delay > max delay."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(
                error_retry_delay_ms=50000,
                max_retry_delay_ms=30000
            )

        assert "cannot exceed max retry delay" in str(exc_info.value)

    def test_is_error_retriable(self):
        """Test error retriable check."""
        model = ModelErrorHandlingSubcontract(
            retriable_error_types=["TimeoutError", "ConnectionError"]
        )

        assert model.is_error_retriable("TimeoutError") is True
        assert model.is_error_retriable("ValidationError") is False

    def test_is_error_fatal(self):
        """Test error fatal check."""
        model = ModelErrorHandlingSubcontract(
            fatal_error_types=["AuthenticationError", "ValidationError"]
        )

        assert model.is_error_fatal("AuthenticationError") is True
        assert model.is_error_fatal("TimeoutError") is False

    def test_calculate_retry_delay(self):
        """Test retry delay calculation with exponential backoff."""
        model = ModelErrorHandlingSubcontract(
            error_retry_delay_ms=1000,
            error_retry_backoff_multiplier=2.0,
            max_retry_delay_ms=10000
        )

        # Attempt 1: 1000ms
        assert model.calculate_retry_delay(1) == 1000

        # Attempt 2: 2000ms
        assert model.calculate_retry_delay(2) == 2000

        # Attempt 3: 4000ms
        assert model.calculate_retry_delay(3) == 4000

        # Attempt 4: 8000ms
        assert model.calculate_retry_delay(4) == 8000

        # Attempt 5: Would be 16000ms, but capped at 10000ms
        assert model.calculate_retry_delay(5) == 10000

    def test_should_open_circuit(self):
        """Test circuit breaker opening logic."""
        model = ModelErrorHandlingSubcontract(
            enable_circuit_breaker=True,
            circuit_failure_threshold=5
        )

        assert model.should_open_circuit(4) is False
        assert model.should_open_circuit(5) is True
        assert model.should_open_circuit(6) is True

    def test_circuit_breaker_disabled(self):
        """Test circuit breaker logic when disabled."""
        model = ModelErrorHandlingSubcontract(
            enable_circuit_breaker=False,
            circuit_failure_threshold=5
        )

        # Should never open when disabled
        assert model.should_open_circuit(10) is False

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        model = ModelErrorHandlingSubcontract(
            circuit_failure_threshold=10,
            error_retry_attempts=5
        )

        json_data = model.model_dump_json()
        assert isinstance(json_data, str)
        assert "circuit_failure_threshold" in json_data

    def test_json_deserialization(self):
        """Test model can be created from JSON."""
        json_data = """
        {
            "circuit_failure_threshold": 10,
            "error_retry_attempts": 5
        }
        """

        model = ModelErrorHandlingSubcontract.model_validate_json(json_data)
        assert model.circuit_failure_threshold == 10
        assert model.error_retry_attempts == 5
```

## Common Patterns

### Pattern 1: Optional Fields

```
class ModelOptionalConfig(BaseModel):
    """Model with optional fields."""

    required_field: str = Field(..., description="This field is required")
    optional_field: Optional[str] = Field(None, description="This field is optional")
    optional_with_default: str = Field("default", description="Optional with default")
```

### Pattern 2: Constrained Values

```
class ModelConstrainedValues(BaseModel):
    """Model with constrained values."""

    positive_int: int = Field(..., ge=0, description="Must be >= 0")
    bounded_int: int = Field(..., ge=1, le=100, description="Must be 1-100")
    percentage: float = Field(..., ge=0.0, le=1.0, description="0.0 to 1.0")
    non_empty_string: str = Field(..., min_length=1, description="Cannot be empty")
    max_length_string: str = Field(..., max_length=256, description="Max 256 chars")
```

### Pattern 3: Complex Nested Models

```
class ModelNestedConfig(BaseModel):
    """Inner nested configuration."""
    setting1: str = Field(default="value1")
    setting2: int = Field(default=42)

class ModelMainConfig(BaseModel):
    """Main configuration with nested model."""
    simple_field: str = Field(default="simple")
    nested_config: ModelNestedConfig = Field(
        default_factory=ModelNestedConfig,
        description="Nested configuration"
    )
```

### Pattern 4: Discriminated Unions

```
from typing import Union, Literal

class ModelStrategyA(BaseModel):
    """Strategy A configuration."""
    type: Literal["strategy_a"] = "strategy_a"
    param_a: int = Field(...)

class ModelStrategyB(BaseModel):
    """Strategy B configuration."""
    type: Literal["strategy_b"] = "strategy_b"
    param_b: str = Field(...)

class ModelMainWithStrategy(BaseModel):
    """Model with strategy selection."""
    strategy: Union[ModelStrategyA, ModelStrategyB] = Field(..., discriminator="type")
```

## Best Practices

### 1. Field Documentation

Always provide clear descriptions:

```
timeout_ms: int = Field(
    default=5000,
    ge=100,
    le=60000,
    description="Operation timeout in milliseconds. Must be between 100ms and 60s."
)
```

### 2. Validation

Add validators for complex logic:

```
@field_validator("max_connections")
@classmethod
def validate_connections(cls, v: int, info) -> int:
    min_connections = info.data.get("min_connections", 1)
    if v < min_connections:
        raise ValueError(f"max_connections ({v}) must be >= min_connections ({min_connections})")
    return v
```

### 3. Helper Methods

Add convenience methods:

```
def is_enabled(self) -> bool:
    """Check if feature is enabled."""
    return self.enabled and self.threshold > 0

def get_timeout_seconds(self) -> float:
    """Get timeout in seconds."""
    return self.timeout_ms / 1000.0
```

### 4. Examples

Provide realistic examples in Config:

```
class Config:
    json_schema_extra = {
        "example": {
            "timeout_ms": 5000,
            "retry_attempts": 3,
            "enabled": True
        }
    }
```

## Troubleshooting

### Issue: ValidationError on Model Creation

**Symptom**: `ValidationError` when creating model

**Solutions**:
1. Check field constraints (ge, le, min_length, etc.)
2. Verify required fields provided
3. Check validator logic
4. Review type annotations

### Issue: Model Not Found

**Symptom**: `ImportError: cannot import ModelYourSubcontract`

**Solutions**:
1. Verify file in `model/subcontracts/`
2. Check `__init__.py` exports model
3. Run `poetry install` to update package

### Issue: Validator Not Running

**Symptom**: Invalid values not caught

**Solutions**:
1. Check validator decorator syntax
2. Verify field name matches
3. Use `@field_validator` for single field, `@model_validator` for cross-field validation

## Next Steps

- **[Mixin Integration](04_MIXIN_INTEGRATION.md)**: Integrate models into nodes
- **[Best Practices](05_BEST_PRACTICES.md)**: Advanced patterns and optimization
- **[Creating Mixins](01_CREATING_MIXINS.md)**: Review complete mixin creation

---

**Congratulations!** You've created a robust Pydantic model for your mixin with validation and type safety.
