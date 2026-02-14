> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Mixin Development](README.md) > Creating Mixins

# Creating Mixins - Step-by-Step Guide

**Status**: Active
**Difficulty**: Beginner to Intermediate
**Time**: 30-60 minutes
**Prerequisites**: Understanding of [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)

## Overview

This guide walks you through creating a complete mixin from scratch, including the YAML contract, Pydantic model, and integration into a node. You'll create a real-world error handling mixin that can be used across multiple node types.

## What You'll Build

**Mixin**: Error handling capabilities with circuit breaker and retry logic
**Applicable**: All node types (core mixin)
**Features**:
- Error categorization and handling
- Circuit breaker pattern
- Retry strategies
- Error metrics collection

## Step 1: Plan Your Mixin

### Define Purpose and Scope

Before writing code, clearly define your mixin:

**✅ Good Mixin Scope**:
- Single, well-defined responsibility
- Reusable across multiple nodes
- Clear boundaries with other mixins
- Applicable to specific node types

**❌ Bad Mixin Scope**:
- Multiple unrelated responsibilities
- Node-specific implementation details
- Overlapping with existing mixins
- Unclear boundaries

### Identify Target Node Types

Determine which node types your mixin should support:

```
# Core mixin (all nodes)
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

# EFFECT-specific mixin
applicable_node_types: ["EFFECT"]

# REDUCER and ORCHESTRATOR only
applicable_node_types: ["REDUCER", "ORCHESTRATOR"]
```

**Error Handling Mixin Decision**: Core mixin - all nodes need error handling.

### List Required Actions

Define what actions your mixin provides:

```
Error Handling Actions:
1. handle_error - Process and categorize errors
2. circuit_breaker_check - Check circuit breaker status
3. should_retry - Determine if operation should retry
4. record_error_metric - Track error occurrences
```

## Step 2: Create YAML Contract

### Choose File Location

> **Note**: YAML mixin contract files are a planned feature. The directory
> `nodes/canary/mixins/` does not yet exist. Currently, the Pydantic subcontract
> models in `models/contracts/subcontracts/` serve as the contract definitions.
> The YAML structure below shows the planned target format.

```bash
# Planned mixin location (not yet created)
# cd src/omnibase_core/nodes/canary/mixins/
# touch mixin_error_handling.yaml

# Current approach: create Pydantic model directly
cd src/omnibase_core/models/contracts/subcontracts/
touch model_error_handling_subcontract.py
```

### Write Basic Structure

```yaml
# mixin_error_handling.yaml
mixin_name: "mixin_error_handling"
mixin_version:
  major: 1
  minor: 0
  patch: 0
description: "Standardized error handling, circuit breakers, and fault tolerance for ONEX nodes"
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]
```

### Define Actions

Add each action with complete specifications:

```
actions:
  - name: "handle_error"
    description: "Process and categorize errors with appropriate handling strategy"
    inputs:
      - "error_info"          # Exception details
      - "error_context"       # Execution context
      - "handling_strategy"   # How to handle (retry/fail/ignore)
    outputs:
      - "error_handling_result"  # Processing result
      - "recovery_actions"       # Suggested recovery steps
    required: true
    timeout_ms: 2000

  - name: "circuit_breaker_check"
    description: "Check circuit breaker status before operation"
    inputs:
      - "operation_key"       # Unique operation identifier
    outputs:
      - "circuit_status"      # open/closed/half_open
      - "failure_rate"        # Current failure percentage
    required: false
    timeout_ms: 500

  - name: "should_retry"
    description: "Determine if failed operation should be retried"
    inputs:
      - "error_type"          # Type of error that occurred
      - "attempt_number"      # Current retry attempt
      - "operation_context"   # Operation details
    outputs:
      - "retry_decision"      # Boolean retry decision
      - "retry_delay_ms"      # Delay before retry
    required: false
    timeout_ms: 100

  - name: "record_error_metric"
    description: "Record error occurrence for monitoring"
    inputs:
      - "error_category"      # Error classification
      - "operation_name"      # Operation that failed
      - "error_metadata"      # Additional error details
    outputs:
      - "metric_recorded"     # Confirmation boolean
    required: false
    timeout_ms: 500
```

### Add Configuration Section

Define configuration parameters with defaults:

```
error_handling_config:
  # Circuit breaker settings
  enable_circuit_breaker: true
  circuit_failure_threshold: 5
  circuit_timeout_ms: 30000
  circuit_half_open_max_calls: 3

  # Retry settings
  error_retry_attempts: 3
  error_retry_delay_ms: 1000
  error_retry_backoff_multiplier: 2.0
  max_retry_delay_ms: 30000

  # Error categorization
  retriable_error_types:
    - "TimeoutError"
    - "ConnectionError"
    - "TemporaryFailure"
  fatal_error_types:
    - "AuthenticationError"
    - "ValidationError"
    - "ConfigurationError"

  # Monitoring
  enable_error_metrics: true
  sensitive_data_scrubbing: true
  error_log_level: "ERROR"
```

### Define Output Models

Specify the structure of action outputs:

```
output_models:
  error_handling_result:
    error_category: "string"
    handling_action: "string"
    recovery_possible: "boolean"
    recovery_suggestions:
      type: "array"
      items: "string"

  circuit_status_result:
    status: "string"  # open/closed/half_open
    failure_count: "integer"
    failure_rate: "float"
    last_failure_time: "timestamp"

  retry_decision_result:
    should_retry: "boolean"
    retry_delay_ms: "integer"
    retry_attempt: "integer"
    max_attempts_reached: "boolean"
```

### Declare Dependencies

Specify what your mixin provides and requires:

```
dependencies:
  - name: "error_handling"
    type: "capability"
    description: "Provides standardized error handling capabilities"

  - name: "circuit_breaker"
    type: "capability"
    description: "Provides circuit breaker pattern implementation"

requires_dependencies:
  - name: "logging_protocol"
    type: "protocol"
    description: "Requires logging capability for error recording"
    optional: false

  - name: "metrics_protocol"
    type: "protocol"
    description: "Requires metrics collection for error tracking"
    optional: true
```

### Add Metrics (Optional)

Define metrics this mixin collects:

```
metrics:
  - name: "errors_total"
    type: "counter"
    description: "Total number of errors handled"
    labels:
      - "error_category"
      - "node_type"
      - "operation_name"

  - name: "circuit_breaker_state"
    type: "gauge"
    description: "Current circuit breaker state (0=closed, 1=open, 2=half_open)"
    labels:
      - "operation_key"

  - name: "retry_attempts_total"
    type: "counter"
    description: "Total number of retry attempts"
    labels:
      - "operation_name"
      - "success"

  - name: "error_handling_duration_ms"
    type: "histogram"
    description: "Time spent handling errors"
    labels:
      - "error_category"
    buckets: [1, 5, 10, 50, 100, 500, 1000, 5000]
```

## Step 3: Validate YAML Contract

### Use Contract Validator

```
# Validate your mixin contract
poetry run onex run contract_validator --contract src/omnibase_core/mixins/mixin_error_handling.yaml

# Expected output:
# ✓ YAML syntax valid
# ✓ Schema validation passed
# ✓ All required fields present
# ✓ Node type constraints valid
# ✓ Action definitions complete
```

### Common Validation Errors

**Missing Required Fields**:
```
# ❌ Missing description
mixin_name: "mixin_example"
mixin_version: {major: 1, minor: 0, patch: 0}
# Error: 'description' field required

# ✅ Correct
mixin_name: "mixin_example"
mixin_version: {major: 1, minor: 0, patch: 0}
description: "Example mixin description"
```

**Invalid Node Types**:
```
# ❌ Invalid node type
applicable_node_types: ["COMPUTE", "INVALID_TYPE"]
# Error: 'INVALID_TYPE' not in [COMPUTE, EFFECT, REDUCER, ORCHESTRATOR]

# ✅ Correct
applicable_node_types: ["COMPUTE", "EFFECT"]
```

**Incomplete Actions**:
```
# ❌ Missing outputs
actions:
  - name: "process_data"
    description: "Process data"
    inputs: ["data"]
    # Error: 'outputs' field required

# ✅ Correct
actions:
  - name: "process_data"
    description: "Process data"
    inputs: ["data"]
    outputs: ["result"]
```

## Step 4: Create Pydantic Backing Model

See [03_PYDANTIC_MODELS.md](03_PYDANTIC_MODELS.md) for detailed instructions.

### Quick Example

```
# model_error_handling_subcontract.py
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum

class EnumCircuitBreakerState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class ModelErrorHandlingResult(BaseModel):
    """Error handling result model."""
    error_category: str = Field(..., description="Error classification")
    handling_action: str = Field(..., description="Action taken")
    recovery_possible: bool = Field(..., description="Whether recovery is possible")
    recovery_suggestions: list[str] = Field(default_factory=list)

class ModelErrorHandlingSubcontract(BaseModel):
    """Error handling mixin Pydantic backing model."""

    subcontract_name: str = Field(default="mixin_error_handling")
    subcontract_version: str = Field(default="1.0.0")
    applicable_node_types: list[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]
    )

    # Circuit breaker configuration
    enable_circuit_breaker: bool = Field(default=True)
    circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    circuit_timeout_ms: int = Field(default=30000, ge=1000, le=300000)

    # Retry configuration
    error_retry_attempts: int = Field(default=3, ge=1, le=10)
    error_retry_delay_ms: int = Field(default=1000, ge=100, le=60000)

    # Error categorization
    retriable_error_types: list[str] = Field(
        default=["TimeoutError", "ConnectionError", "TemporaryFailure"]
    )
    fatal_error_types: list[str] = Field(
        default=["AuthenticationError", "ValidationError", "ConfigurationError"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enable_circuit_breaker": True,
                "circuit_failure_threshold": 5,
                "error_retry_attempts": 3
            }
        }
```

## Step 5: Test Your Mixin

### Unit Test the Pydantic Model

```
# tests/model/subcontracts/test_model_error_handling_subcontract.py
import pytest
from pydantic import ValidationError
from omnibase_core.models.contracts.subcontracts.model_error_handling_subcontract import ModelErrorHandlingSubcontract

def test_error_handling_subcontract_defaults():
    """Test default values."""
    mixin = ModelErrorHandlingSubcontract()

    assert mixin.subcontract_name == "mixin_error_handling"
    assert mixin.subcontract_version == "1.0.0"
    assert mixin.enable_circuit_breaker is True
    assert mixin.error_retry_attempts == 3

def test_error_handling_subcontract_validation():
    """Test field validation."""
    # Valid configuration
    mixin = ModelErrorHandlingSubcontract(
        circuit_failure_threshold=10,
        error_retry_attempts=5
    )
    assert mixin.circuit_failure_threshold == 10

    # Invalid: threshold too high
    with pytest.raises(ValidationError):
        ModelErrorHandlingSubcontract(circuit_failure_threshold=101)

    # Invalid: retry attempts too low
    with pytest.raises(ValidationError):
        ModelErrorHandlingSubcontract(error_retry_attempts=0)

def test_error_handling_subcontract_custom_error_types():
    """Test custom error type configuration."""
    mixin = ModelErrorHandlingSubcontract(
        retriable_error_types=["CustomError1", "CustomError2"],
        fatal_error_types=["FatalCustomError"]
    )

    assert "CustomError1" in mixin.retriable_error_types
    assert "FatalCustomError" in mixin.fatal_error_types
```

### Integration Test with Node

```
# tests/integration/test_error_handling_mixin_integration.py
import pytest
from omnibase_core.nodes import NodeCompute
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.subcontracts.model_error_handling_subcontract import ModelErrorHandlingSubcontract

class TestNodeWithErrorHandling(NodeCompute):
    """Test node with error handling mixin."""

    async def execute_compute(self, contract: ModelContractCompute):
        # Access error handling configuration
        error_config = contract.error_handling_configuration

        try:
            result = await self._risky_operation()
            return result
        except Exception as e:
            # Use mixin capabilities
            if error_config.enable_circuit_breaker:
                circuit_status = await self._check_circuit_breaker(
                    operation_key="risky_operation"
                )

                if circuit_status.status == "open":
                    raise RuntimeError("Circuit breaker open")

            # Retry logic
            if self._should_retry(e, error_config):
                return await self._retry_operation(error_config)

            raise

async def test_error_handling_mixin_integration():
    """Test error handling mixin integrated into node."""
    # Create contract with error handling mixin
    contract = ModelContractCompute(
        subcontracts=[
            ModelErrorHandlingSubcontract(
                enable_circuit_breaker=True,
                error_retry_attempts=3
            )
        ]
    )

    # Create node instance
    node = TestNodeWithErrorHandling()

    # Test error handling
    with pytest.raises(RuntimeError):
        await node.execute_compute(contract)
```

## Step 6: Document Your Mixin

### Create Mixin README

```markdown
# Error Handling Mixin

**Version**: 1.0.0
**Applicable**: All node types
**Status**: Production Ready

## Overview

Provides standardized error handling, circuit breaker patterns, and retry logic for ONEX nodes.

## Features

- **Error Categorization**: Automatic classification of errors
- **Circuit Breaker**: Prevent cascading failures
- **Retry Logic**: Configurable retry strategies with backoff
- **Error Metrics**: Comprehensive error tracking

## Usage

### Basic Configuration

```
subcontracts:
  - path: "../../mixins/mixin_error_handling.yaml"
    integration_field: "error_handling_configuration"
```markdown

### Advanced Configuration

```
from omnibase_core.models.contracts.subcontracts.model_error_handling_subcontract import ModelErrorHandlingSubcontract

error_config = ModelErrorHandlingSubcontract(
    enable_circuit_breaker=True,
    circuit_failure_threshold=10,
    error_retry_attempts=5,
    error_retry_delay_ms=2000
)
```markdown

## Best Practices

1. **Always Enable Circuit Breakers**: For EFFECT nodes calling external systems
2. **Configure Retry Types**: Specify which errors are retriable
3. **Set Appropriate Thresholds**: Based on your SLA requirements
4. **Monitor Metrics**: Track error rates and circuit breaker states
```

## Common Patterns

### Pattern 1: Core Mixin (All Nodes)

```
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]
```

**Use Cases**: Health checks, performance monitoring, logging

### Pattern 2: EFFECT-Specific Mixin

```
applicable_node_types: ["EFFECT"]
```

**Use Cases**: External dependencies, circuit breakers, API clients

### Pattern 3: REDUCER-Specific Mixin

```
applicable_node_types: ["REDUCER"]
```

**Use Cases**: State management, aggregation, caching

### Pattern 4: ORCHESTRATOR-Specific Mixin

```
applicable_node_types: ["ORCHESTRATOR"]
```

**Use Cases**: Workflow coordination, FSM, routing

## Troubleshooting

### Issue: Contract Validation Fails

**Symptom**: Validator reports schema errors

**Solution**:
1. Verify YAML syntax with a YAML linter
2. Check all required fields present
3. Validate node type names
4. Ensure action definitions complete

### Issue: Pydantic Model Import Fails

**Symptom**: `ImportError: cannot import ModelYourMixinSubcontract`

**Solution**:
1. Verify model file in correct location: `models/contracts/subcontracts/`
2. Check model class name matches pattern
3. Ensure `__init__.py` exports your model
4. Run `poetry install` to update package

### Issue: Node Can't Find Mixin Configuration

**Symptom**: `AttributeError: 'ModelContractCompute' has no attribute 'your_mixin_configuration'`

**Solution**:
1. Verify `integration_field` name in contract
2. Check mixin path is correct
3. Ensure contract loaded properly
4. Validate subcontract reference syntax

## Next Steps

- **[Mixin YAML Schema](02_MIXIN_YAML_SCHEMA.md)**: Complete YAML reference
- **[Pydantic Models](03_PYDANTIC_MODELS.md)**: Detailed model creation guide
- **[Mixin Integration](04_MIXIN_INTEGRATION.md)**: Integration patterns
- **[Best Practices](05_BEST_PRACTICES.md)**: Advanced patterns and utilities

---

**Congratulations!** You've created a complete mixin. Review [Best Practices](05_BEST_PRACTICES.md) for optimization tips.
