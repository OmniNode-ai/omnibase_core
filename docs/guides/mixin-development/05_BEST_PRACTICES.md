> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Mixin Development](README.md) > Best Practices

# Mixin Development Best Practices

**Status**: Active
**Type**: Best Practices Guide
**Prerequisites**: [Creating Mixins](01_CREATING_MIXINS.md), [Pydantic Models](03_PYDANTIC_MODELS.md), [Mixin Integration](04_MIXIN_INTEGRATION.md)

## Overview

This guide provides best practices, patterns, tools, and utilities for creating robust, maintainable mixins. Follow these guidelines to ensure your mixins are production-ready and follow ONEX standards.

## Design Principles

### 1. Single Responsibility

**Principle**: Each mixin should address exactly one cross-cutting concern.

**✓ Good Examples**:
```
# ✓ Single concern: Error handling
mixin_name: "mixin_error_handling"
description: "Provides error handling and retry logic"

# ✓ Single concern: Logging
mixin_name: "mixin_logging"
description: "Provides structured logging capabilities"

# ✓ Single concern: Caching
mixin_name: "mixin_caching"
description: "Provides multi-tier caching strategies"
```

**✗ Bad Examples**:
```
# ✗ Multiple concerns
mixin_name: "mixin_utilities"
description: "Provides error handling, logging, and caching"

# ✗ Too broad
mixin_name: "mixin_everything"
description: "All the features you need"
```

### 2. Composability

**Principle**: Mixins should work together without conflicts.

**✓ Good Design**:
```
# Independent mixins that compose well
subcontracts:
  - path: "../../mixins/mixin_error_handling.yaml"
    integration_field: "error_handling_configuration"  # ✓ Unique field

  - path: "../../mixins/mixin_performance_monitoring.yaml"
    integration_field: "performance_monitoring_configuration"  # ✓ Unique field

  - path: "../../mixins/mixin_caching.yaml"
    integration_field: "caching_configuration"  # ✓ Unique field
```

**✗ Bad Design**:
```
# Conflicting integration fields
subcontracts:
  - path: "../../mixins/mixin_error_handling.yaml"
    integration_field: "config"  # ✗ Too generic

  - path: "../../mixins/mixin_caching.yaml"
    integration_field: "config"  # ✗ Conflict!
```

### 3. Explicit Over Implicit

**Principle**: Make dependencies and requirements explicit in contracts.

**✓ Good Practice**:
```
# Explicit dependencies
requires_dependencies:
  - name: "logging_protocol"
    type: "protocol"
    description: "Required for error logging"
    optional: false  # ✓ Clearly required

  - name: "metrics_protocol"
    type: "protocol"
    description: "Optional metrics collection"
    optional: true  # ✓ Clearly optional
```

**✗ Bad Practice**:
```
# Implicit dependencies (undocumented)
# Code assumes logging exists but doesn't declare it
# ✗ No requires_dependencies section
```

## Naming Conventions

### Mixin Files

**Pattern**: `mixin_[capability_name].yaml`

```
# ✓ Good names
mixin_error_handling.yaml
mixin_circuit_breaker.yaml
mixin_rate_limiting.yaml
mixin_authentication.yaml

# ✗ Bad names
error_handling.yaml         # Missing 'mixin_' prefix
mixin-error-handling.yaml   # Use underscores, not hyphens
ErrorHandling.yaml          # Use lowercase
mixin_errors.yaml           # Too vague
```

### Pydantic Model Files

**Pattern**: `model_[capability_name]_subcontract.py`

```
# ✓ Good names
model_error_handling_subcontract.py
model_circuit_breaker_subcontract.py
model_rate_limiting_subcontract.py

# ✗ Bad names
error_handling_model.py     # Wrong pattern
model_error_handling.py     # Missing '_subcontract'
ModelErrorHandling.py       # Use lowercase
```

### Pydantic Model Classes

**Pattern**: `Model[CapabilityName]Subcontract`

```
# ✓ Good class names
class ModelErrorHandlingSubcontract(BaseModel):
    ...

class ModelCircuitBreakerSubcontract(BaseModel):
    ...

# ✗ Bad class names
class ErrorHandlingSubcontract(BaseModel):  # Missing 'Model' prefix
    ...

class ModelErrorHandling(BaseModel):  # Missing 'Subcontract' suffix
    ...
```

### Integration Fields

**Pattern**: `{capability}_configuration`

```
# ✓ Good integration fields
integration_field: "error_handling_configuration"
integration_field: "circuit_breaker_configuration"
integration_field: "authentication_configuration"

# ✗ Bad integration fields
integration_field: "config"                  # Too generic
integration_field: "error_handling"          # Missing '_configuration'
integration_field: "error_handling_config"   # Use 'configuration', not 'config'
```

## Configuration Best Practices

### Sensible Defaults

Provide production-ready defaults:

```
error_handling_config:
  # ✓ Good: Sensible defaults
  enable_circuit_breaker: true        # Default to fault tolerance
  circuit_failure_threshold: 5        # Reasonable threshold
  error_retry_attempts: 3             # Not too many, not too few
  error_retry_delay_ms: 1000          # 1 second initial delay

  # ✗ Bad: Dangerous defaults
  # enable_circuit_breaker: false     # ✗ Unsafe default
  # circuit_failure_threshold: 1000   # ✗ Way too high
  # error_retry_attempts: 100         # ✗ Way too many
```

### Configuration Validation

Add constraints to prevent invalid configurations:

```
class ModelErrorHandlingSubcontract(BaseModel):
    """Error handling subcontract with validation."""

    # ✓ Good: Constrained values
    circuit_failure_threshold: int = Field(
        default=5,
        ge=1,     # Minimum 1
        le=100,   # Maximum 100
        description="Number of failures before opening circuit"
    )

    error_retry_attempts: int = Field(
        default=3,
        ge=1,     # At least 1 attempt
        le=10,    # Max 10 attempts
        description="Maximum retry attempts"
    )

    # ✗ Bad: No constraints
    # circuit_failure_threshold: int = 5  # Any value allowed
    # error_retry_attempts: int = 3       # Could be negative or huge
```

### Environment-Specific Configuration

Support different configurations for different environments:

```
class ModelCircuitBreakerSubcontract(BaseModel):
    """Circuit breaker with environment support."""

    # ✓ Good: Environment-aware defaults
    circuit_failure_threshold: int = Field(
        default=5,
        description="Failures before opening (use 10 in production)"
    )

    # Helper method for environment
    @classmethod
    def for_environment(cls, env: str):
        """Create configuration for specific environment."""
        if env == "production":
            return cls(
                circuit_failure_threshold=10,  # More tolerant in prod
                circuit_timeout_ms=60000       # Longer timeout in prod
            )
        elif env == "development":
            return cls(
                circuit_failure_threshold=3,   # Stricter in dev
                circuit_timeout_ms=10000       # Shorter timeout in dev
            )
        else:
            return cls()  # Use defaults
```

## Action Design

### Complete Action Specifications

Provide comprehensive action definitions:

```
actions:
  # ✓ Good: Complete specification
  - name: "handle_error"
    description: "Process and categorize errors with appropriate handling strategy. Returns error handling result with recovery suggestions."
    inputs:
      - "error_info"        # Exception details including type, message, stack trace
      - "error_context"     # Execution context: node_id, operation_name, correlation_id
      - "handling_strategy" # Strategy: retry/fail_fast/fallback/ignore
    outputs:
      - "error_handling_result"  # Structured result with category, actions taken
      - "recovery_actions"       # List of suggested recovery steps
    required: true               # Action must be implemented
    timeout_ms: 2000             # Max 2 seconds to handle error

  # ✗ Bad: Incomplete specification
  - name: "handle_error"
    description: "Handles errors"  # ✗ Vague description
    inputs: ["error"]              # ✗ Unclear what "error" contains
    outputs: ["result"]            # ✗ What is "result"?
    required: true
    # ✗ Missing timeout
```

### Timeout Guidelines

Set appropriate timeouts based on operation complexity:

```
actions:
  # Fast operations
  - name: "validate_input"
    timeout_ms: 100        # ✓ Quick validation

  - name: "check_cache"
    timeout_ms: 500        # ✓ Fast cache lookup

  # Moderate operations
  - name: "handle_error"
    timeout_ms: 2000       # ✓ Error processing

  - name: "execute_retry"
    timeout_ms: 5000       # ✓ Includes retry logic

  # Long operations
  - name: "aggregate_data"
    timeout_ms: 30000      # ✓ Complex aggregation

  - name: "batch_process"
    timeout_ms: 60000      # ✓ Large batch processing
```

## Validation Best Practices

### Multi-Level Validation

Implement validation at multiple levels:

```
class ModelErrorHandlingSubcontract(BaseModel):
    """Error handling with multi-level validation."""

    circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    error_retry_attempts: int = Field(default=3, ge=1, le=10)

    # Level 1: Field-level validation (Pydantic automatic)
    # - Enforces ge/le constraints
    # - Type checking

    # Level 2: Single-field validators
    @field_validator("circuit_failure_threshold")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        """Additional threshold validation."""
        if v > 50:
            warnings.warn(
                f"Circuit failure threshold {v} is very high. "
                "Consider using a lower value for better fault tolerance."
            )
        return v

    # Level 3: Cross-field validators
    @model_validator(mode='after')
    def validate_circuit_and_retry(self):
        """Validate circuit breaker and retry are coherent."""
        threshold = self.circuit_failure_threshold
        retries = self.error_retry_attempts

        if threshold < retries:
            raise ValueError(
                f"Circuit breaker threshold ({threshold}) should be >= "
                f"retry attempts ({retries}) to allow retries before circuit opens"
            )

        return self
```

### Validation Error Messages

Provide clear, actionable error messages:

```
# ✓ Good: Clear and actionable
@field_validator("circuit_timeout_ms")
@classmethod
def validate_timeout(cls, v: int, info) -> int:
    """Validate circuit timeout is reasonable."""
    if v < 1000:
        raise ValueError(
            f"Circuit timeout ({v}ms) is too short. "
            f"Minimum recommended value is 1000ms. "
            f"Consider using 5000ms for most use cases."
        )
    return v

# ✗ Bad: Vague error message
@field_validator("circuit_timeout_ms")
@classmethod
def validate_timeout(cls, v: int) -> int:
    """Validate timeout."""
    if v < 1000:
        raise ValueError("Invalid timeout")  # ✗ Not helpful
    return v
```

## Documentation

### Comprehensive Mixin Documentation

Document your mixin thoroughly:

```
mixin_name: "mixin_error_handling"
mixin_version: {major: 1, minor: 0, patch: 0}
description: |
  Provides standardized error handling, circuit breakers, and fault tolerance for ONEX nodes.

  **Features**:
  - Automatic error categorization (transient vs permanent)
  - Circuit breaker pattern to prevent cascading failures
  - Exponential backoff retry logic with configurable attempts
  - Error metrics collection for monitoring
  - Sensitive data scrubbing in error messages

  **Use Cases**:
  - EFFECT nodes calling external APIs (circuit breaker protection)
  - Any node requiring retry logic for transient failures
  - Production environments requiring fault tolerance

  **Best Practices**:
  - Enable circuit breaker for all external calls
  - Set circuit_failure_threshold based on your SLA
  - Configure retriable_error_types for your specific errors
  - Monitor circuit breaker metrics to tune thresholds

  **Examples**:
  See docs/guides/mixin-development/examples/error_handling_examples.md
```

### Inline Code Documentation

Document your Pydantic models thoroughly:

```
class ModelErrorHandlingSubcontract(BaseModel):
    """
    Error handling subcontract Pydantic backing model.

    Provides runtime validation and configuration for the error handling mixin.
    Supports circuit breaker patterns, retry logic with exponential backoff,
    and comprehensive error categorization.

    **Usage**:
        >>> config = ModelErrorHandlingSubcontract(
        ...     circuit_failure_threshold=10,
        ...     error_retry_attempts=5
        ... )
        >>> config.is_error_retriable("TimeoutError")
        True

    **Examples**:
        Production configuration:
        >>> prod_config = ModelErrorHandlingSubcontract(
        ...     enable_circuit_breaker=True,
        ...     circuit_failure_threshold=10,
        ...     circuit_timeout_ms=60000,
        ...     error_retry_attempts=5
        ... )

        Development configuration:
        >>> dev_config = ModelErrorHandlingSubcontract(
        ...     enable_circuit_breaker=True,
        ...     circuit_failure_threshold=3,
        ...     circuit_timeout_ms=10000,
        ...     error_retry_attempts=2
        ... )

    **See Also**:
        - docs/guides/mixin-development/01_CREATING_MIXINS.md
        - docs/guides/mixin-development/04_MIXIN_INTEGRATION.md
    """

    circuit_failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description=(
            "Number of consecutive failures before opening the circuit breaker. "
            "Lower values fail faster but may be too sensitive. "
            "Higher values are more tolerant but allow more failures. "
            "Recommended: 5 for development, 10 for production."
        )
    )
```

## Testing

### Comprehensive Test Coverage

Test all aspects of your mixin:

```
# tests/model/subcontracts/test_model_error_handling_subcontract.py

class TestModelErrorHandlingSubcontract:
    """Comprehensive test suite for error handling mixin."""

    # 1. Test defaults
    def test_default_values(self):
        """Test all default values are sensible."""
        model = ModelErrorHandlingSubcontract()
        assert model.enable_circuit_breaker is True
        assert model.circuit_failure_threshold == 5
        assert model.error_retry_attempts == 3
        assert len(model.retriable_error_types) > 0

    # 2. Test validation
    def test_validation_constraints(self):
        """Test field constraint validation."""
        # Test minimum constraint
        with pytest.raises(ValidationError):
            ModelErrorHandlingSubcontract(circuit_failure_threshold=0)

        # Test maximum constraint
        with pytest.raises(ValidationError):
            ModelErrorHandlingSubcontract(circuit_failure_threshold=101)

    # 3. Test cross-field validation
    def test_cross_field_validation(self):
        """Test validators that check multiple fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorHandlingSubcontract(
                circuit_failure_threshold=2,  # Less than retry attempts
                error_retry_attempts=5
            )
        assert "should be >=" in str(exc_info.value)

    # 4. Test helper methods
    def test_is_error_retriable(self):
        """Test error retriable check."""
        model = ModelErrorHandlingSubcontract(
            retriable_error_types=["TimeoutError"]
        )
        assert model.is_error_retriable("TimeoutError") is True
        assert model.is_error_retriable("ValidationError") is False

    # 5. Test edge cases
    def test_calculate_retry_delay_edge_cases(self):
        """Test retry delay calculation edge cases."""
        model = ModelErrorHandlingSubcontract(
            error_retry_delay_ms=1000,
            max_retry_delay_ms=5000
        )

        # Test capping at max delay
        assert model.calculate_retry_delay(10) == 5000

        # Test zero attempt (should use attempt 1)
        assert model.calculate_retry_delay(1) == 1000

    # 6. Test serialization
    def test_json_serialization_round_trip(self):
        """Test model can be serialized and deserialized."""
        original = ModelErrorHandlingSubcontract(
            circuit_failure_threshold=10
        )

        json_str = original.model_dump_json()
        restored = ModelErrorHandlingSubcontract.model_validate_json(json_str)

        assert restored.circuit_failure_threshold == 10

    # 7. Test integration scenarios
    def test_production_configuration(self):
        """Test realistic production configuration."""
        prod_config = ModelErrorHandlingSubcontract(
            enable_circuit_breaker=True,
            circuit_failure_threshold=10,
            circuit_timeout_ms=60000,
            error_retry_attempts=5,
            error_retry_delay_ms=2000,
            retriable_error_types=["TimeoutError", "ServiceUnavailable"]
        )

        # Verify production-ready settings
        assert prod_config.enable_circuit_breaker is True
        assert prod_config.circuit_failure_threshold >= 5
        assert prod_config.error_retry_attempts <= 10
```

## Tools and Utilities

### Contract Validator

Use the enhanced contract validator:

```
# Validate mixin contract
uv run onex run contract_validator \
    --contract src/your_project/mixins/mixin_error_handling.yaml \
    --verbose

# Validate node contract with mixins
uv run onex run contract_validator \
    --contract src/your_project/nodes/api_client_effect/v1_0_0/contract.yaml \
    --check-mixins \
    --verbose
```

### Type Generation

Generate Pydantic models from YAML contracts:

```
# Generate model skeleton
uv run onex run generate_model \
    --contract src/your_project/mixins/mixin_error_handling.yaml \
    --output src/your_project/model/subcontracts/model_error_handling_subcontract.py

# Note: Review and customize generated model
```

### Mixin Inspector

Inspect mixin usage across project:

```
# Find all nodes using a specific mixin
uv run onex run inspect_mixin \
    --mixin mixin_error_handling \
    --project-root src/your_project

# Output:
# Nodes using mixin_error_handling:
# - api_client_effect (v1.0.0)
# - database_connector_effect (v1.0.0)
# - external_api_gateway_effect (v2.0.0)
```

### Documentation Generator

Generate documentation from mixin contracts:

```
# Generate mixin documentation
uv run onex run generate_mixin_docs \
    --mixin src/your_project/mixins/mixin_error_handling.yaml \
    --output docs/mixins/ERROR_HANDLING_MIXIN.md \
    --include-examples
```

## Performance Optimization

### Lazy Loading

Load mixin configurations lazily when possible:

```
class NodeApiClientEffect(NodeEffect):
    """Node with lazy mixin loading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_config = None  # Lazy loaded

    @property
    def error_config(self) -> ModelErrorHandlingSubcontract:
        """Lazy load error handling configuration."""
        if self._error_config is None:
            self._error_config = self.contract.error_handling_configuration
        return self._error_config
```

### Caching Mixin Results

Cache expensive mixin operations:

```
from functools import lru_cache

class NodeDataProcessor(NodeCompute):
    """Node with mixin result caching."""

    @lru_cache(maxsize=128)
    def calculate_retry_delay(self, attempt: int) -> int:
        """Calculate retry delay with caching."""
        return self.error_config.calculate_retry_delay(attempt)
```

### Minimize Validation

Validate once at initialization, not per-execution:

```
class NodeApiClientEffect(NodeEffect):
    """Node with validation at initialization."""

    async def initialize(self, contract: ModelContractEffect):
        """Initialize node and validate mixin configuration."""
        await super().initialize(contract)

        # ✓ Good: Validate once at initialization
        self.error_config = contract.error_handling_configuration
        self._validate_error_config()  # Validate here

    async def execute_effect(self, contract: ModelContractEffect):
        """Execute effect (no validation needed)."""
        # ✓ Config already validated
        return await self._execute_with_validated_config()

    def _validate_error_config(self):
        """Validate error handling configuration."""
        if self.error_config.circuit_failure_threshold < 1:
            raise ValueError("Invalid circuit breaker threshold")
```

## Common Pitfalls

### Pitfall 1: Tight Coupling

**❌ Bad**: Mixin depends on specific node implementation

```
# ✗ Bad: Mixin code assumes specific node methods
class ErrorHandlingMixin:
    def handle_error(self, error):
        # ✗ Assumes node has _log_error method
        self._log_error(error)
```

**✅ Good**: Mixin uses protocols/interfaces

```
# ✓ Good: Mixin uses dependency injection
class ErrorHandlingMixin:
    def __init__(self, logger: LoggerProtocol):
        self.logger = logger

    def handle_error(self, error):
        # ✓ Uses injected logger
        self.logger.log_error(error)
```

### Pitfall 2: Configuration Conflicts

**❌ Bad**: Multiple mixins try to configure the same thing

```
# ✗ Bad: Both mixins configure timeouts
mixin_error_handling:
  timeout_ms: 5000

mixin_circuit_breaker:
  timeout_ms: 10000  # ✗ Which timeout wins?
```

**✅ Good**: Clear separation of concerns

```
# ✓ Good: Each mixin has distinct configuration
error_handling_config:
  retry_timeout_ms: 5000  # ✓ Specific to retries

circuit_breaker_config:
  circuit_timeout_ms: 10000  # ✓ Specific to circuit breaker
```

### Pitfall 3: Missing Node Type Constraints

**❌ Bad**: Mixin applicable to wrong node types

```
# ✗ Bad: State management mixin allows COMPUTE nodes
mixin_name: "mixin_state_persistence"
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]
# ✗ COMPUTE nodes should be stateless!
```

**✅ Good**: Correct node type constraints

```
# ✓ Good: State management only for REDUCER
mixin_name: "mixin_state_persistence"
applicable_node_types: ["REDUCER"]
# ✓ Only stateful nodes
```

## Checklist

Use this checklist when creating mixins:

### Planning Phase
- [ ] Single, well-defined responsibility
- [ ] Identified target node types
- [ ] Listed all required actions
- [ ] Checked for existing similar mixins

### Implementation Phase
- [ ] Created YAML contract following schema
- [ ] Added comprehensive action definitions
- [ ] Provided sensible configuration defaults
- [ ] Created Pydantic backing model
- [ ] Added field validators
- [ ] Included helper methods
- [ ] Exported model in `__init__.py`

### Testing Phase
- [ ] Unit tests for Pydantic model
- [ ] Validation tests for all constraints
- [ ] Integration tests with nodes
- [ ] Edge case tests
- [ ] Serialization round-trip tests

### Documentation Phase
- [ ] Comprehensive mixin description
- [ ] Documented all actions
- [ ] Provided usage examples
- [ ] Documented node type constraints
- [ ] Added inline code documentation

### Validation Phase
- [ ] Contract validator passes
- [ ] Type checking passes (mypy)
- [ ] All tests pass
- [ ] Link validator passes

## Next Steps

- **[Creating Mixins](01_CREATING_MIXINS.md)**: Review step-by-step creation process
- **[Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)**: Deep architectural understanding
- **[Node Building Guide](../node-building/README.md)**: Build nodes using mixins

---

**Keep these best practices in mind when creating mixins to ensure production-ready, maintainable code!**
