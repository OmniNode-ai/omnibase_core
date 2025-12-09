# Contract-Driven NodeOrchestrator v1.0 Specification

> **Version**: 1.0.0
> **Date**: 2025-12-09
> **Status**: DRAFT - Ready for Implementation
> **Ticket**: [OMN-496](https://linear.app/omninode/issue/OMN-496)
> **Related**: [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](./CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md)

---

## Executive Summary

This document defines the **minimal v1.0 implementation** of contract-driven `NodeOrchestrator`. The goal is a stable foundation for workflow coordination that can be shipped safely and extended incrementally.

**v1.0 Scope**: Workflow-driven coordination with sequential/parallel/batch execution modes, dependency-aware step ordering, action emission pattern, and abort-on-first-failure semantics. No advanced branching, no distributed leases, no workflow persistence.

**Core Philosophy**: Pure workflow pattern - `(definition, steps) -> (result, actions[])`. Orchestrators coordinate work by emitting `ModelAction` instances for deferred execution by target nodes, following single-writer semantics with lease-based ownership.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [v1.0 Scope](#v10-scope)
3. [Core Models](#core-models)
4. [Enums](#enums)
5. [Contract Models](#contract-models)
6. [Execution Model](#execution-model)
7. [Action Emission Pattern](#action-emission-pattern)
8. [Error Model](#error-model-v10)
9. [NodeOrchestrator Behavior](#v10-nodeorchestrator-behavior)
10. [Contract Examples](#contract-examples)
11. [Implementation Plan](#implementation-plan)
12. [Acceptance Criteria](#acceptance-criteria)

---

## Design Principles

These principles apply to v1.0 and all future versions:

1. **Zero Custom Code**: Developers inherit from `NodeOrchestrator` without writing coordination logic
2. **Workflow-Driven**: Coordination is defined by workflow definitions and steps in YAML contracts
3. **Pure Workflow Pattern**: `(definition, steps) -> (result, actions[])` with no side effects
4. **Action Emission**: Orchestrators emit actions for deferred execution, not direct invocation
5. **Single-Writer Semantics**: Actions carry lease_id and epoch for ownership verification
6. **Typed Boundaries**: All public surfaces use Pydantic models
7. **Dependency-Aware**: Topological ordering ensures correct execution sequence

### Thread Safety and State Management

The workflow executor and coordination functions are designed to be **pure and stateless**:

- All workflow execution functions operate only on their input parameters
- Each `execute_workflow()` invocation operates on its own data without shared state
- `ModelAction` instances are immutable (`frozen=True`) after creation
- `ModelWorkflowCoordinationSubcontract` is immutable for thread-safe configuration access
- Safe for concurrent use from multiple threads

**Design Note**: The `ModelOrchestratorOutput` model is mutable to support progressive result building during workflow execution. Callers should treat it as read-only after receiving results.

---

## v1.0 Scope

### What's IN v1.0

| Feature | Description |
|---------|-------------|
| **3 Execution Modes** | `SEQUENTIAL`, `PARALLEL`, `BATCH` |
| **7 Step Types** | `compute`, `effect`, `reducer`, `orchestrator`, `conditional`, `parallel`, `custom` |
| **Dependency Resolution** | Topological ordering via Kahn's algorithm |
| **Cycle Detection** | DFS-based cycle detection before execution |
| **Action Emission** | `ModelAction` with lease semantics for target node execution |
| **Abort on First Failure** | Configurable via `error_action` per step |
| **Workflow Timeout** | Global `timeout_ms` on workflow definition |
| **Step Configuration** | Per-step `timeout_ms`, `retry_count`, `priority`, `enabled` |
| **Coordination Rules** | `parallel_execution_allowed`, `failure_recovery_strategy` |

### What's NOT in v1.0

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| **Conditional Branching** | v1.1 | Requires expression language for condition evaluation |
| **Streaming Mode** | v1.1 | Requires backpressure and windowing semantics |
| **Distributed Leases** | v1.2 | Adds distributed lock complexity |
| **Workflow Persistence** | v1.2 | Requires checkpoint/recovery infrastructure |
| **Compensation Actions** | v1.2 | Saga pattern needs careful design |
| **Dynamic Step Injection** | v1.3 | Runtime workflow modification is complex |
| **Cross-Workflow Dependencies** | v1.3 | Inter-workflow coordination requires registry |
| **Hierarchical Workflows** | v1.3 | Sub-workflow nesting needs scoping rules |

---

## Core Models

### ModelOrchestratorInput

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode


class ModelOrchestratorInput(BaseModel):
    """
    Input model for NodeOrchestrator operations.

    Strongly typed input wrapper for workflow coordination with comprehensive
    configuration for execution modes, parallelism, timeouts, and failure handling.
    """

    workflow_id: UUID = Field(..., description="Unique workflow identifier")
    steps: list[dict[str, Any]] = Field(
        ..., description="Simplified WorkflowStep representation"
    )
    operation_id: UUID = Field(
        default_factory=uuid4, description="Unique operation identifier"
    )
    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.SEQUENTIAL, description="Execution mode for workflow"
    )
    max_parallel_steps: int = Field(
        default=5, description="Maximum number of parallel steps"
    )
    global_timeout_ms: int = Field(
        default=300000, description="Global workflow timeout (5 minutes default)"
    )
    failure_strategy: str = Field(
        default="fail_fast", description="Strategy for handling failures"
    )
    load_balancing_enabled: bool = Field(
        default=False, description="Enable load balancing for operations"
    )
    dependency_resolution_enabled: bool = Field(
        default=True, description="Enable automatic dependency resolution"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional workflow metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=False,
    )
```

### ModelOrchestratorOutput

```python
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.service.model_custom_fields import ModelCustomFields


class ModelOrchestratorOutput(BaseModel):
    """
    Type-safe orchestrator output.

    Provides structured output storage for orchestrator execution
    results with type safety and validation.
    """

    # Execution summary
    execution_status: str = Field(default=..., description="Overall execution status")
    execution_time_ms: int = Field(
        default=..., description="Total execution time in milliseconds"
    )
    start_time: str = Field(default=..., description="Execution timestamp (ISO format)")
    end_time: str = Field(default=..., description="Execution timestamp (ISO format)")

    # Step results
    completed_steps: list[str] = Field(
        default_factory=list, description="List of completed step IDs"
    )
    failed_steps: list[str] = Field(
        default_factory=list, description="List of failed step IDs"
    )
    skipped_steps: list[str] = Field(
        default_factory=list, description="List of skipped step IDs"
    )

    # Step outputs
    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Outputs from each step"
    )

    # Final outputs
    final_result: Any | None = Field(default=None, description="Final orchestration result")
    output_variables: dict[str, Any] = Field(
        default_factory=dict, description="Output variables from the orchestration"
    )

    # Error information
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of errors (each with 'step_id', 'error_type', 'message')"
    )

    # Metrics
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Performance metrics"
    )

    # Parallel execution tracking
    parallel_executions: int = Field(
        default=0, description="Number of parallel execution batches completed"
    )

    # Actions tracking
    actions_emitted: list[Any] = Field(
        default_factory=list, description="List of actions emitted during workflow execution"
    )

    # Custom outputs
    custom_outputs: ModelCustomFields | None = Field(
        default=None, description="Custom output fields for orchestrator-specific data"
    )
```

### ModelAction

```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumActionType


class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Represents an Action emitted by the Orchestrator to Compute/Reducer nodes
    with single-writer semantics enforced via lease_id and epoch.

    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access.
    """

    action_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this action"
    )

    action_type: EnumActionType = Field(
        default=..., description="Type of action for execution routing"
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for action execution",
        min_length=1,
        max_length=100,
    )

    payload: dict[str, Any] = Field(
        default_factory=dict, description="Action payload data"
    )

    dependencies: list[UUID] = Field(
        default_factory=list, description="List of action IDs this action depends on"
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Execution timeout in milliseconds",
        ge=100,
        le=300000,
    )

    # Lease management for single-writer semantics
    lease_id: UUID = Field(
        default=..., description="Lease ID proving Orchestrator ownership"
    )

    epoch: int = Field(
        default=...,
        description="Monotonically increasing version number",
        ge=0,
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for action execution"
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when action was created"
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )
```

### ModelWorkflowStep

```python
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelWorkflowStep(BaseModel):
    """
    Strongly-typed workflow step definition.

    Replaces dict[str, str | int | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for workflow execution.
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
    }

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking workflow step across operations",
    )

    step_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this workflow step"
    )

    step_name: str = Field(
        default=...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=200,
    )

    step_type: Literal[
        "compute", "effect", "reducer", "orchestrator", "conditional", "parallel", "custom"
    ] = Field(default=..., description="Type of workflow step execution")

    # Execution configuration
    timeout_ms: int = Field(
        default=30000,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=300000,
    )

    retry_count: int = Field(
        default=3,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    # Conditional execution
    enabled: bool = Field(default=True, description="Whether this step is enabled")

    skip_on_failure: bool = Field(
        default=False, description="Whether to skip if previous steps failed"
    )

    # Error handling
    continue_on_error: bool = Field(
        default=False, description="Whether to continue workflow if this step fails"
    )

    error_action: Literal["stop", "continue", "retry", "compensate"] = Field(
        default="stop", description="Action to take when step fails"
    )

    # Performance requirements
    max_memory_mb: int | None = Field(
        default=None, description="Maximum memory usage in megabytes", ge=1, le=32768
    )

    max_cpu_percent: int | None = Field(
        default=None, description="Maximum CPU usage percentage", ge=1, le=100
    )

    # Priority and ordering
    priority: int = Field(
        default=100,
        description="Step execution priority (higher = more priority)",
        ge=1,
        le=1000,
    )

    order_index: int = Field(
        default=0, description="Order index for step execution sequence", ge=0
    )

    # Dependencies
    depends_on: list[UUID] = Field(
        default_factory=list, description="List of step IDs this step depends on"
    )

    # Parallel execution
    parallel_group: str | None = Field(
        default=None, description="Group identifier for parallel execution", max_length=100
    )

    max_parallel_instances: int = Field(
        default=1, description="Maximum parallel instances of this step", ge=1, le=100
    )
```

---

## Enums

### EnumExecutionMode

```python
from enum import Enum


class EnumExecutionMode(Enum):
    """Execution modes for workflow steps."""

    SEQUENTIAL = "sequential"   # Steps execute one after another
    PARALLEL = "parallel"       # Independent steps execute concurrently
    CONDITIONAL = "conditional" # v1.1+: Steps execute based on conditions
    BATCH = "batch"             # Steps grouped into batches
    STREAMING = "streaming"     # v1.1+: Continuous streaming execution
```

### EnumWorkflowState

```python
from enum import Enum


class EnumWorkflowState(Enum):
    """Workflow execution states."""

    PENDING = "pending"       # Workflow created, not yet started
    RUNNING = "running"       # Workflow currently executing
    PAUSED = "paused"         # Workflow paused (v1.2+)
    COMPLETED = "completed"   # Workflow finished successfully
    FAILED = "failed"         # Workflow failed
    CANCELLED = "cancelled"   # Workflow cancelled (v1.2+)
```

### EnumActionType

```python
from enum import Enum


class EnumActionType(Enum):
    """Types of Actions for orchestrated execution."""

    COMPUTE = "compute"       # Target NodeCompute
    EFFECT = "effect"         # Target NodeEffect
    REDUCE = "reduce"         # Target NodeReducer
    ORCHESTRATE = "orchestrate"  # Target NodeOrchestrator (sub-workflow)
    CUSTOM = "custom"         # Custom action type
```

### EnumFailureRecoveryStrategy

```python
from enum import Enum


class EnumFailureRecoveryStrategy(str, Enum):
    """Failure recovery strategies."""

    RETRY = "RETRY"           # Retry the failed step
    ROLLBACK = "ROLLBACK"     # Rollback to previous checkpoint (v1.2+)
    COMPENSATE = "COMPENSATE" # Execute compensation actions (v1.2+)
    ABORT = "ABORT"           # Abort entire workflow
```

### EnumBranchCondition

```python
from enum import Enum


class EnumBranchCondition(Enum):
    """Conditional branching types (v1.1+)."""

    IF_TRUE = "if_true"       # Branch if condition is true
    IF_FALSE = "if_false"     # Branch if condition is false
    IF_ERROR = "if_error"     # Branch if step errored
    IF_SUCCESS = "if_success" # Branch if step succeeded
    IF_TIMEOUT = "if_timeout" # Branch if step timed out
    CUSTOM = "custom"         # Custom condition expression
```

---

## Contract Models

### ModelWorkflowDefinition

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ..., description="Model version (MUST be provided in YAML contract)"
    )

    workflow_metadata: ModelWorkflowDefinitionMetadata = Field(
        default=..., description="Workflow metadata"
    )

    execution_graph: ModelExecutionGraph = Field(
        default=..., description="Execution graph for the workflow"
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=lambda: ModelCoordinationRules(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Rules for workflow coordination",
    )
```

### ModelWorkflowDefinitionMetadata

```python
from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowDefinitionMetadata(BaseModel):
    """Metadata for a workflow definition."""

    version: ModelSemVer = Field(
        ..., description="Model version (MUST be provided in YAML contract)"
    )

    workflow_name: str = Field(default=..., description="Name of the workflow")

    workflow_version: ModelSemVer = Field(
        ..., description="Version of the workflow (MUST be provided in YAML contract)"
    )

    description: str = Field(default=..., description="Description of the workflow")

    execution_mode: str = Field(
        default="sequential",
        description="Execution mode: sequential, parallel, batch"
    )

    timeout_ms: int = Field(
        default=600000,
        description="Workflow timeout in milliseconds",
        ge=1000,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelCoordinationRules

```python
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCoordinationRules(BaseModel):
    """Rules for workflow coordination."""

    version: ModelSemVer = Field(
        ..., description="Model version (MUST be provided in YAML contract)"
    )

    synchronization_points: list[str] = Field(
        default_factory=list,
        description="Named synchronization points in the workflow",
    )

    parallel_execution_allowed: bool = Field(
        default=True, description="Whether parallel execution is allowed"
    )

    failure_recovery_strategy: EnumFailureRecoveryStrategy = Field(
        default=EnumFailureRecoveryStrategy.RETRY,
        description="Strategy for handling failures",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
```

### ModelWorkflowCoordinationSubcontract

```python
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflowCoordinationSubcontract(BaseModel):
    """
    Workflow Coordination Subcontract for ORCHESTRATOR nodes.

    Provides workflow orchestration, node coordination, and execution
    management capabilities. Immutable (frozen=True) for thread safety.
    """

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    version: ModelSemVer = Field(
        ..., description="Model version (MUST be provided in YAML contract)"
    )

    subcontract_name: str = Field(
        default="workflow_coordination_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: ModelSemVer = Field(
        ..., description="Version of the subcontract (MUST be provided in YAML contract)"
    )

    applicable_node_types: list[str] = Field(
        default=["ORCHESTRATOR"], description="Node types this subcontract applies to"
    )

    # Configuration
    max_concurrent_workflows: int = Field(
        default=10, description="Maximum concurrent workflows", ge=1, le=100
    )

    default_workflow_timeout_ms: int = Field(
        default=600000, description="Default workflow timeout", ge=60000, le=3600000
    )

    node_coordination_timeout_ms: int = Field(
        default=30000, description="Node coordination timeout", ge=5000, le=300000
    )

    checkpoint_interval_ms: int = Field(
        default=60000, description="Checkpoint interval", ge=10000, le=600000
    )

    auto_retry_enabled: bool = Field(
        default=True, description="Whether automatic retry is enabled"
    )

    parallel_execution_enabled: bool = Field(
        default=True, description="Whether parallel execution is enabled"
    )

    workflow_persistence_enabled: bool = Field(
        default=True, description="Whether workflow state persistence is enabled"
    )

    # Failure recovery
    max_retries: int = Field(
        default=3, description="Maximum retries for failed operations", ge=0, le=10
    )

    retry_delay_ms: int = Field(
        default=2000, description="Delay between retries", ge=1000, le=60000
    )

    exponential_backoff: bool = Field(
        default=True, description="Whether to use exponential backoff"
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )
```

---

## Execution Model

### Execution Mode Semantics

#### SEQUENTIAL Execution

Steps execute in topological order, one at a time:

```text
Step A (no deps) → Step B (deps: A) → Step C (deps: B) → Step D (deps: B,C)
```

**Rules**:

1. Steps execute in dependency-resolved order (Kahn's algorithm)
2. Each step waits for completion before next step starts
3. Disabled steps are skipped entirely
4. Failed steps trigger `error_action` handling

#### PARALLEL Execution

Independent steps execute concurrently in waves:

```text
Wave 1: [Step A, Step B] (no deps)
    ↓ (both complete)
Wave 2: [Step C (deps: A), Step D (deps: B)]
    ↓ (both complete)
Wave 3: [Step E (deps: C, D)]
```

**Rules**:

1. Steps with met dependencies form execution waves
2. All steps in a wave execute concurrently via `asyncio.gather()`
3. Next wave starts only when current wave completes
4. Failed steps in a wave don't cancel sibling steps

#### BATCH Execution

Sequential execution with batch metadata for grouping:

```text
Batch of N steps executed sequentially with batch_size metadata
```

**Rules**:

1. Same as sequential but with batch metadata tracking
2. Useful for grouped operations with shared context

### Dependency Resolution

Dependencies are resolved using **Kahn's algorithm** for topological sorting:

```python
def get_execution_order(workflow_steps: list[ModelWorkflowStep]) -> list[UUID]:
    """
    Get topological execution order for workflow steps.

    Uses Kahn's algorithm:
    1. Build adjacency list and in-degree map
    2. Queue all nodes with in-degree 0
    3. Pop from queue, add to result, decrement neighbors' in-degrees
    4. Repeat until queue empty

    Raises:
        ModelOnexError: If workflow contains cycles
    """
```

### Cycle Detection

Cycles are detected using **DFS-based algorithm** before execution:

```python
def _has_dependency_cycles(workflow_steps: list[ModelWorkflowStep]) -> bool:
    """
    Check if workflow contains dependency cycles using DFS.

    Maintains:
    - visited: set of all visited nodes
    - rec_stack: set of nodes in current recursion path

    Cycle detected when neighbor is already in rec_stack.
    """
```

### Abort on First Failure

v1.0 supports configurable failure handling per step:

| `error_action` | Behavior |
|----------------|----------|
| `stop` | Abort workflow immediately |
| `continue` | Continue to next step |
| `retry` | Retry step (v1.0: uses `retry_count`) |
| `compensate` | v1.2+: Execute compensation action |

When `error_action == "stop"`:

```text
Step 1: OK      → Result preserved
Step 2: FAIL   → Error recorded, workflow aborts
Step 3: SKIPPED → Not executed
Step 4: SKIPPED → Not executed

Result: FAILED
```

---

## Action Emission Pattern

### Single-Writer Semantics

Orchestrators emit `ModelAction` instances with lease-based ownership:

```python
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeCompute",
    payload={
        "workflow_id": str(workflow_id),
        "step_id": str(step.step_id),
        "step_name": step.step_name,
    },
    dependencies=step.depends_on,
    priority=min(step.priority, 10),  # Capped to ModelAction's 1-10 range
    timeout_ms=step.timeout_ms,
    lease_id=uuid4(),  # Proves orchestrator ownership
    epoch=0,           # Monotonically increasing version
    retry_count=step.retry_count,
    metadata={
        "step_name": step.step_name,
        "correlation_id": str(step.correlation_id),
    },
)
```

### Action Type Mapping

Step types map to action types as follows:

| Step Type | Action Type | Target Node |
|-----------|-------------|-------------|
| `compute` | `COMPUTE` | `NodeCompute` |
| `effect` | `EFFECT` | `NodeEffect` |
| `reducer` | `REDUCE` | `NodeReducer` |
| `orchestrator` | `ORCHESTRATE` | `NodeOrchestrator` |
| `custom` | `CUSTOM` | `NodeCustom` |

### Action Immutability

`ModelAction` instances are **frozen** after creation:

- Cannot modify fields after instantiation
- Thread-safe for concurrent read access
- To modify, use `model_copy()`:

```python
# Increment retry count for retry attempt
new_action = action.model_copy(update={"retry_count": action.retry_count + 1})
```

---

## Error Model (v1.0)

v1.0 uses **string-based error tracking**:

```python
# In ModelOrchestratorOutput
errors: list[dict[str, str]] = Field(
    default_factory=list,
    description="List of errors (each with 'step_id', 'error_type', 'message')"
)
```

Error entries contain:

```python
{
    "step_id": "uuid-of-failed-step",
    "error_type": "validation_error",  # or "timeout", "compute_error", etc.
    "message": "Human-readable error description"
}
```

### Error Handling Flow

1. **ModelOnexError** - Expected ONEX errors with structured context
2. **Generic Exception** - Unexpected errors with full traceback logging
3. **Error Action** - Per-step `error_action` determines continuation

```python
try:
    # Execute step
    action = _create_action_for_step(step, workflow_id)
except ModelOnexError as e:
    # Handle expected ONEX errors
    failed_steps.append(str(step.step_id))
    if step.error_action == "stop":
        break
except Exception as e:
    # Handle unexpected errors
    failed_steps.append(str(step.step_id))
    logging.exception(f"Step '{step.step_name}' failed: {e}")
```

---

## v1.0 NodeOrchestrator Behavior

### Startup Behavior

When a `NodeOrchestrator` instance starts:

1. **Load Container**: Receive `ModelONEXContainer` for dependency injection
2. **Initialize Base**: Call `super().__init__(container)` for base class setup
3. **Load Contract**: Attempt to load `workflow_coordination` from node contract
4. **Set Definition**: If contract present, extract `workflow_definition`
5. **Ready State**: Node ready to process workflow inputs

### Runtime Behavior

When `process(ModelOrchestratorInput)` is called:

1. **Validate Definition**: Ensure `workflow_definition` is loaded
2. **Convert Steps**: Convert dict steps to `ModelWorkflowStep` instances
3. **Execute Workflow**: Call `execute_workflow_from_contract()`
4. **Build Output**: Convert `WorkflowExecutionResult` to `ModelOrchestratorOutput`
5. **Return**: Return typed output with actions and metrics

### Lifecycle

```text
┌─────────────────────┐
│   Container Init    │──▶ Receives ModelONEXContainer
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Contract Load     │──▶ Loads workflow_definition from contract
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│    Node Ready       │──▶ workflow_definition set, ready for processing
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│     process()       │──▶ Validates, executes workflow, emits actions
└─────────────────────┘
```

### Process Method Signature

```python
async def process(
    self,
    input_data: ModelOrchestratorInput,
) -> ModelOrchestratorOutput:
    """
    Process workflow using workflow-driven coordination.

    Pure workflow pattern: Executes steps, emits actions for deferred execution.

    Args:
        input_data: Orchestrator input with workflow steps and configuration

    Returns:
        Orchestrator output with execution results and emitted actions

    Raises:
        ModelOnexError: If workflow definition not loaded or execution fails
    """
```

---

## Contract Examples

### Basic Data Processing Workflow

```yaml
# examples/contracts/orchestrator/data_processing_workflow_v1.yaml
node_type: ORCHESTRATOR
node_name: data_processing_orchestrator
node_version: "1.0.0"

workflow_coordination:
  version:
    major: 1
    minor: 0
    patch: 0
  subcontract_version:
    major: 1
    minor: 0
    patch: 0

  # Workflow definition
  workflow_definition:
    version:
      major: 1
      minor: 0
      patch: 0

    workflow_metadata:
      version:
        major: 1
        minor: 0
        patch: 0
      workflow_name: data_processing_pipeline
      workflow_version:
        major: 1
        minor: 0
        patch: 0
      description: "Multi-stage data processing workflow"
      execution_mode: sequential
      timeout_ms: 300000

    execution_graph:
      version:
        major: 1
        minor: 0
        patch: 0
      nodes:
        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "fetch_data_node"
          node_type: EFFECT
          dependencies: []

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "validate_schema_node"
          node_type: COMPUTE
          dependencies: ["fetch_data_node"]

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "transform_data_node"
          node_type: COMPUTE
          dependencies: ["validate_schema_node"]

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "persist_results_node"
          node_type: EFFECT
          dependencies: ["transform_data_node"]

    coordination_rules:
      version:
        major: 1
        minor: 0
        patch: 0
      parallel_execution_allowed: false
      failure_recovery_strategy: RETRY
      synchronization_points:
        - "after_validation"
        - "before_persist"
```

### Parallel Processing Workflow

```yaml
# examples/contracts/orchestrator/parallel_processing_v1.yaml
node_type: ORCHESTRATOR
node_name: parallel_processor
node_version: "1.0.0"

workflow_coordination:
  version:
    major: 1
    minor: 0
    patch: 0
  subcontract_version:
    major: 1
    minor: 0
    patch: 0

  max_concurrent_workflows: 5
  parallel_execution_enabled: true

  workflow_definition:
    version:
      major: 1
      minor: 0
      patch: 0

    workflow_metadata:
      version:
        major: 1
        minor: 0
        patch: 0
      workflow_name: parallel_etl_pipeline
      workflow_version:
        major: 1
        minor: 0
        patch: 0
      description: "Parallel ETL with independent source extraction"
      execution_mode: parallel
      timeout_ms: 600000

    execution_graph:
      version:
        major: 1
        minor: 0
        patch: 0
      nodes:
        # Wave 1: Independent extractions (parallel)
        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "extract_source_a"
          node_type: EFFECT
          dependencies: []

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "extract_source_b"
          node_type: EFFECT
          dependencies: []

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "extract_source_c"
          node_type: EFFECT
          dependencies: []

        # Wave 2: Transforms depend on their extracts
        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "transform_a"
          node_type: COMPUTE
          dependencies: ["extract_source_a"]

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "transform_b"
          node_type: COMPUTE
          dependencies: ["extract_source_b"]

        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "transform_c"
          node_type: COMPUTE
          dependencies: ["extract_source_c"]

        # Wave 3: Merge depends on all transforms
        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "merge_results"
          node_type: REDUCER
          dependencies:
            - "transform_a"
            - "transform_b"
            - "transform_c"

        # Wave 4: Load depends on merge
        - version:
            major: 1
            minor: 0
            patch: 0
          node_id: "load_to_warehouse"
          node_type: EFFECT
          dependencies: ["merge_results"]

    coordination_rules:
      version:
        major: 1
        minor: 0
        patch: 0
      parallel_execution_allowed: true
      failure_recovery_strategy: ABORT
```

### Usage Example

```python
from uuid import uuid4

from omnibase_core.nodes import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode


class NodeDataPipeline(NodeOrchestrator):
    """Data pipeline orchestrator - all logic from contract."""
    pass


# Create node from container
container = ModelONEXContainer(...)
node = NodeDataPipeline(container)

# Set workflow definition (manual injection for this example)
node.workflow_definition = ModelWorkflowDefinition(...)

# Define workflow steps
steps_config = [
    {
        "step_name": "Fetch Data",
        "step_type": "effect",
        "timeout_ms": 10000,
    },
    {
        "step_name": "Validate Schema",
        "step_type": "compute",
        "depends_on": [fetch_step_id],
        "timeout_ms": 5000,
    },
    {
        "step_name": "Transform Data",
        "step_type": "compute",
        "depends_on": [validate_step_id],
        "timeout_ms": 15000,
    },
    {
        "step_name": "Persist Results",
        "step_type": "effect",
        "depends_on": [transform_step_id],
        "timeout_ms": 10000,
    },
]

# Execute workflow
input_data = ModelOrchestratorInput(
    workflow_id=uuid4(),
    steps=steps_config,
    execution_mode=EnumExecutionMode.SEQUENTIAL,
)

result = await node.process(input_data)

print(f"Status: {result.execution_status}")
print(f"Completed: {len(result.completed_steps)} steps")
print(f"Actions emitted: {len(result.actions_emitted)}")
print(f"Execution time: {result.execution_time_ms}ms")
```

---

## Implementation Plan

### Phase 1: Core Enums (~1 day)

| Task | File | Priority |
|------|------|----------|
| EnumExecutionMode | `enums/enum_workflow_execution.py` | P0 |
| EnumWorkflowState | `enums/enum_workflow_execution.py` | P0 |
| EnumActionType | `enums/enum_workflow_execution.py` | P0 |
| EnumBranchCondition | `enums/enum_workflow_execution.py` | P0 |
| EnumFailureRecoveryStrategy | `enums/enum_workflow_coordination.py` | P0 |

### Phase 2: Core Models (~3 days)

| Task | File | Priority |
|------|------|----------|
| ModelOrchestratorInput | `models/orchestrator/model_orchestrator_input.py` | P0 |
| ModelOrchestratorOutput | `models/orchestrator/model_orchestrator_output.py` | P0 |
| ModelAction | `models/orchestrator/model_action.py` | P0 |
| ModelWorkflowStep | `models/contracts/model_workflow_step.py` | P0 |
| ModelDeclarativeWorkflowResult | `models/workflow/execution/model_declarative_workflow_result.py` | P0 |

### Phase 3: Contract Models (~2 days)

| Task | File | Priority |
|------|------|----------|
| ModelWorkflowDefinition | `models/contracts/subcontracts/model_workflow_definition.py` | P0 |
| ModelWorkflowDefinitionMetadata | `models/contracts/subcontracts/model_workflow_definition_metadata.py` | P0 |
| ModelCoordinationRules | `models/contracts/subcontracts/model_coordination_rules.py` | P0 |
| ModelExecutionGraph | `models/contracts/subcontracts/model_execution_graph.py` | P0 |
| ModelWorkflowNode | `models/contracts/subcontracts/model_workflow_node.py` | P0 |
| ModelWorkflowCoordinationSubcontract | `models/contracts/subcontracts/model_workflow_coordination_subcontract.py` | P0 |

### Phase 4: Execution (~3 days)

| Task | File | Priority |
|------|------|----------|
| workflow_executor.py | `utils/workflow_executor.py` | P0 |
| MixinWorkflowExecution | `mixins/mixin_workflow_execution.py` | P0 |
| NodeOrchestrator | `nodes/node_orchestrator.py` | P0 |

### Phase 5: Testing (~3 days)

| Task | File | Priority |
|------|------|----------|
| Unit tests for enums | `tests/unit/enums/test_workflow_*.py` | P0 |
| Unit tests for models | `tests/unit/models/orchestrator/test_*.py` | P0 |
| Unit tests for executor | `tests/unit/utils/test_workflow_executor.py` | P0 |
| Integration tests | `tests/integration/test_orchestrator_workflow.py` | P0 |

### Total Estimate

- **Files**: ~20 files
- **Code**: ~1500 lines
- **Tests**: ~800 lines
- **Timeline**: 12 working days

---

## Acceptance Criteria

### Functional Requirements

- [ ] `ModelWorkflowDefinition` validates contracts with proper Pydantic constraints
- [ ] All 3 execution modes implemented (SEQUENTIAL, PARALLEL, BATCH)
- [ ] All 7 step types supported (compute, effect, reducer, orchestrator, conditional, parallel, custom)
- [ ] Dependency resolution via Kahn's algorithm for topological ordering
- [ ] Cycle detection via DFS before execution
- [ ] Action emission with lease_id and epoch for single-writer semantics
- [ ] Per-step `error_action` handling (stop, continue, retry)
- [ ] Workflow timeout enforcement via `timeout_ms`
- [ ] Disabled steps properly skipped (not marked as failed)

### Type Safety Requirements

- [ ] All models use Pydantic with appropriate `ConfigDict`
- [ ] `ModelAction` is frozen for thread safety
- [ ] `ModelWorkflowCoordinationSubcontract` is frozen for configuration immutability
- [ ] mypy --strict passes with zero errors
- [ ] All enums are properly typed string enums

### Testing Requirements

- [ ] Unit tests for each enum
- [ ] Unit tests for each model
- [ ] Unit tests for workflow executor (sequential, parallel, batch)
- [ ] Unit tests for cycle detection
- [ ] Unit tests for topological ordering
- [ ] Integration test with example contracts
- [ ] 90%+ code coverage for orchestrator module

### Documentation Requirements

- [ ] Example contracts in `examples/contracts/orchestrator/`
- [ ] API documentation for public functions
- [ ] Thread safety documentation for models
- [ ] Migration guide from code-driven orchestration

---

## References

- **NodeCompute Spec**: [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](./CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md)
- **ONEX Architecture**: [ONEX_FOUR_NODE_ARCHITECTURE.md](./ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Example Contract**: data_processing_workflow_v1.yaml (to be created in examples/contracts/orchestrator/)
- **Linear Issue**: [OMN-496](https://linear.app/omninode/issue/OMN-496)
- **NodeCompute Pattern**: [node_compute.py](../../src/omnibase_core/nodes/node_compute.py)
- **NodeReducer Pattern**: [node_reducer.py](../../src/omnibase_core/nodes/node_reducer.py)

---

**Last Updated**: 2025-12-09
**Version**: 1.0.0
**Status**: DRAFT - Ready for Implementation
