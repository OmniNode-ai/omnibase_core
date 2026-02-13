> **Navigation**: [Home](../../INDEX.md) > [Reference](../README.md) > API > Enums

# Enums API Reference - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides comprehensive API reference for all enumeration types in omnibase_core. Enums provide type-safe constants and validation throughout the ONEX framework.

## Core Enumerations

### Error Codes

#### EnumCoreErrorCode

**Location**: `omnibase_core.enums.enum_core_error_code`

**Purpose**: Standard error codes for ONEX framework.

```python
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

### Handler Enums

Handler enums provide typed classifications for handler systems in the ONEX framework.

#### EnumHandlerTypeCategory

**Location**: `omnibase_core.enums.enum_handler_type_category`

**Purpose**: Behavioral classification of handlers (pure vs impure, deterministic vs non-deterministic).

**Added**: v0.4.0 (OMN-1085)

```python
from omnibase_core.enums import EnumHandlerTypeCategory

# Classify handler behavior
if category == EnumHandlerTypeCategory.COMPUTE:
    # Pure, deterministic - safe to cache
    result = cache.get_or_compute(key, handler.execute)
elif category == EnumHandlerTypeCategory.EFFECT:
    # Has side effects - needs idempotency checks
    if not is_idempotent_request(request):
        result = handler.execute(request)
```

**Available Categories**:

| Category | Pure (no I/O) | Deterministic | Use Case |
|----------|---------------|---------------|----------|
| `COMPUTE` | Yes | Yes | Caching, parallel execution |
| `EFFECT` | No | N/A | I/O operations, external systems |
| `NONDETERMINISTIC_COMPUTE` | Yes | No | Random, time-based computations |

**Helper Methods**:
- `values()` - Get all category values as strings
- `assert_exhaustive(value)` - Ensure exhaustive match handling

**See Also**: [EnumNodeKind](#enumnodekind), [EnumHandlerType](#enumhandlertype)

---

#### EnumHandlerCapability

**Location**: `omnibase_core.enums.enum_handler_capability`

**Purpose**: Unified handler capabilities that span all node types.

**Added**: v0.4.0 (OMN-1085)

```python
from omnibase_core.enums import EnumHandlerCapability

# Declare handler capabilities
capabilities = {
    EnumHandlerCapability.CACHE,
    EnumHandlerCapability.RETRY,
    EnumHandlerCapability.IDEMPOTENT,
}

# Check capability before applying optimization
if EnumHandlerCapability.CACHE in handler.capabilities:
    result = cache.get_or_compute(key, handler.execute)
```

**Available Capabilities**:

- `TRANSFORM` - Can transform data between formats
- `VALIDATE` - Can validate input/output data
- `CACHE` - Supports caching of results
- `RETRY` - Supports automatic retry on transient failures
- `BATCH` - Supports batch processing of multiple items
- `STREAM` - Supports streaming data processing
- `ASYNC` - Supports asynchronous execution
- `IDEMPOTENT` - Operation is idempotent (safe to retry)

**Capability Compatibility Matrix**:

| Capability | COMPUTE | EFFECT | NONDETERMINISTIC |
|------------|---------|--------|------------------|
| CACHE | Yes | Caution* | No |
| RETRY | Yes | Caution* | Yes |
| IDEMPOTENT | Always | Must check | Always |

*Caution: EFFECT handlers with CACHE or RETRY should also declare IDEMPOTENT.

**See Also**: [EnumHandlerTypeCategory](#enumhandlertypecategory), [EnumComputeCapability](#enumcomputecapability), [EnumEffectCapability](#enumeffectcapability)

---

#### EnumComputeCapability

**Location**: `omnibase_core.enums.enum_compute_capability`

**Purpose**: Capabilities specific to COMPUTE nodes in the four-node architecture.

**Added**: v0.4.0 (OMN-1085)

```python
from omnibase_core.enums import EnumComputeCapability

# Check if a compute handler supports transformation
if EnumComputeCapability.TRANSFORM in handler.capabilities:
    result = handler.transform(input_data)
```

**Available Capabilities**:

- `TRANSFORM` - Data transformation operations
- `VALIDATE` - Data validation operations

**Helper Methods**:
- `values()` - Get all capability values as strings
- `assert_exhaustive(value)` - Ensure exhaustive match handling

**See Also**: [EnumHandlerCapability](#enumhandlercapability), [EnumEffectCapability](#enumeffectcapability)

---

#### EnumEffectCapability

**Location**: `omnibase_core.enums.enum_effect_capability`

**Purpose**: Capabilities specific to EFFECT nodes in the four-node architecture.

**Added**: v0.4.0 (OMN-1085)

```python
from omnibase_core.enums import EnumEffectCapability

# Check if an effect handler supports HTTP operations
if EnumEffectCapability.HTTP in handler.capabilities:
    response = handler.http_request(url, method="GET")
```

**Available Capabilities**:

- `HTTP` - HTTP/REST API interactions
- `DB` - Database operations (SQL, NoSQL)
- `KAFKA` - Apache Kafka message queue operations
- `FILESYSTEM` - File system read/write operations

**Helper Methods**:
- `values()` - Get all capability values as strings
- `assert_exhaustive(value)` - Ensure exhaustive match handling

**See Also**: [EnumHandlerCapability](#enumhandlercapability), [EnumComputeCapability](#enumcomputecapability)

---

#### EnumHandlerCommandType

**Location**: `omnibase_core.enums.enum_handler_command_type`

**Purpose**: Typed command identifiers for handler operations.

**Added**: v0.4.0 (OMN-1085)

```python
from omnibase_core.enums import EnumHandlerCommandType

# Dispatch handler commands with type safety
match command:
    case EnumHandlerCommandType.EXECUTE:
        result = handler.execute(input_data)
    case EnumHandlerCommandType.VALIDATE:
        errors = handler.validate(input_data)
    case EnumHandlerCommandType.DRY_RUN:
        preview = handler.dry_run(input_data)
    case _:
        EnumHandlerCommandType.assert_exhaustive(command)
```

**Execution Commands**:
- `EXECUTE` - Run the handler's primary operation
- `VALIDATE` - Validate input data without executing
- `DRY_RUN` - Simulate execution without side effects
- `ROLLBACK` - Undo a previous operation (EFFECT handlers only)

**Introspection Commands**:
- `DESCRIBE` - Return handler capabilities and metadata
- `HEALTH_CHECK` - Verify handler is operational

**Configuration Commands**:
- `CONFIGURE` - Update handler settings
- `RESET` - Restore handler to initial state

**See Also**: [EnumHandlerType](#enumhandlertype), [EnumHandlerTypeCategory](#enumhandlertypecategory)

---

#### EnumHandlerType

**Location**: `omnibase_core.enums.enum_handler_type`

**Purpose**: Handler type classification by external system.

```python
from omnibase_core.enums import EnumHandlerType

# Register handler by type
registry.register(EnumHandlerType.HTTP, http_handler)
registry.register(EnumHandlerType.DATABASE, db_handler)
```

**Available Types**:
- `HTTP` - HTTP/REST API handlers
- `DATABASE` - Relational database handlers
- `KAFKA` - Apache Kafka message queue handlers
- `FILESYSTEM` - File system handlers
- `VAULT` - Secret management handlers
- `VECTOR_STORE` - Vector database handlers
- `GRAPH_DATABASE` - Graph database handlers
- `REDIS` - Redis cache handlers
- `EVENT_BUS` - Event bus handlers
- `LOCAL` - Local echo handler (dev/test only)

**See Also**: [EnumHandlerTypeCategory](#enumhandlertypecategory), [EnumHandlerCapability](#enumhandlercapability)

---

### Node Architecture Enums

#### EnumNodeKind

**Location**: `omnibase_core.enums.enum_node_kind`

**Purpose**: High-level architectural classification for ONEX nodes.

```python
from omnibase_core.enums import EnumNodeKind

# Route based on architectural role
if node_kind == EnumNodeKind.COMPUTE:
    route_to_compute_pipeline(node)
elif node_kind == EnumNodeKind.EFFECT:
    route_to_effect_pipeline(node)
```

**Core Four-Node Architecture Types**:

| Kind | Purpose | Examples |
|------|---------|----------|
| `EFFECT` | External interactions (I/O) | API calls, database ops, file system |
| `COMPUTE` | Data processing & transformation | Calculations, validations, data mapping |
| `REDUCER` | State aggregation & management | State machines, accumulators |
| `ORCHESTRATOR` | Workflow coordination | Multi-step workflows, parallel execution |

**Infrastructure Types**:
- `RUNTIME_HOST` - Runtime host nodes that manage node lifecycle

**Helper Methods**:
- `is_core_node_type(node_kind)` - Check if it's a core 4-node architecture type
- `is_infrastructure_type(node_kind)` - Check if it's an infrastructure type

**See Also**: [EnumNodeType](#enumnodetype), [EnumHandlerTypeCategory](#enumhandlertypecategory), [Migration Guide](../../guides/ENUM_NODE_KIND_MIGRATION.md)

---

#### EnumNodeType

**Location**: `omnibase_core.enums.enum_node_type`

**Purpose**: Specific node implementation type classification.

```python
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

```python
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

```python
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

```python
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

### Execution Status

#### EnumExecutionStatus

**Location**: `omnibase_core.enums.enum_execution_status`

**Purpose**: Canonical execution status for ONEX lifecycle tracking.

**Updated**: v0.6.4 (OMN-1310) - Consolidated from multiple status enums.

```python
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

status = EnumExecutionStatus.SUCCESS
```

#### Available Statuses

**Note**: All values are lowercase strings.

- `PENDING` = "pending" - Execution is queued but not yet started
- `RUNNING` = "running" - Execution is in progress
- `COMPLETED` = "completed" - Execution finished (generic completion)
- `SUCCESS` = "success" - Execution completed successfully
- `FAILED` = "failed" - Execution failed with an error
- `SKIPPED` = "skipped" - Execution was skipped
- `CANCELLED` = "cancelled" - Execution was cancelled by user or system
- `TIMEOUT` = "timeout" - Execution exceeded time limit
- `PARTIAL` = "partial" - Execution partially completed (some steps succeeded)

**Helper Methods**:
- `is_terminal(status)` - Returns True if execution has finished
- `is_active(status)` - Returns True if status is RUNNING or PENDING
- `is_successful(status)` - Returns True if status is SUCCESS or COMPLETED
- `is_failure(status)` - Returns True if status is FAILED or TIMEOUT
- `is_running(status)` - Returns True if status is RUNNING
- `is_cancelled(status)` - Returns True if status is CANCELLED
- `is_skipped(status)` - Returns True if status is SKIPPED
- `is_partial(status)` - Returns True if status is PARTIAL
- `to_base_status()` - Convert to EnumBaseStatus for universal operations
- `from_base_status(base_status)` - Create from EnumBaseStatus

**CANCELLED State Semantics**:

The `CANCELLED` status has special semantics that distinguish it from both success and failure states:

- **Terminal**: CANCELLED is a terminal state (`is_terminal()` returns True) - execution has finished and will not continue
- **Not a success**: `is_successful()` returns False - the execution did not complete its intended work
- **Not a failure**: `is_failure()` returns False - no error occurred; cancellation was intentional
- **Intentional termination**: Represents user or system-initiated cancellation, not an error condition

This distinction is important for:
1. **Metrics/reporting**: CANCELLED executions should not count as failures in error rates
2. **Retry logic**: CANCELLED tasks should not automatically retry (unlike FAILED or TIMEOUT)
3. **Billing/quotas**: CANCELLED work may warrant different accounting than completed or failed work

```python
# Correct handling of CANCELLED state
status = EnumExecutionStatus.CANCELLED

# Terminal check includes CANCELLED
assert EnumExecutionStatus.is_terminal(status)  # True

# Success/failure checks exclude CANCELLED
assert not EnumExecutionStatus.is_successful(status)  # Not a success
assert not EnumExecutionStatus.is_failure(status)     # Not a failure

# Use is_cancelled for explicit cancellation handling
if EnumExecutionStatus.is_cancelled(status):
    log.info("Execution was cancelled by user/system")
```

### Workflow Status

#### EnumWorkflowStatus

**Location**: `omnibase_core.enums.enum_workflow_status`

**Purpose**: Canonical workflow status for ONEX workflow lifecycle.

**Updated**: v0.6.4 (OMN-1310) - Consolidated from EnumWorkflowState and enum_workflow_coordination.EnumWorkflowStatus.

```python
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus

status = EnumWorkflowStatus.RUNNING
```

#### Available Statuses

**Note**: All values are lowercase strings.

- `PENDING` = "pending" - Workflow is queued but not yet started
- `RUNNING` = "running" - Workflow is actively executing
- `COMPLETED` = "completed" - Workflow finished successfully
- `FAILED` = "failed" - Workflow terminated due to an error
- `CANCELLED` = "cancelled" - Workflow was manually or programmatically cancelled
- `PAUSED` = "paused" - Workflow execution is temporarily suspended

**Helper Methods**:
- `is_terminal(status)` - Returns True if workflow has finished (COMPLETED, FAILED, CANCELLED)
- `is_active(status)` - Returns True if workflow is in progress (PENDING, RUNNING, PAUSED)
- `is_successful(status)` - Returns True if status is COMPLETED
- `is_error_state(status)` - Returns True if status is FAILED

**CANCELLED State Semantics**:

The `CANCELLED` status in workflows follows the same semantics as execution status:

- **Terminal**: CANCELLED is a terminal state - the workflow has finished and will not continue
- **Not a success**: `is_successful()` returns False - the workflow did not complete its intended work
- **Not a failure**: `is_error_state()` returns False - no error occurred; cancellation was intentional
- **Intentional termination**: Represents user or system-initiated cancellation, not an error condition

```python
# Correct handling of CANCELLED workflow state
status = EnumWorkflowStatus.CANCELLED

# Terminal check includes CANCELLED
assert EnumWorkflowStatus.is_terminal(status)  # True

# Success/error checks exclude CANCELLED
assert not EnumWorkflowStatus.is_successful(status)   # Not a success
assert not EnumWorkflowStatus.is_error_state(status)  # Not an error

# CANCELLED is a clean termination, not a failure
```

---

### Operation Status

#### EnumOperationStatus

**Location**: `omnibase_core.enums.enum_operation_status`

**Purpose**: Canonical operation status for API and service operations.

**Updated**: v0.6.4 (OMN-1310) - Consolidated from enum_execution.EnumOperationStatus.

```python
from omnibase_core.enums.enum_operation_status import EnumOperationStatus

status = EnumOperationStatus.SUCCESS
```

#### Available Statuses

**Note**: All values are lowercase strings.

- `SUCCESS` = "success" - Operation completed successfully
- `FAILED` = "failed" - Operation failed with an error
- `IN_PROGRESS` = "in_progress" - Operation is currently executing
- `CANCELLED` = "cancelled" - Operation was cancelled
- `PENDING` = "pending" - Operation is queued but not started
- `TIMEOUT` = "timeout" - Operation exceeded time limit

**Helper Methods** (instance methods):
- `is_terminal()` - Returns True if operation has finished (SUCCESS, FAILED, CANCELLED, TIMEOUT)
- `is_active()` - Returns True if operation is in progress (IN_PROGRESS, PENDING)
- `is_successful()` - Returns True if status is SUCCESS
- `to_base_status()` - Convert to EnumBaseStatus for universal operations
- `from_base_status(base_status)` - Create from EnumBaseStatus (class method)

**CANCELLED State Semantics**:

The `CANCELLED` status in operations follows the same semantics as other status enums:

- **Terminal**: CANCELLED is a terminal state - the operation has finished
- **Not a success**: `is_successful()` returns False
- **Distinct from failure**: CANCELLED represents intentional termination, not an error

```python
# Correct handling of CANCELLED operation state
status = EnumOperationStatus.CANCELLED

# Terminal check includes CANCELLED
assert status.is_terminal()  # True

# Success check excludes CANCELLED
assert not status.is_successful()  # Not a success

# CANCELLED is distinct from FAILED
assert status != EnumOperationStatus.FAILED
```

---

### Message Roles

#### EnumMessageRole

**Location**: `omnibase_core.enums.enum_message_role`

**Purpose**: Message roles in communication.

```python
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

```python
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

```python
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

```python
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

```python
from omnibase_core.enums.enum_health_status import EnumHealthStatus

def check_health(health_status: EnumHealthStatus) -> bool:
    """Check if node is healthy."""
    return health_status in [EnumHealthStatus.HEALTHY, EnumHealthStatus.DEGRADED]

# Usage
if check_health(node.health_status):
    print("Node is operational")
```

### Enum Iteration

```python
from omnibase_core.enums.enum_workflow_execution import EnumActionType

def get_all_action_types() -> List[str]:
    """Get all available action types."""
    return [action_type.value for action_type in EnumActionType]

# Usage
available_actions = get_all_action_types()
print(f"Available actions: {available_actions}")
```

### Enum Mapping

```python
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

# Map status to HTTP status codes
STATUS_TO_HTTP = {
    EnumExecutionStatus.SUCCESS: 200,
    EnumExecutionStatus.FAILED: 500,
    EnumExecutionStatus.TIMEOUT: 408,
    EnumExecutionStatus.CANCELLED: 499,
    EnumExecutionStatus.RUNNING: 202,
    EnumExecutionStatus.PENDING: 202
}

def get_http_status(operation_status: EnumExecutionStatus) -> int:
    """Get HTTP status code for operation status."""
    return STATUS_TO_HTTP.get(operation_status, 500)
```

### Custom Enum Methods

```python
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

```python
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

def convert_status_to_error_code(status: EnumExecutionStatus) -> EnumCoreErrorCode:
    """Convert operation status to error code."""
    status_to_error = {
        EnumExecutionStatus.FAILED: EnumCoreErrorCode.PROCESSING_ERROR,
        EnumExecutionStatus.TIMEOUT: EnumCoreErrorCode.TIMEOUT_ERROR,
        EnumExecutionStatus.CANCELLED: EnumCoreErrorCode.PROCESSING_ERROR
    }
    return status_to_error.get(status, EnumCoreErrorCode.PROCESSING_ERROR)
```

### Enum Validation in Error Handling

```python
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

```python
from functools import lru_cache
from omnibase_core.enums.enum_node_type import EnumNodeType

@lru_cache(maxsize=32)
def is_compute_node(node_type: EnumNodeType) -> bool:
    """Cache enum comparison for performance."""
    return node_type == EnumNodeType.COMPUTE_GENERIC
```

### Enum Lookup Optimization

```python
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
- [EnumNodeKind Migration Guide](../../guides/ENUM_NODE_KIND_MIGRATION.md) - Migration from EnumNodeType to EnumNodeKind
- [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Architecture overview

### Handler Enum Relationships

The handler enums form a cohesive system for classifying and managing handlers:

```text
EnumHandlerType          --> What external system? (HTTP, DATABASE, KAFKA...)
    |
    v
EnumHandlerTypeCategory  --> What computational behavior? (COMPUTE, EFFECT)
    |
    v
EnumHandlerCapability    --> What features? (CACHE, RETRY, IDEMPOTENT...)
    |
    v
EnumHandlerCommandType   --> What operation? (EXECUTE, VALIDATE, DRY_RUN...)
```

This classification hierarchy enables:
1. **Type-based routing**: Route to handlers by external system type
2. **Behavior-based optimization**: Apply caching/retry based on category
3. **Capability-based selection**: Choose handlers that support required features
4. **Type-safe dispatching**: Use typed commands instead of magic strings

### Status Enum Relationships (OMN-1310)

Status enums are organized by semantic category:

```text
EnumBaseStatus           --> Universal status primitives
    |                        (PENDING, RUNNING, COMPLETED, FAILED, etc.)
    |
    +-> EnumExecutionStatus    --> Task/job/step completion states
    |       includes: PENDING, RUNNING, SUCCESS, FAILED, CANCELLED,
    |                 TIMEOUT, SKIPPED, PARTIAL, COMPLETED
    |
    +-> EnumWorkflowStatus     --> Workflow lifecycle states
    |       includes: PENDING, RUNNING, COMPLETED, FAILED,
    |                 CANCELLED, PAUSED
    |
    +-> EnumOperationStatus    --> API/service operation outcomes
    |       includes: SUCCESS, FAILED, IN_PROGRESS, CANCELLED,
    |                 PENDING, TIMEOUT
    |
    +-> EnumHealthStatus       --> System/component health states
            includes: HEALTHY, DEGRADED, UNHEALTHY, CRITICAL,
                      UNKNOWN, WARNING, UNREACHABLE, etc.
```

**Key Semantic Rules**:
1. **CANCELLED is neither success nor failure** - Intentional termination, not an error
2. **All status enums use lowercase string values** - e.g., "running", not "RUNNING"
3. **Helper methods provide consistent classification** - `is_terminal()`, `is_successful()`, etc.
4. **Base status conversion available** - `to_base_status()` and `from_base_status()` methods

**Breaking Change Notice (v0.6.4)**: These enums consolidate and replace multiple
previous enum definitions. See module docstrings for migration guidance.
