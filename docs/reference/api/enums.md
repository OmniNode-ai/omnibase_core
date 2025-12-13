# Enums API Reference - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides comprehensive API reference for all enumeration types in omnibase_core. Enums provide type-safe constants and validation throughout the ONEX framework.

## Core Enumerations

### Error Codes

#### EnumCoreErrorCode

**Location**: `omnibase_core.enums.enum_core_error_code`

**Purpose**: Standard error codes for ONEX framework.

```
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Usage in error handling
error = ModelOnexError(
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="Input validation failed"
)
```

#### Available Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `PROCESSING_ERROR` - General processing error
- `TIMEOUT_ERROR` - Operation timeout
- `CONFIGURATION_ERROR` - Configuration issue
- `DEPENDENCY_ERROR` - External dependency failure
- `AUTHENTICATION_ERROR` - Authentication failure
- `AUTHORIZATION_ERROR` - Authorization failure
- `NOT_FOUND_ERROR` - Resource not found
- `CONFLICT_ERROR` - Resource conflict
- `RATE_LIMIT_ERROR` - Rate limit exceeded

### Node Types

#### EnumNodeType

**Location**: `omnibase_core.enums.enum_node_type`

**Purpose**: Node type classification.

```
from omnibase_core.enums.enum_node_type import EnumNodeType

# Use the GENERIC variant for four-node architecture types
node_type = EnumNodeType.COMPUTE_GENERIC
```

#### Available Node Types

**Core ONEX Four-Node Architecture Types**:
> **Migration Note**: As of v0.2.0, the four-node architecture types use `*_GENERIC` suffix to eliminate naming collisions with `EnumNodeKind`. Legacy YAML configs automatically map old names to new variants.

- `COMPUTE_GENERIC` - Pure computation nodes (was `COMPUTE`)
- `EFFECT_GENERIC` - Side effect nodes (was `EFFECT`)
- `REDUCER_GENERIC` - State management nodes (was `REDUCER`)
- `ORCHESTRATOR_GENERIC` - Workflow coordination nodes (was `ORCHESTRATOR`)

**Other Node Types**:
- `GATEWAY` - Gateway nodes for routing
- `VALIDATOR` - Validation nodes
- `TRANSFORMER` - Data transformation nodes
- `AGGREGATOR` - Data aggregation nodes
- `FUNCTION` - Function nodes
- `TOOL` - Tool nodes
- `AGENT` - Agent nodes
- `MODEL` - Model nodes
- `PLUGIN` - Plugin nodes
- `SCHEMA` - Schema nodes
- `NODE` - Generic node
- `WORKFLOW` - Workflow nodes
- `SERVICE` - Service nodes
- `UNKNOWN` - Unknown node type

**Helper Methods**:
- `is_processing_node(node_type)` - Check if node performs data processing
- `is_control_node(node_type)` - Check if node handles control flow
- `is_output_node(node_type)` - Check if node produces output effects
- `get_node_category(node_type)` - Get functional category (processing/control/output)

### Action Types

#### EnumActionType

**Location**: `omnibase_core.enums.enum_workflow_execution`

**Purpose**: Types of Actions for orchestrated execution.

```
from uuid import uuid4
from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.orchestrator.model_action import ModelAction

action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    target_node_type="compute",
    lease_id=uuid4(),
    epoch=1,
    payload={"field": "status", "value": "completed"}
)
```

#### Available Action Types

- `COMPUTE` - Compute node action
- `EFFECT` - Effect node action
- `REDUCE` - Reducer node action
- `ORCHESTRATE` - Orchestrator action
- `CUSTOM` - Custom action type

**Note**: For Intent side effects, `ModelIntent` uses a string-based `intent_type` field (not an enum). Common values include: "log", "emit_event", "write", "notify", "http_request".

### Circuit Breaker States

#### EnumCircuitBreakerState

**Location**: `omnibase_core.enums.enum_circuit_breaker_state`

**Purpose**: Circuit breaker state management.

```
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState

state = circuit_breaker.get_state()
if state == EnumCircuitBreakerState.OPEN:
    # Circuit breaker is open, don't execute
    pass
```

#### Available States

- `CLOSED` - Normal operation, requests allowed
- `OPEN` - Circuit is open, requests blocked
- `HALF_OPEN` - Testing if service recovered

### Health Status

#### EnumHealthStatus

**Location**: `omnibase_core.enums.enum_health_status`

**Purpose**: Health status indicators.

```
from omnibase_core.enums.enum_health_status import EnumHealthStatus

health_status = EnumHealthStatus.HEALTHY
```

#### Available Statuses

**Note**: All values are lowercase strings.

- `HEALTHY` = "healthy" - Node is healthy and operational
- `DEGRADED` = "degraded" - Node is partially functional
- `UNHEALTHY` = "unhealthy" - Node is not functional
- `CRITICAL` = "critical" - Node is in critical state
- `UNKNOWN` = "unknown" - Health status cannot be determined
- `WARNING` = "warning" - Node has warnings
- `UNREACHABLE` = "unreachable" - Node cannot be reached
- `AVAILABLE` = "available" - Node is available
- `UNAVAILABLE` = "unavailable" - Node is unavailable
- `ERROR` = "error" - Node has errors

**Helper Methods**:
- `is_operational()` - Returns True if status is HEALTHY or DEGRADED
- `requires_attention()` - Returns True if status is UNHEALTHY or CRITICAL

### Operation Status

#### EnumOperationStatus

**Location**: `omnibase_core.enums.enum_operation_status`

**Purpose**: Operation execution status.

```
from omnibase_core.enums.enum_operation_status import EnumOperationStatus

status = EnumOperationStatus.SUCCESS
```

#### Available Statuses

**Note**: All values are lowercase strings.

- `SUCCESS` = "success" - Operation completed successfully
- `FAILED` = "failed" - Operation failed
- `IN_PROGRESS` = "in_progress" - Operation is in progress
- `CANCELLED` = "cancelled" - Operation was cancelled
- `PENDING` = "pending" - Operation is pending
- `TIMEOUT` = "timeout" - Operation timed out

**Helper Methods**:
- `is_terminal()` - Returns True if status is SUCCESS, FAILED, CANCELLED, or TIMEOUT
- `is_active()` - Returns True if status is IN_PROGRESS or PENDING
- `is_successful()` - Returns True if status is SUCCESS

### Message Roles

#### EnumMessageRole

**Location**: `omnibase_core.enums.enum_message_role`

**Purpose**: Message roles in communication.

```
from omnibase_core.enums.enum_message_role import EnumMessageRole

message_role = EnumMessageRole.REQUEST
```

#### Available Roles

- `REQUEST` - Request message
- `RESPONSE` - Response message
- `NOTIFICATION` - Notification message
- `ERROR` - Error message
- `HEARTBEAT` - Heartbeat message

### LLM Providers

#### EnumLLMProvider

**Location**: `omnibase_core.enums.enum_llm_provider`

**Purpose**: Supported LLM providers.

```
from omnibase_core.enums.enum_llm_provider import EnumLLMProvider

provider = EnumLLMProvider.OPENAI
```

#### Available Providers

- `OPENAI` - OpenAI GPT models
- `ANTHROPIC` - Anthropic Claude models
- `GOOGLE` - Google Gemini models
- `AZURE` - Azure OpenAI models
- `LOCAL` - Local model deployment

### Metric Types

#### EnumMetricType

**Location**: `omnibase_core.enums.enum_metric_type`

**Purpose**: Metric measurement types.

```
from omnibase_core.enums.enum_metric_type import EnumMetricType

metric_type = EnumMetricType.COUNTER
```

#### Available Types

- `COUNTER` - Incrementing counter
- `GAUGE` - Current value gauge
- `HISTOGRAM` - Value distribution
- `SUMMARY` - Statistical summary
- `TIMER` - Time measurement

## Usage Patterns

### Enum Validation

```
from pydantic import BaseModel, Field, field_validator
from omnibase_core.enums.enum_node_type import EnumNodeType

class NodeConfig(BaseModel):
    """Node configuration with enum validation."""

    node_type: EnumNodeType = Field(description="Type of node")
    name: str = Field(description="Node name")

    @field_validator('node_type')
    @classmethod
    def validate_node_type(cls, v):
        """Validate node type."""
        if v not in EnumNodeType:
            raise ValueError(f"Invalid node type: {v}")
        return v
```

### Enum Comparison

```
from omnibase_core.enums.enum_health_status import EnumHealthStatus

def check_health(health_status: EnumHealthStatus) -> bool:
    """Check if node is healthy."""
    return health_status in [EnumHealthStatus.HEALTHY, EnumHealthStatus.DEGRADED]

# Usage
if check_health(node.health_status):
    print("Node is operational")
```

### Enum Iteration

```
from omnibase_core.enums.enum_workflow_execution import EnumActionType

def get_all_action_types() -> List[str]:
    """Get all available action types."""
    return [action_type.value for action_type in EnumActionType]

# Usage
available_actions = get_all_action_types()
print(f"Available actions: {available_actions}")
```

### Enum Mapping

```
from omnibase_core.enums.enum_operation_status import EnumOperationStatus

# Map status to HTTP status codes
STATUS_TO_HTTP = {
    EnumOperationStatus.SUCCESS: 200,
    EnumOperationStatus.FAILURE: 500,
    EnumOperationStatus.TIMEOUT: 408,
    EnumOperationStatus.CANCELLED: 499,
    EnumOperationStatus.IN_PROGRESS: 202,
    EnumOperationStatus.PENDING: 202
}

def get_http_status(operation_status: EnumOperationStatus) -> int:
    """Get HTTP status code for operation status."""
    return STATUS_TO_HTTP.get(operation_status, 500)
```

### Custom Enum Methods

```
from enum import Enum

class EnumCustomStatus(str, Enum):
    """Custom enum with additional methods."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

    @classmethod
    def get_active_statuses(cls) -> List[str]:
        """Get all active statuses."""
        return [cls.ACTIVE.value]

    def is_active(self) -> bool:
        """Check if status is active."""
        return self == self.ACTIVE

    def get_display_name(self) -> str:
        """Get human-readable display name."""
        display_names = {
            self.ACTIVE: "Active",
            self.INACTIVE: "Inactive",
            self.PENDING: "Pending"
        }
        return display_names.get(self, self.value.title())
```

## Error Handling with Enums

### Enum Error Conversion

```
from omnibase_core.enums.enum_operation_status import EnumOperationStatus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def convert_status_to_error_code(status: EnumOperationStatus) -> EnumCoreErrorCode:
    """Convert operation status to error code."""
    status_to_error = {
        EnumOperationStatus.FAILURE: EnumCoreErrorCode.PROCESSING_ERROR,
        EnumOperationStatus.TIMEOUT: EnumCoreErrorCode.TIMEOUT_ERROR,
        EnumOperationStatus.CANCELLED: EnumCoreErrorCode.PROCESSING_ERROR
    }
    return status_to_error.get(status, EnumCoreErrorCode.PROCESSING_ERROR)
```

### Enum Validation in Error Handling

```
from omnibase_core.enums.enum_health_status import EnumHealthStatus

def validate_health_status(status: str) -> EnumHealthStatus:
    """Validate and convert health status string to enum."""
    try:
        return EnumHealthStatus(status)
    except ValueError:
        raise ValueError(f"Invalid health status: {status}. Valid values: {[s.value for s in EnumHealthStatus]}")
```

## Performance Considerations

### Enum Caching

```
from functools import lru_cache
from omnibase_core.enums.enum_node_type import EnumNodeType

@lru_cache(maxsize=32)
def is_compute_node(node_type: EnumNodeType) -> bool:
    """Cache enum comparison for performance."""
    return node_type == EnumNodeType.COMPUTE_GENERIC
```

### Enum Lookup Optimization

```
from omnibase_core.enums.enum_workflow_execution import EnumActionType

# Pre-compute lookup table for performance
ACTION_TYPE_LOOKUP = {action_type.value: action_type for action_type in EnumActionType}

def get_action_type(value: str) -> EnumActionType:
    """Fast enum lookup."""
    return ACTION_TYPE_LOOKUP.get(value, EnumActionType.CUSTOM)
```

## Related Documentation

- [Nodes API](nodes.md) - Node class reference
- [Models API](models.md) - Model class reference
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Node Building Guide](../../guides/node-building/README.md) - Usage examples
