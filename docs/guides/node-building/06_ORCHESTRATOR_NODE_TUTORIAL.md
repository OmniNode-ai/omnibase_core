# ORCHESTRATOR Node Tutorial: Build a Data Processing Pipeline

**Reading Time**: 45 minutes
**Difficulty**: Advanced
**Prerequisites**: All other node tutorials (COMPUTE, EFFECT, REDUCER)

## What You'll Build

In this tutorial, you'll build a production-ready **Data Processing Pipeline Orchestrator** that:

- Coordinates multiple nodes (COMPUTE, EFFECT, REDUCER) in a workflow
- Supports three execution modes: SEQUENTIAL, PARALLEL, BATCH
- Implements action emission for deferred execution with ModelAction pattern
- Manages dependencies between workflow steps
- Uses lease-based single-writer semantics for distributed coordination
- Provides comprehensive workflow monitoring

## Execution Shape

> **Canonical Execution Shapes**: ORCHESTRATOR nodes support multiple patterns:
> - **Event to Orchestrator**: External events trigger workflow coordination
> - **Command to Orchestrator**: API/CLI commands initiate workflows
> - **Action to Effect**: Orchestrator emits Actions that Effect nodes execute
> ORCHESTRATOR nodes coordinate but do NOT perform direct I/O - they emit Actions.
> See [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) for the complete pattern.

## ⚠️ CRITICAL: ORCHESTRATOR Result Constraint

**ORCHESTRATOR nodes CANNOT return typed results** - they can only emit **events** and **intents**.

```python
# ✅ CORRECT - Return events and intents, NO result
return ModelHandlerOutput[None](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    events=[...],
    intents=[...],
    result=None,  # Must be None
)

# ❌ WRONG - Orchestrator cannot return result
return ModelHandlerOutput[dict](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    result={"status": "completed"},  # ERROR!
)
```

**Why?**
- **Separation of Concerns**: Orchestrators coordinate; COMPUTE nodes transform data
- **Only COMPUTE nodes return typed results**
- **Orchestrators communicate via events and intents, not direct results**

**Validation Error:**
```
ValueError: ORCHESTRATOR cannot set result - use events[] and intents[] only.
Only COMPUTE nodes return typed results.
```

See [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md#4-orchestrator-node) for detailed explanation.

---

**Why ORCHESTRATOR Nodes?**

ORCHESTRATOR nodes coordinate complex workflows in the ONEX architecture:
- Multi-step data processing pipelines
- Workflow coordination with dependencies
- Parallel execution of independent operations
- Conditional branching based on runtime state
- Load balancing across execution nodes
- Error recovery and compensation logic

**Tutorial Structure**:
1. Understand orchestration concepts (actions, workflows, execution modes)
2. Define workflow models and configuration
3. Implement the ORCHESTRATOR node with three execution modes
4. Add conditional branching and error handling
5. Write comprehensive tests
6. See real-world usage examples

---

## v0.4.0 Architecture

> **v0.4.0 Update**: `NodeOrchestrator` is now the PRIMARY workflow-driven implementation. The "Declarative" suffix has been removed because this IS the standard approach. All orchestrator nodes use YAML contracts for configuration with zero custom Python code for standard workflows.

### Key Changes in v0.4.0

| Before (v0.3.x) | After (v0.4.0) |
|-----------------|----------------|
| `NodeOrchestratorDeclarative` | `NodeOrchestrator` (primary) |
| Manual workflow setup | YAML contract-driven |
| Custom Python coordination | Workflow definitions |
| Multiple import paths | Single import: `from omnibase_core.nodes import NodeOrchestrator` |

### Import Patterns (v0.4.0+)

```python
# All node types - single import path
from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
    EnumBranchCondition,
)

# Container for dependency injection
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# ModelAction for workflow actions
from omnibase_core.models.orchestrator.model_action import ModelAction

# Workflow step model
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
```

---

## Workflow-Driven Architecture

The omnibase_core codebase provides **comprehensive YAML contract infrastructure** for building orchestrator workflows **without custom Python code**.

### Available Infrastructure (v0.4.0+)

| Component | Status | Description |
|-----------|--------|-------------|
| YAML Contract Models | Complete | Full Pydantic validation |
| Subcontract Composition | Complete | ModelContractOrchestrator |
| Runtime Executor Services | Complete | workflow_executor.py with MixinWorkflowExecution |
| NodeOrchestrator | Complete | Primary workflow-driven implementation |
| Documentation | Complete | Full tutorial and migration guides |

### Example YAML Contract

```yaml
# contracts/orchestrator_data_pipeline.yaml
node_type: ORCHESTRATOR
node_name: data_pipeline_orchestrator

workflow_coordination:
  execution_mode: sequential  # or parallel, batch
  max_parallel_branches: 4
  checkpoint_enabled: true
  rollback_enabled: true

  workflow_definition:
    execution_graph:
      steps:
        - step_id: fetch_data
          step_name: "Fetch Data from Sources"
          step_type: effect
          target_node_type: NodeDataFetcher
          timeout_ms: 10000

        - step_id: validate_data
          step_name: "Validate Data Quality"
          step_type: compute
          target_node_type: NodeDataValidator
          depends_on: [fetch_data]
          timeout_ms: 5000

        - step_id: aggregate_metrics
          step_name: "Aggregate Metrics"
          step_type: reducer
          target_node_type: NodeMetricsAggregator
          depends_on: [validate_data]
          timeout_ms: 8000
```

### When Custom Code IS Needed

Most orchestrator workflows require **ZERO custom Python code**. Custom code is only needed for:
- Custom conditional branching logic
- Advanced error recovery strategies
- Complex coordination patterns not supported by YAML

---

## Prerequisites Check

```bash
# Verify Poetry and environment
poetry --version
pwd  # Should end with /omnibase_core

# Install dependencies
poetry install

# Run existing orchestrator tests
poetry run pytest tests/unit/nodes/test_node_orchestrator.py -v --maxfail=1
```

If tests pass, you're ready to begin!

---

## Orchestration Concepts

### What is an Action?

An **action** is an Orchestrator-issued command that represents work to be done by a specific node type. Actions use the **ModelAction pattern** with lease management for single-writer semantics:

```python
from uuid import uuid4
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.nodes import EnumActionType

# Example: Action for COMPUTE operation
compute_action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeDataValidator",
    payload={"data": input_data},
    dependencies=[],  # No dependencies
    priority=1,
    timeout_ms=5000,
    lease_id=uuid4(),  # Orchestrator ownership proof
    epoch=1,  # Optimistic concurrency control
)

# Example: Action for EFFECT operation with dependency
effect_action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.EFFECT,
    target_node_type="NodeDatabaseWriter",
    payload={"data": processed_data},
    dependencies=[compute_action.action_id],  # Depends on compute
    priority=2,
    timeout_ms=10000,
    lease_id=uuid4(),  # Orchestrator ownership proof
    epoch=1,  # Optimistic concurrency control
)
```

**Key Points**:
- Actions represent "units of work" issued by the Orchestrator
- They can have dependencies on other actions
- The orchestrator emits actions and coordinates execution
- Actions enable deferred, dependency-aware execution
- Each action has a `lease_id` proving Orchestrator ownership
- The `epoch` field enables optimistic concurrency control

### Action Lease Management

Actions include **lease management** fields to ensure single-writer semantics and prevent concurrent modification conflicts:

**lease_id (UUID)**:
- Proves which Orchestrator instance owns this action
- Generated when the Orchestrator creates the action
- Must match for any updates or state changes
- Enables **single-writer semantics**: only the owning Orchestrator can modify the action
- Prevents multiple Orchestrators from conflicting on the same action

**epoch (int)**:
- Enables **optimistic concurrency control**
- Incremented each time the action is updated
- Prevents lost updates in distributed scenarios
- Must match expected value for updates to succeed

**Usage Example**:
```python
from uuid import uuid4
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.nodes import EnumActionType

# Orchestrator creates action with initial lease and epoch
orchestrator_lease_id = uuid4()
action = ModelAction(
    action_type=EnumActionType.COMPUTE,
    target_node_type="NodeDataProcessor",
    payload={"task": "process"},
    lease_id=orchestrator_lease_id,  # Ownership proof
    epoch=1,  # Initial epoch
)

# To modify a frozen action, use model_copy()
# Only the owning Orchestrator should update
updated_action = action.model_copy(update={
    "payload": {"task": "process", "status": "in_progress"},
    "epoch": 2,  # Incremented epoch
})

# Another Orchestrator cannot modify (lease_id mismatch)
# This update would be rejected in a distributed system:
# invalid_update = action.model_copy(update={
#     "lease_id": uuid4(),  # Different lease_id - REJECTED!
#     "epoch": 2,
# })
```

**Benefits**:
- **Safety**: Prevents concurrent modification by multiple Orchestrators
- **Consistency**: Ensures only authorized updates succeed
- **Traceability**: Lease ID tracks which Orchestrator owns each action
- **Conflict Prevention**: Epoch detects and prevents lost updates

### Workflow Steps

A **workflow step** groups related configuration for execution:

```python
from uuid import uuid4
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

step = ModelWorkflowStep(
    step_id=uuid4(),
    step_name="Validate and Process Data",
    step_type="compute",
    timeout_ms=30000,
    retry_count=3,
    depends_on=[],  # List of step IDs this step depends on
)
```

### Execution Modes

ORCHESTRATOR nodes support three execution modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **SEQUENTIAL** | Execute steps one after another | When order matters, dependencies exist |
| **PARALLEL** | Execute independent steps concurrently | Independent operations, maximize throughput |
| **BATCH** | Execute with load balancing and batching | High volume, resource-constrained scenarios |

### Dependency Graphs

The orchestrator builds a **dependency graph** to determine execution order:

```text
Step 1 (Validate) --+
                    +--> Step 3 (Aggregate)
Step 2 (Fetch) -----+

Step 3 (Aggregate) ----> Step 4 (Save)
```

Execution order: Steps 1 & 2 in parallel -> Step 3 -> Step 4

---

## Step 1: Define Workflow Input Model

**File**: `src/your_project/nodes/model_pipeline_orchestrator_input.py`

```python
"""Input model for data processing pipeline orchestrator."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.nodes import EnumExecutionMode


class ModelPipelineConfig(BaseModel):
    """Configuration for pipeline processing."""

    model_config = ConfigDict(extra="forbid")

    # Data source configuration
    data_source: str = Field(
        ...,
        description="Source identifier for data",
    )

    # Processing options
    validate_input: bool = Field(
        default=True,
        description="Whether to validate input data",
    )

    enable_caching: bool = Field(
        default=True,
        description="Whether to cache intermediate results",
    )

    parallel_processing: bool = Field(
        default=False,
        description="Whether to use parallel execution mode",
    )

    # Quality thresholds
    quality_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum quality score to proceed",
    )


class ModelPipelineOrchestratorInput(BaseModel):
    """
    Input for data processing pipeline orchestration.

    Defines the workflow configuration and execution parameters
    for coordinating a multi-step data pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    # Workflow identification
    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique workflow identifier",
    )

    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Operation correlation ID",
    )

    # Input data
    input_data: dict[str, object] = Field(
        ...,
        description="Input data to process through pipeline",
    )

    # Pipeline configuration
    config: ModelPipelineConfig = Field(
        default_factory=ModelPipelineConfig,
        description="Pipeline processing configuration",
    )

    # Execution mode
    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.SEQUENTIAL,
        description="Workflow execution mode",
    )

    # Failure handling
    failure_strategy: str = Field(
        default="fail_fast",
        description="How to handle step failures",
    )

    max_parallel_steps: int = Field(
        default=3,
        ge=1,
        description="Maximum parallel steps for PARALLEL mode",
    )
```

---

## Step 2: Implement the ORCHESTRATOR Node

### Using NodeOrchestrator Base Class

For workflow-driven orchestration, use `NodeOrchestrator` which provides all standard features:

**File**: `src/your_project/nodes/node_pipeline_orchestrator.py`

```python
"""
Data Processing Pipeline Orchestrator Node.

Coordinates multi-step data pipeline with validation, fetching,
processing, and storage via action emission and workflow coordination.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Any

from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.logging.logging_structured import emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .model_pipeline_orchestrator_input import ModelPipelineOrchestratorInput


class NodePipelineOrchestrator(NodeOrchestrator):
    """
    Data Processing Pipeline Orchestrator.

    Coordinates a multi-step data pipeline workflow:
    1. Validation (COMPUTE node)
    2. Data fetching (EFFECT node)
    3. Processing (COMPUTE node)
    4. Aggregation (REDUCER node)
    5. Storage (EFFECT node)

    Supports SEQUENTIAL, PARALLEL, and BATCH execution modes.

    Features (via NodeOrchestrator):
    - Workflow step execution
    - Action emission and coordination
    - Dependency resolution with topological ordering
    - Execution mode management (SEQUENTIAL, PARALLEL, BATCH)
    - Lease management for single-writer semantics
    - Cycle detection in workflow graphs
    - Error handling and recovery

    Thread Safety:
        NodePipelineOrchestrator instances are NOT thread-safe due to
        mutable workflow state. Each thread should have its own instance.
        See docs/guides/THREADING.md for patterns.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize the pipeline orchestrator.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)

        # Orchestrator configuration (bypass Pydantic validation for mutable attrs)
        object.__setattr__(self, "max_concurrent_workflows", 5)
        object.__setattr__(self, "default_step_timeout_ms", 30000)

        # Workflow tracking
        object.__setattr__(self, "active_workflows", {})
        object.__setattr__(self, "emitted_actions", {})

        emit_log_event(
            LogLevel.INFO,
            "NodePipelineOrchestrator initialized",
            {"node_id": str(self.node_id)},
        )

    async def process_pipeline(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Process data through the pipeline workflow.

        Creates workflow steps with actions, coordinates execution
        based on the specified execution mode, and returns results.

        Args:
            input_data: Pipeline configuration and input data

        Returns:
            Workflow execution results with emitted actions

        Raises:
            ModelOnexError: If workflow coordination fails
        """
        start_time = datetime.now()

        try:
            # Create workflow steps
            steps = self._create_pipeline_steps(input_data)

            # Build orchestrator input
            orchestrator_input = ModelOrchestratorInput(
                workflow_id=input_data.workflow_id,
                steps=[step.model_dump() for step in steps],
                execution_mode=input_data.execution_mode,
            )

            # Execute workflow (delegate to base orchestrator logic)
            result = await self.process(orchestrator_input)

            processing_time_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000

            emit_log_event(
                LogLevel.INFO,
                f"Pipeline workflow completed: {input_data.workflow_id}",
                {
                    "workflow_id": str(input_data.workflow_id),
                    "execution_mode": input_data.execution_mode.value,
                    "processing_time_ms": processing_time_ms,
                },
            )

            return result

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Pipeline workflow failed: {e}",
                {
                    "workflow_id": str(input_data.workflow_id),
                    "error": str(e),
                },
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Pipeline orchestration failed: {e}",
                context={
                    "workflow_id": str(input_data.workflow_id),
                },
            ) from e

    def _create_pipeline_steps(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> list[ModelWorkflowStep]:
        """
        Create workflow steps for the data pipeline.

        Each step is configured with appropriate type, timeout,
        and dependencies to ensure correct execution order.

        Args:
            input_data: Pipeline configuration

        Returns:
            List of workflow steps
        """
        steps: list[ModelWorkflowStep] = []

        # Step 1: Validation (if enabled)
        validation_step_id = uuid4()
        if input_data.config.validate_input:
            validation_step = ModelWorkflowStep(
                step_id=validation_step_id,
                step_name="Validate Input Data",
                step_type="compute",
                timeout_ms=5000,
                retry_count=0,
                depends_on=[],
            )
            steps.append(validation_step)

        # Step 2: Data Fetching
        fetch_step_id = uuid4()
        fetch_dependencies = (
            [validation_step_id] if input_data.config.validate_input else []
        )

        fetch_step = ModelWorkflowStep(
            step_id=fetch_step_id,
            step_name="Fetch Data from Source",
            step_type="effect",
            timeout_ms=10000,
            retry_count=2,
            depends_on=fetch_dependencies,
        )
        steps.append(fetch_step)

        # Step 3: Data Processing
        process_step_id = uuid4()
        process_step = ModelWorkflowStep(
            step_id=process_step_id,
            step_name="Process Fetched Data",
            step_type="compute",
            timeout_ms=15000,
            retry_count=1,
            depends_on=[fetch_step_id],
        )
        steps.append(process_step)

        # Step 4: Data Aggregation
        aggregate_step_id = uuid4()
        aggregate_step = ModelWorkflowStep(
            step_id=aggregate_step_id,
            step_name="Aggregate Processed Data",
            step_type="reducer",
            timeout_ms=10000,
            retry_count=0,
            depends_on=[process_step_id],
        )
        steps.append(aggregate_step)

        # Step 5: Save Results
        save_step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Save Aggregated Results",
            step_type="effect",
            timeout_ms=10000,
            retry_count=3,
            depends_on=[aggregate_step_id],
        )
        steps.append(save_step)

        return steps

    async def _initialize_node_resources(self) -> None:
        """Initialize orchestrator-specific resources."""
        emit_log_event(
            LogLevel.INFO,
            "NodePipelineOrchestrator resources initialized",
            {"node_id": str(self.node_id)},
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup orchestrator-specific resources."""
        self.active_workflows.clear()
        self.emitted_actions.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodePipelineOrchestrator resources cleaned up",
            {"node_id": str(self.node_id)},
        )
```

**What `NodeOrchestrator` Provides**:
- Workflow step execution with topological ordering
- Action emission, tracking, and coordination
- Dependency resolution and cycle detection
- Execution mode management (SEQUENTIAL, PARALLEL, BATCH)
- Lease management for single-writer semantics
- Epoch control for optimistic concurrency
- Disabled step handling
- YAML contract integration via MixinWorkflowExecution

**Key Implementation Points**:

1. **Workflow Steps**: Each step is a `ModelWorkflowStep` with type, timeout, and dependencies
2. **Dependency Management**: Steps specify dependencies via `depends_on` field (list of UUIDs)
3. **Execution Mode Support**: The orchestrator supports SEQUENTIAL, PARALLEL, BATCH modes
4. **Thread Safety**: Use `object.__setattr__()` to bypass Pydantic validation for mutable attributes
5. **Type Safety**: All steps use proper step_type literals ("compute", "effect", "reducer", etc.)

---

## Step 3: Add Conditional Branching

Extend the orchestrator to support conditional execution:

**File**: `src/your_project/nodes/node_conditional_pipeline_orchestrator.py`

```python
"""
Conditional Pipeline Orchestrator with branching logic.

Demonstrates conditional step execution based on runtime state.
"""

from uuid import uuid4
from typing import Any

from omnibase_core.nodes import EnumBranchCondition, EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

from .node_pipeline_orchestrator import NodePipelineOrchestrator
from .model_pipeline_orchestrator_input import ModelPipelineOrchestratorInput


class NodeConditionalPipelineOrchestrator(NodePipelineOrchestrator):
    """
    Pipeline orchestrator with conditional branching.

    Adds conditional execution based on quality scores and validation results.
    """

    def _create_pipeline_steps(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> list[ModelWorkflowStep]:
        """
        Create pipeline steps with conditional branching.

        Adds quality-based branching:
        - High quality -> Fast track (skip some processing)
        - Low quality -> Full processing pipeline
        - Failed validation -> Error handling branch
        """
        steps = super()._create_pipeline_steps(input_data)

        # Add conditional quality check step
        quality_check_step = self._create_quality_check_step(input_data)
        steps.insert(1, quality_check_step)  # After validation

        # Add conditional fast-track step (only executes for high quality data)
        fast_track_step = self._create_fast_track_step(input_data)
        steps.append(fast_track_step)

        return steps

    def _create_quality_check_step(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelWorkflowStep:
        """Create step for quality assessment."""
        return ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Assess Data Quality",
            step_type="compute",
            timeout_ms=5000,
            retry_count=0,
            depends_on=[],
        )

    def _create_fast_track_step(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelWorkflowStep:
        """Create fast-track step for high-quality data."""
        return ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Fast Track Storage",
            step_type="effect",
            timeout_ms=5000,
            retry_count=1,
            depends_on=[],
            # Conditional execution would be configured via contract
        )

    def _check_high_quality(
        self,
        step: ModelWorkflowStep,
        previous_results: list[Any],
    ) -> bool:
        """
        Condition function to check if data is high quality.

        Args:
            step: Current workflow step
            previous_results: Results from previous steps

        Returns:
            True if quality score >= 0.9, False otherwise
        """
        # Extract quality score from previous results
        for result in previous_results:
            if isinstance(result, dict) and "quality_score" in result:
                return result["quality_score"] >= 0.9

        return False
```

**Conditional Execution Features**:

1. **EnumBranchCondition**: Built-in conditions (IF_TRUE, IF_FALSE, IF_ERROR, IF_SUCCESS, IF_TIMEOUT, CUSTOM)
2. **Custom Logic**: Custom Python functions for complex branching logic
3. **Runtime Branching**: Steps execute only if condition is met
4. **Previous Results**: Condition functions can access prior step results

---

## Step 4: Execution Mode Comparison

### SEQUENTIAL Mode

```python
from omnibase_core.nodes import EnumExecutionMode

# Create orchestrator
orchestrator = NodePipelineOrchestrator(container)

# Configure for sequential execution
input_data = ModelPipelineOrchestratorInput(
    input_data={"id": "123", "data": "sample"},
    config=ModelPipelineConfig(
        data_source="database",
        validate_input=True,
    ),
    execution_mode=EnumExecutionMode.SEQUENTIAL,
)

# Execute
result = await orchestrator.process_pipeline(input_data)

# Execution order: Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5
# Total time: ~50ms (sum of all steps)
```

### PARALLEL Mode

```python
# Configure for parallel execution
input_data = ModelPipelineOrchestratorInput(
    input_data={"id": "123", "data": "sample"},
    config=ModelPipelineConfig(
        data_source="database",
        validate_input=True,
        parallel_processing=True,
    ),
    execution_mode=EnumExecutionMode.PARALLEL,
    max_parallel_steps=3,
)

# Execute
result = await orchestrator.process_pipeline(input_data)

# Execution order (respects dependencies):
#   Wave 1: Step 1 (validation) [10ms]
#   Wave 2: Step 2 (fetch) [10ms]
#   Wave 3: Step 3 (process) [15ms]
#   Wave 4: Step 4 (aggregate) [10ms]
#   Wave 5: Step 5 (save) [10ms]
# Total time: ~55ms (dependencies prevent full parallelization)

# If steps were independent:
#   All 5 steps run in parallel
#   Total time: 15ms (max of all steps)
```

### BATCH Mode

```python
# Configure for batch execution with load balancing
input_data = ModelPipelineOrchestratorInput(
    input_data={"id": "123", "data": "sample"},
    config=ModelPipelineConfig(
        data_source="database",
        validate_input=True,
    ),
    execution_mode=EnumExecutionMode.BATCH,
)

# Execute
result = await orchestrator.process_pipeline(input_data)

# Execution:
#   - Load balancer distributes operations
#   - Similar operations are grouped
#   - Resource utilization is optimized
# Total time: ~50-60ms (overhead for load balancing)
```

**Mode Selection Guidelines**:

| Scenario | Recommended Mode | Reason |
|----------|------------------|--------|
| Strong dependencies between steps | SEQUENTIAL | Order must be preserved |
| Independent operations | PARALLEL | Maximize throughput |
| High volume, resource-constrained | BATCH | Optimize resource usage |
| Real-time processing | SEQUENTIAL or PARALLEL | Minimize latency |
| Background jobs | BATCH | Optimize for cost/efficiency |

---

## Step 5: Error Handling and Recovery

Add robust error handling with compensation logic:

```python
from omnibase_core.nodes import EnumWorkflowState
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class NodeResilientPipelineOrchestrator(NodePipelineOrchestrator):
    """
    Pipeline orchestrator with error recovery.

    Implements compensation logic and partial failure handling.
    """

    async def process_pipeline(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """Execute workflow with error recovery."""
        try:
            return await super().process_pipeline(input_data)

        except ModelOnexError as e:
            # Check if we can recover
            if self._can_recover(e, input_data):
                emit_log_event(
                    LogLevel.WARNING,
                    "Attempting error recovery",
                    {"error": str(e), "workflow_id": str(input_data.workflow_id)},
                )

                # Attempt recovery
                return await self._recover_workflow(input_data, e)

            # Cannot recover, re-raise
            raise

    def _can_recover(
        self,
        error: ModelOnexError,
        input_data: ModelPipelineOrchestratorInput,
    ) -> bool:
        """
        Determine if workflow can recover from error.

        Args:
            error: The error that occurred
            input_data: Original workflow input

        Returns:
            True if recovery is possible
        """
        # Check error code
        recoverable_codes = [
            EnumCoreErrorCode.TIMEOUT,
            EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
        ]

        if error.error_code in recoverable_codes:
            return True

        # Check if failure_strategy allows recovery
        if input_data.failure_strategy == "continue_on_error":
            return True

        return False

    async def _recover_workflow(
        self,
        input_data: ModelPipelineOrchestratorInput,
        error: ModelOnexError,
    ) -> ModelOrchestratorOutput:
        """
        Attempt to recover workflow from error.

        Strategies:
        1. Retry with exponential backoff
        2. Skip failed step and continue
        3. Use cached results if available
        4. Rollback to last successful state

        Args:
            input_data: Original workflow input
            error: The error that occurred

        Returns:
            Recovered workflow results
        """
        # Strategy 1: Retry with backoff
        if error.error_code == EnumCoreErrorCode.TIMEOUT:
            emit_log_event(
                LogLevel.INFO,
                "Retrying workflow with increased timeout",
                {"workflow_id": str(input_data.workflow_id)},
            )

            # Increase timeout and retry
            input_data.max_parallel_steps = max(1, input_data.max_parallel_steps - 1)
            return await super().process_pipeline(input_data)

        # Strategy 2: Skip failed step (partial results)
        if input_data.failure_strategy == "continue_on_error":
            emit_log_event(
                LogLevel.WARNING,
                "Continuing workflow with partial results",
                {"workflow_id": str(input_data.workflow_id)},
            )

            # Return partial results
            return ModelOrchestratorOutput(
                execution_status="partial_success",
                execution_time_ms=0.0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                completed_steps=[],
                failed_steps=[],
                final_result=None,
                actions_emitted=[],
                metrics={"recovery_strategy": "partial_results"},
            )

        # No recovery possible
        raise error
```

---

## Step 6: Testing the ORCHESTRATOR Node

**File**: `tests/nodes/test_node_pipeline_orchestrator.py`

```python
"""Tests for NodePipelineOrchestrator."""

import pytest
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes import EnumExecutionMode

from your_project.nodes.node_pipeline_orchestrator import (
    NodePipelineOrchestrator,
)
from your_project.nodes.model_pipeline_orchestrator_input import (
    ModelPipelineOrchestratorInput,
    ModelPipelineConfig,
)


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def orchestrator(container):
    """Create orchestrator instance."""
    return NodePipelineOrchestrator(container)


@pytest.mark.asyncio
async def test_sequential_execution(orchestrator):
    """Test sequential workflow execution."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
            validate_input=True,
        ),
        execution_mode=EnumExecutionMode.SEQUENTIAL,
    )

    # Act
    result = await orchestrator.process_pipeline(input_data)

    # Assert
    assert result.execution_status in ["completed", "success"]
    assert len(result.completed_steps) >= 4
    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_parallel_execution(orchestrator):
    """Test parallel workflow execution."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
            validate_input=False,
        ),
        execution_mode=EnumExecutionMode.PARALLEL,
        max_parallel_steps=3,
    )

    # Act
    result = await orchestrator.process_pipeline(input_data)

    # Assert
    assert result.execution_status in ["completed", "success"]


@pytest.mark.asyncio
async def test_batch_execution(orchestrator):
    """Test batch workflow execution with load balancing."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
        ),
        execution_mode=EnumExecutionMode.BATCH,
    )

    # Act
    result = await orchestrator.process_pipeline(input_data)

    # Assert
    assert result.execution_status in ["completed", "success"]


@pytest.mark.asyncio
async def test_workflow_step_creation(orchestrator):
    """Test workflow step creation."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
            validate_input=True,
        ),
    )

    # Act
    steps = orchestrator._create_pipeline_steps(input_data)

    # Assert
    assert len(steps) >= 5  # At least 5 steps with validation
    assert all(step.step_name for step in steps)
    assert all(step.step_type in ["compute", "effect", "reducer"] for step in steps)


@pytest.mark.asyncio
async def test_dependency_order(orchestrator):
    """Test that steps have correct dependency order."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
            validate_input=True,
        ),
    )

    # Act
    steps = orchestrator._create_pipeline_steps(input_data)

    # Assert
    # First step (validation) has no dependencies
    assert len(steps[0].depends_on) == 0

    # Subsequent steps should have dependencies
    for i, step in enumerate(steps[1:], start=1):
        # Each step (except the first) should depend on something
        # (exact dependency structure depends on implementation)
        pass


@pytest.mark.asyncio
async def test_action_emission(orchestrator):
    """Test action creation and emission."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
        ),
        execution_mode=EnumExecutionMode.SEQUENTIAL,
    )

    # Act
    result = await orchestrator.process_pipeline(input_data)

    # Assert
    assert len(result.actions_emitted) > 0
    # Verify action structure
    for action in result.actions_emitted:
        assert action.action_id is not None
        assert action.action_type is not None
        assert action.target_node_type is not None
        assert action.lease_id is not None  # Verify lease management
        assert action.epoch >= 1  # Verify epoch control
```

**Test Coverage**:
- Sequential execution mode
- Parallel execution mode
- Batch execution mode
- Workflow step creation
- Dependency ordering
- Action emission with lease management

---

## Real-World Usage Examples

### Example 1: ETL Pipeline

```python
"""ETL pipeline using ORCHESTRATOR node."""

orchestrator = NodePipelineOrchestrator(container)

# Configure ETL workflow
input_data = ModelPipelineOrchestratorInput(
    input_data={
        "source_table": "raw_events",
        "target_table": "processed_events",
    },
    config=ModelPipelineConfig(
        data_source="source_database",
        validate_input=True,
        enable_caching=True,
    ),
    execution_mode=EnumExecutionMode.BATCH,  # Optimize for large datasets
)

# Execute ETL
result = await orchestrator.process_pipeline(input_data)

print(f"ETL completed: {len(result.completed_steps)} steps")
print(f"Processing time: {result.execution_time_ms}ms")
print(f"Actions emitted: {len(result.actions_emitted)}")
```

### Example 2: Real-Time Data Processing

```python
"""Real-time data processing with parallel execution."""

orchestrator = NodePipelineOrchestrator(container)

# Configure real-time workflow
input_data = ModelPipelineOrchestratorInput(
    input_data={
        "stream_id": "sensor-data-stream",
        "window_size": "5m",
    },
    config=ModelPipelineConfig(
        data_source="kafka_stream",
        validate_input=True,
        parallel_processing=True,
    ),
    execution_mode=EnumExecutionMode.PARALLEL,  # Minimize latency
    max_parallel_steps=5,
)

# Execute real-time processing
result = await orchestrator.process_pipeline(input_data)

print(f"Stream processing completed in {result.execution_time_ms}ms")
```

### Example 3: Conditional Workflow

```python
"""Conditional workflow based on data quality."""

orchestrator = NodeConditionalPipelineOrchestrator(container)

# Configure quality-based workflow
input_data = ModelPipelineOrchestratorInput(
    input_data={
        "batch_id": "batch-2024-01",
    },
    config=ModelPipelineConfig(
        data_source="data_lake",
        validate_input=True,
        quality_threshold=0.9,
    ),
    execution_mode=EnumExecutionMode.SEQUENTIAL,
)

# Execute with conditional branching
result = await orchestrator.process_pipeline(input_data)

# High-quality data -> Fast track
# Low-quality data -> Full processing pipeline
print(f"Workflow completed: {result.execution_status}")
```

---

## Common Patterns

### Pattern 1: Fan-Out/Fan-In

Execute multiple operations in parallel, then aggregate:

```python
"""Fan-out/fan-in pattern for parallel data processing."""

from uuid import uuid4
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.nodes import EnumActionType

orchestrator_lease_id = uuid4()

# Step 1: Fan-out (parallel fetches from multiple sources)
fetch_actions = []
for source in ["db1", "db2", "db3"]:
    fetch_action = ModelAction(
        action_id=uuid4(),
        action_type=EnumActionType.EFFECT,
        target_node_type="NodeDataFetcherEffect",
        payload={"source": source},
        dependencies=[],  # No dependencies - can run in parallel
        priority=1,
        timeout_ms=10000,
        lease_id=orchestrator_lease_id,
        epoch=1,
    )
    fetch_actions.append(fetch_action)

# Step 2: Fan-in (aggregate all results)
fan_in_dependencies = [action.action_id for action in fetch_actions]

aggregate_action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.REDUCE,
    target_node_type="NodeDataAggregatorReducer",
    payload={"operation": "merge"},
    dependencies=fan_in_dependencies,  # Wait for all fetches
    priority=2,
    timeout_ms=15000,
    lease_id=orchestrator_lease_id,
    epoch=1,
)

# Execute with PARALLEL mode for optimal performance
```

### Pattern 2: Circuit Breaker

Prevent cascading failures with circuit breaker pattern:

```python
"""Circuit breaker pattern for resilient orchestration."""


class NodeCircuitBreakerOrchestrator(NodePipelineOrchestrator):
    """Orchestrator with circuit breaker for external services."""

    def __init__(self, container):
        super().__init__(container)
        object.__setattr__(self, "circuit_breaker_state", {})
        object.__setattr__(self, "failure_threshold", 3)

    async def process_pipeline(self, input_data):
        """Execute with circuit breaker protection."""
        # Check circuit state before execution
        steps = self._create_pipeline_steps(input_data)

        for step in steps:
            service = step.step_type

            # Check if circuit is open
            if self._is_circuit_open(service):
                emit_log_event(
                    LogLevel.WARNING,
                    f"Circuit breaker OPEN for {service}",
                    {"service": service},
                )
                # Skip this service or use fallback
                continue

        # Execute workflow
        try:
            result = await super().process_pipeline(input_data)
            # Reset circuits on success
            for step in steps:
                self._reset_circuit(step.step_type)
            return result

        except Exception as e:
            # Record failure and potentially open circuit
            for step in steps:
                self._record_failure(step.step_type)
            raise

    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for service."""
        state = self.circuit_breaker_state.get(service, {"failures": 0})
        return state.get("failures", 0) >= self.failure_threshold

    def _record_failure(self, service: str) -> None:
        """Record failure for service."""
        if service not in self.circuit_breaker_state:
            self.circuit_breaker_state[service] = {"failures": 0}
        self.circuit_breaker_state[service]["failures"] += 1

    def _reset_circuit(self, service: str) -> None:
        """Reset circuit breaker for service."""
        if service in self.circuit_breaker_state:
            self.circuit_breaker_state[service]["failures"] = 0
```

### Pattern 3: Saga with Compensation

Implement saga pattern with compensation for distributed transactions:

```python
"""Saga pattern with compensation for distributed transactions."""


class NodeSagaOrchestrator(NodePipelineOrchestrator):
    """Orchestrator implementing saga pattern with compensation."""

    async def process_pipeline(self, input_data):
        """Execute workflow with compensation tracking."""
        compensation_stack: list[dict] = []

        try:
            # Execute steps and track compensations
            steps = self._create_pipeline_steps(input_data)

            for step in steps:
                # Execute step via parent
                # (simplified - actual implementation would execute each step)

                # Register compensation action
                compensation = self._create_compensation(step)
                if compensation:
                    compensation_stack.append(compensation)

            return await super().process_pipeline(input_data)

        except Exception as e:
            # Execute compensations in reverse order
            emit_log_event(
                LogLevel.WARNING,
                "Executing compensation actions",
                {"compensations": len(compensation_stack)},
            )

            for compensation in reversed(compensation_stack):
                await self._execute_compensation(compensation)

            raise

    def _create_compensation(self, step: ModelWorkflowStep) -> dict | None:
        """Create compensation action for step."""
        # Example: If step saves to database, compensation deletes
        if step.step_type == "effect":
            return {
                "action": "rollback",
                "step_id": str(step.step_id),
                "step_name": step.step_name,
            }
        return None

    async def _execute_compensation(self, compensation: dict) -> None:
        """Execute compensation action."""
        emit_log_event(
            LogLevel.INFO,
            f"Executing compensation: {compensation['action']}",
            {"compensation": compensation},
        )

        # Execute compensation logic
        # (Would call appropriate EFFECT node to undo the action)
```

---

## Troubleshooting

### Issue: Workflow execution hangs

**Problem**: Workflow doesn't complete and appears stuck.

**Solution**:
1. Check for circular dependencies in step dependency graph
2. Verify timeout values are appropriate
3. Enable debug logging to see step execution:

```python
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.enums.enum_log_level import EnumLogLevel

# Enable debug logging
emit_log_event_sync(
    EnumLogLevel.DEBUG,
    "Orchestrator execution trace",
    {"workflow_id": str(workflow_id)},
)
```

### Issue: Steps execute in wrong order

**Problem**: Workflow steps don't respect dependencies.

**Solution**:
1. Verify `depends_on` field in steps is correctly set with UUIDs
2. Use SEQUENTIAL mode to force serial execution during debugging
3. Check that workflow definition is properly loaded

```python
# Verify step dependencies
steps = orchestrator._create_pipeline_steps(input_data)
for step in steps:
    print(f"Step: {step.step_name}, depends_on: {step.depends_on}")
```

### Issue: Parallel mode slower than sequential

**Problem**: PARALLEL mode performs worse than SEQUENTIAL.

**Solution**:
1. Check if steps have dependencies that prevent parallelization
2. Verify `max_parallel_steps` is appropriate for your system
3. Use BATCH mode for resource-constrained environments

```python
# Optimize parallel configuration
input_data = ModelPipelineOrchestratorInput(
    # ...
    execution_mode=EnumExecutionMode.PARALLEL,
    max_parallel_steps=5,  # Adjust based on available resources
)
```

### Issue: Memory usage grows over time

**Problem**: ORCHESTRATOR consumes increasing memory.

**Solution**:
1. Implement cleanup in `_cleanup_node_resources()`
2. Clear workflow tracking dictionaries
3. Limit concurrent workflows with semaphore

```python
async def _cleanup_node_resources(self):
    """Cleanup orchestrator resources."""
    self.active_workflows.clear()
    self.emitted_actions.clear()
```

---

## Next Steps

Congratulations! You've completed the ORCHESTRATOR node tutorial. You now know how to:

- Build multi-step workflow orchestrators
- Use action emission for deferred execution
- Implement lease management for single-writer semantics
- Implement SEQUENTIAL, PARALLEL, and BATCH execution modes
- Add conditional branching and error recovery
- Test orchestrator nodes comprehensively

### Related Documentation

- [Node Types Overview](02_NODE_TYPES.md) - Understanding the 4-node architecture
- [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Complete architecture guide
- [Migration Guide](../MIGRATING_TO_DECLARATIVE_NODES.md) - Migrating from v0.3.x to v0.4.0
- [Patterns Catalog](07_PATTERNS_CATALOG.md) - Common orchestration patterns

### Practice Exercises

1. **Build a CI/CD Pipeline Orchestrator**
   - Steps: lint -> test -> build -> deploy
   - Use SEQUENTIAL mode with conditional branching
   - Add rollback compensation logic

2. **Create a Data Quality Pipeline**
   - Parallel data quality checks
   - Aggregate results with REDUCER
   - Conditional routing based on quality scores

3. **Implement Event-Driven Orchestrator**
   - Use Event Registry integration
   - Trigger workflows from external events
   - Coordinate async event processing

### Production Checklist

Before deploying ORCHESTRATOR nodes to production:

- [ ] Comprehensive tests for all execution modes
- [ ] Error handling and compensation logic implemented
- [ ] Workflow timeouts configured appropriately
- [ ] Dependency resolution tested thoroughly
- [ ] Performance benchmarks established
- [ ] Monitoring and logging enabled
- [ ] Circuit breaker patterns for external services
- [ ] Resource cleanup in `_cleanup_node_resources()`
- [ ] Documentation for all workflows
- [ ] Rollback procedures documented

---

**Tutorial Complete!**

You've mastered ORCHESTRATOR nodes and completed the full ONEX node building guide. You're now ready to build complex, production-ready workflows using the four-node architecture.
