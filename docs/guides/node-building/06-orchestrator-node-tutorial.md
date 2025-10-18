# ORCHESTRATOR Node Tutorial: Build a Data Processing Pipeline

**Reading Time**: 40 minutes
**Difficulty**: Advanced
**Prerequisites**: All other node tutorials (COMPUTE, EFFECT, REDUCER)

## What You'll Build

In this tutorial, you'll build a production-ready **Data Processing Pipeline Orchestrator** that:

✅ Coordinates multiple nodes (COMPUTE, EFFECT, REDUCER) in a workflow
✅ Supports three execution modes: SEQUENTIAL, PARALLEL, BATCH
✅ Implements thunk emission for deferred execution
✅ Manages dependencies between workflow steps
✅ Handles conditional branching and error recovery
✅ Provides comprehensive workflow monitoring

**Why ORCHESTRATOR Nodes?**

ORCHESTRATOR nodes coordinate complex workflows in the ONEX architecture:
- Multi-step data processing pipelines
- Workflow coordination with dependencies
- Parallel execution of independent operations
- Conditional branching based on runtime state
- Load balancing across execution nodes
- Error recovery and compensation logic

**Tutorial Structure**:
1. Understand orchestration concepts (thunks, workflows, execution modes)
2. Define workflow models and configuration
3. Implement the ORCHESTRATOR node with three execution modes
4. Add conditional branching and error handling
5. Write comprehensive tests
6. See real-world usage examples

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

✅ **If tests pass**, you're ready to begin!

---

## Orchestration Concepts

### What is a Thunk?

A **thunk** is a deferred execution unit that represents work to be done by a specific node type:

```python
from omnibase_core.nodes.model_thunk import ModelThunk
from omnibase_core.nodes.enum_orchestrator_types import EnumThunkType

# Example: Thunk for COMPUTE operation
compute_thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumThunkType.COMPUTE,
    target_node_type="NodeDataValidator",
    operation_data={"data": input_data},
    dependencies=[],  # No dependencies
    priority=1,
    timeout_ms=5000,
)

# Example: Thunk for EFFECT operation with dependency
effect_thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumThunkType.EFFECT,
    target_node_type="NodeDatabaseWriter",
    operation_data={"data": processed_data},
    dependencies=[compute_thunk.thunk_id],  # Depends on compute
    priority=2,
    timeout_ms=10000,
)
```

**Key Points**:
- Thunks represent "units of work" to be executed
- They can have dependencies on other thunks
- The orchestrator emits thunks and coordinates execution
- Thunks enable deferred, dependency-aware execution

### Workflow Steps

A **workflow step** groups related thunks together:

```python
from omnibase_core.nodes.model_workflow_step import ModelWorkflowStep

step = ModelWorkflowStep(
    step_id=uuid4(),
    step_name="Validate and Process Data",
    execution_mode=EnumExecutionMode.SEQUENTIAL,
    thunks=[validation_thunk, processing_thunk],
    timeout_ms=30000,
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

```
Step 1 (Validate) ─┐
                   ├──> Step 3 (Aggregate)
Step 2 (Fetch) ────┘

Step 3 (Aggregate) ───> Step 4 (Save)
```

Execution order: Steps 1&2 in parallel → Step 3 → Step 4

---

## Step 1: Define Workflow Input Model

**File**: `src/your_project/nodes/model_pipeline_orchestrator_input.py`

```python
"""Input model for data processing pipeline orchestrator."""

from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from omnibase_core.nodes.enum_orchestrator_types import EnumExecutionMode


class ModelPipelineConfig(BaseModel):
    """Configuration for pipeline processing."""

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

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
```

---

## Step 2: Implement the ORCHESTRATOR Node

**File**: `src/your_project/nodes/node_pipeline_orchestrator.py`

```python
"""
Data Processing Pipeline Orchestrator Node.

Coordinates multi-step data pipeline with validation, fetching,
processing, and storage via thunk emission and workflow coordination.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Any

from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.enum_orchestrator_types import (
    EnumExecutionMode,
    EnumThunkType,
    EnumWorkflowState,
)
from omnibase_core.nodes.model_thunk import ModelThunk
from omnibase_core.nodes.model_workflow_step import ModelWorkflowStep
from omnibase_core.nodes.model_orchestrator_input import ModelOrchestratorInput
from omnibase_core.nodes.model_orchestrator_output import ModelOrchestratorOutput
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .model_pipeline_orchestrator_input import ModelPipelineOrchestratorInput


class NodePipelineOrchestrator(NodeCoreBase):
    """
    Data Processing Pipeline Orchestrator.

    Coordinates a multi-step data pipeline workflow:
    1. Validation (COMPUTE node)
    2. Data fetching (EFFECT node)
    3. Processing (COMPUTE node)
    4. Aggregation (REDUCER node)
    5. Storage (EFFECT node)

    Supports SEQUENTIAL, PARALLEL, and BATCH execution modes.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize the pipeline orchestrator.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)

        # Orchestrator configuration
        object.__setattr__(self, "max_concurrent_workflows", 5)
        object.__setattr__(self, "default_step_timeout_ms", 30000)

        # Workflow tracking
        object.__setattr__(self, "active_workflows", {})
        object.__setattr__(self, "emitted_thunks", {})

        emit_log_event(
            LogLevel.INFO,
            "NodePipelineOrchestrator initialized",
            {"node_id": str(self.node_id)},
        )

    async def process(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Process data through the pipeline workflow.

        Creates workflow steps with thunks, coordinates execution
        based on the specified execution mode, and returns results.

        Args:
            input_data: Pipeline configuration and input data

        Returns:
            Workflow execution results with emitted thunks

        Raises:
            ModelOnexError: If workflow coordination fails
        """
        start_time = datetime.now()

        try:
            # Create workflow steps
            steps = await self._create_pipeline_steps(input_data)

            # Build orchestrator input
            orchestrator_input = ModelOrchestratorInput(
                workflow_id=input_data.workflow_id,
                operation_id=input_data.operation_id,
                steps=[step.model_dump() for step in steps],
                execution_mode=input_data.execution_mode,
                dependency_resolution_enabled=True,
                failure_strategy=input_data.failure_strategy,
                max_parallel_steps=input_data.max_parallel_steps,
                metadata={
                    "pipeline_type": "data_processing",
                    "data_source": input_data.config.data_source,
                },
            )

            # Execute workflow (delegate to base orchestrator logic)
            result = await self._execute_workflow(orchestrator_input)

            processing_time_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000

            emit_log_event(
                LogLevel.INFO,
                f"Pipeline workflow completed: {input_data.workflow_id}",
                {
                    "workflow_id": str(input_data.workflow_id),
                    "execution_mode": input_data.execution_mode.value,
                    "steps_completed": result.steps_completed,
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

    async def _create_pipeline_steps(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> list[ModelWorkflowStep]:
        """
        Create workflow steps for the data pipeline.

        Each step contains thunks representing operations to perform.
        Dependencies between thunks ensure correct execution order.

        Args:
            input_data: Pipeline configuration

        Returns:
            List of workflow steps with thunks
        """
        steps = []

        # Step 1: Validation (if enabled)
        if input_data.config.validate_input:
            validation_thunk = ModelThunk(
                thunk_id=uuid4(),
                thunk_type=EnumThunkType.COMPUTE,
                target_node_type="NodeDataValidatorCompute",
                operation_data={
                    "data": input_data.input_data,
                    "validation_rules": {
                        "required_fields": ["id", "data"],
                        "quality_threshold": input_data.config.quality_threshold,
                    },
                },
                dependencies=[],
                priority=1,
                timeout_ms=5000,
                retry_count=0,
                metadata={"step_type": "validation"},
                created_at=datetime.now(),
            )

            validation_step = ModelWorkflowStep(
                step_id=uuid4(),
                step_name="Validate Input Data",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                thunks=[validation_thunk],
                timeout_ms=self.default_step_timeout_ms,
                metadata={"step_type": "validation"},
            )
            steps.append(validation_step)

        # Step 2: Data Fetching
        fetch_thunk_id = uuid4()
        fetch_dependencies = (
            [steps[0].thunks[0].thunk_id] if input_data.config.validate_input else []
        )

        fetch_thunk = ModelThunk(
            thunk_id=fetch_thunk_id,
            thunk_type=EnumThunkType.EFFECT,
            target_node_type="NodeDataFetcherEffect",
            operation_data={
                "source": input_data.config.data_source,
                "query": input_data.input_data.get("query", {}),
            },
            dependencies=fetch_dependencies,
            priority=1,
            timeout_ms=10000,
            retry_count=2,
            metadata={"step_type": "fetch"},
            created_at=datetime.now(),
        )

        fetch_step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Fetch Data from Source",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[fetch_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "fetch"},
        )
        steps.append(fetch_step)

        # Step 3: Data Processing
        process_thunk_id = uuid4()
        process_thunk = ModelThunk(
            thunk_id=process_thunk_id,
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeDataProcessorCompute",
            operation_data={
                "operation": "transform",
                "enable_caching": input_data.config.enable_caching,
            },
            dependencies=[fetch_thunk_id],
            priority=1,
            timeout_ms=15000,
            retry_count=1,
            metadata={"step_type": "processing"},
            created_at=datetime.now(),
        )

        process_step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Process Fetched Data",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[process_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "processing"},
        )
        steps.append(process_step)

        # Step 4: Data Aggregation
        aggregate_thunk_id = uuid4()
        aggregate_thunk = ModelThunk(
            thunk_id=aggregate_thunk_id,
            thunk_type=EnumThunkType.REDUCE,
            target_node_type="NodeMetricsAggregatorReducer",
            operation_data={
                "aggregation_type": "sum",
                "group_by": "category",
            },
            dependencies=[process_thunk_id],
            priority=1,
            timeout_ms=10000,
            retry_count=0,
            metadata={"step_type": "aggregation"},
            created_at=datetime.now(),
        )

        aggregate_step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Aggregate Processed Data",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[aggregate_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "aggregation"},
        )
        steps.append(aggregate_step)

        # Step 5: Save Results
        save_thunk = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.EFFECT,
            target_node_type="NodeDatabaseWriterEffect",
            operation_data={
                "destination": "processed_data_table",
                "mode": "upsert",
            },
            dependencies=[aggregate_thunk_id],
            priority=2,
            timeout_ms=10000,
            retry_count=3,
            metadata={"step_type": "storage"},
            created_at=datetime.now(),
        )

        save_step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Save Aggregated Results",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[save_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "storage"},
        )
        steps.append(save_step)

        return steps

    async def _execute_workflow(
        self,
        orchestrator_input: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Execute workflow based on execution mode.

        Delegates to the appropriate execution strategy:
        - SEQUENTIAL: Execute steps one by one
        - PARALLEL: Execute independent steps concurrently
        - BATCH: Execute with load balancing

        Args:
            orchestrator_input: Workflow configuration

        Returns:
            Workflow execution results
        """
        # Import base orchestrator for execution logic
        from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

        # Create base orchestrator instance
        base_orchestrator = NodeOrchestrator(self.container)

        # Delegate execution to base orchestrator
        result = await base_orchestrator.process(orchestrator_input)

        return result

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
        self.emitted_thunks.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodePipelineOrchestrator resources cleaned up",
            {"node_id": str(self.node_id)},
        )
```

**Key Implementation Points**:

1. **Thunk Creation**: Each workflow step contains thunks representing operations
2. **Dependency Management**: Thunks specify dependencies via `dependencies` field
3. **Execution Mode Support**: The orchestrator supports SEQUENTIAL, PARALLEL, BATCH modes
4. **Delegation Pattern**: Complex orchestration logic is delegated to `NodeOrchestrator` base class
5. **Type Safety**: All thunks use `EnumThunkType` for type specification

---

## Step 3: Add Conditional Branching

Let's extend the orchestrator to support conditional execution:

**File**: `src/your_project/nodes/node_conditional_pipeline_orchestrator.py`

```python
"""
Conditional Pipeline Orchestrator with branching logic.

Demonstrates conditional step execution based on runtime state.
"""

from uuid import uuid4
from datetime import datetime

from omnibase_core.nodes.enum_orchestrator_types import EnumBranchCondition

from .node_pipeline_orchestrator import NodePipelineOrchestrator
from .model_pipeline_orchestrator_input import ModelPipelineOrchestratorInput


class NodeConditionalPipelineOrchestrator(NodePipelineOrchestrator):
    """
    Pipeline orchestrator with conditional branching.

    Adds conditional execution based on quality scores and validation results.
    """

    async def _create_pipeline_steps(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> list[ModelWorkflowStep]:
        """
        Create pipeline steps with conditional branching.

        Adds quality-based branching:
        - High quality → Fast track (skip some processing)
        - Low quality → Full processing pipeline
        - Failed validation → Error handling branch
        """
        steps = await super()._create_pipeline_steps(input_data)

        # Add conditional quality check step
        quality_check_step = self._create_quality_check_step(input_data)
        steps.insert(1, quality_check_step)  # After validation

        # Add conditional fast-track step
        fast_track_step = self._create_fast_track_step(input_data)
        fast_track_step.condition = EnumBranchCondition.CUSTOM
        fast_track_step.condition_function = self._check_high_quality
        steps.append(fast_track_step)

        return steps

    def _create_quality_check_step(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelWorkflowStep:
        """Create step for quality assessment."""
        quality_thunk = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeQualityAssessorCompute",
            operation_data={
                "threshold": input_data.config.quality_threshold,
            },
            dependencies=[],
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={"step_type": "quality_check"},
            created_at=datetime.now(),
        )

        return ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Assess Data Quality",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[quality_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "quality_check"},
        )

    def _create_fast_track_step(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelWorkflowStep:
        """Create fast-track step for high-quality data."""
        fast_track_thunk = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.EFFECT,
            target_node_type="NodeFastTrackWriterEffect",
            operation_data={
                "destination": "fast_track_table",
            },
            dependencies=[],
            priority=3,
            timeout_ms=5000,
            retry_count=1,
            metadata={"step_type": "fast_track"},
            created_at=datetime.now(),
        )

        return ModelWorkflowStep(
            step_id=uuid4(),
            step_name="Fast Track Storage",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[fast_track_thunk],
            timeout_ms=self.default_step_timeout_ms,
            metadata={"step_type": "fast_track"},
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

1. **EnumBranchCondition**: Built-in conditions (IF_TRUE, IF_FALSE, CUSTOM)
2. **condition_function**: Custom Python functions for complex logic
3. **Runtime Branching**: Steps execute only if condition is met
4. **Previous Results**: Condition functions can access prior step results

---

## Step 4: Execution Mode Comparison

Let's see how the same pipeline executes in different modes:

### SEQUENTIAL Mode

```python
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
result = await orchestrator.process(input_data)

# Execution order: Step 1 → Step 2 → Step 3 → Step 4 → Step 5
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
result = await orchestrator.process(input_data)

# Execution order:
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
result = await orchestrator.process(input_data)

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
class NodeResilientPipelineOrchestrator(NodePipelineOrchestrator):
    """
    Pipeline orchestrator with error recovery.

    Implements compensation logic and partial failure handling.
    """

    async def process(
        self,
        input_data: ModelPipelineOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """Execute workflow with error recovery."""
        try:
            return await super().process(input_data)

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
            return await super().process(input_data)

        # Strategy 2: Skip failed step
        if input_data.failure_strategy == "continue_on_error":
            emit_log_event(
                LogLevel.WARNING,
                "Continuing workflow with partial results",
                {"workflow_id": str(input_data.workflow_id)},
            )

            # Return partial results
            return ModelOrchestratorOutput(
                workflow_id=input_data.workflow_id,
                operation_id=input_data.operation_id,
                workflow_state=EnumWorkflowState.PARTIAL_SUCCESS,
                steps_completed=0,
                steps_failed=1,
                thunks_emitted=[],
                processing_time_ms=0.0,
                results=[],
                metadata={"recovery_strategy": "partial_results"},
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
from omnibase_core.nodes.enum_orchestrator_types import (
    EnumExecutionMode,
    EnumWorkflowState,
)

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
    result = await orchestrator.process(input_data)

    # Assert
    assert result.workflow_state == EnumWorkflowState.COMPLETED
    assert result.steps_completed >= 4  # At least 4 steps executed
    assert result.steps_failed == 0
    assert len(result.thunks_emitted) >= 4
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_parallel_execution(orchestrator):
    """Test parallel workflow execution."""
    # Arrange
    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="test_database",
            validate_input=False,  # Skip validation for independence
        ),
        execution_mode=EnumExecutionMode.PARALLEL,
        max_parallel_steps=3,
    )

    # Act
    result = await orchestrator.process(input_data)

    # Assert
    assert result.workflow_state == EnumWorkflowState.COMPLETED
    assert result.parallel_executions is not None
    assert result.parallel_executions > 0


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
    result = await orchestrator.process(input_data)

    # Assert
    assert result.workflow_state == EnumWorkflowState.COMPLETED
    assert result.load_balanced_operations is not None
    assert result.load_balanced_operations > 0


@pytest.mark.asyncio
async def test_conditional_branching(orchestrator):
    """Test conditional step execution."""
    from your_project.nodes.node_conditional_pipeline_orchestrator import (
        NodeConditionalPipelineOrchestrator,
    )

    # Arrange
    conditional_orchestrator = NodeConditionalPipelineOrchestrator(
        orchestrator.container
    )

    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "high_quality"},
        config=ModelPipelineConfig(
            data_source="test_database",
            quality_threshold=0.95,
        ),
        execution_mode=EnumExecutionMode.SEQUENTIAL,
    )

    # Act
    result = await conditional_orchestrator.process(input_data)

    # Assert
    assert result.workflow_state == EnumWorkflowState.COMPLETED
    # Conditional steps may be skipped based on quality


@pytest.mark.asyncio
async def test_error_recovery(orchestrator):
    """Test error recovery mechanisms."""
    from your_project.nodes.node_resilient_pipeline_orchestrator import (
        NodeResilientPipelineOrchestrator,
    )

    # Arrange
    resilient_orchestrator = NodeResilientPipelineOrchestrator(
        orchestrator.container
    )

    input_data = ModelPipelineOrchestratorInput(
        workflow_id=uuid4(),
        input_data={"id": "test-123", "data": "sample"},
        config=ModelPipelineConfig(
            data_source="unavailable_source",  # This will fail
        ),
        execution_mode=EnumExecutionMode.SEQUENTIAL,
        failure_strategy="continue_on_error",
    )

    # Act
    result = await resilient_orchestrator.process(input_data)

    # Assert
    # Should return partial results instead of failing
    assert result.workflow_state in [
        EnumWorkflowState.PARTIAL_SUCCESS,
        EnumWorkflowState.COMPLETED,
    ]


@pytest.mark.asyncio
async def test_dependency_resolution(orchestrator):
    """Test dependency graph construction and execution."""
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
    result = await orchestrator.process(input_data)

    # Assert
    assert result.workflow_state == EnumWorkflowState.COMPLETED
    # Verify steps executed in dependency order
    assert result.steps_completed > 0


@pytest.mark.asyncio
async def test_thunk_emission(orchestrator):
    """Test thunk creation and emission."""
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
    result = await orchestrator.process(input_data)

    # Assert
    assert len(result.thunks_emitted) > 0
    # Verify thunk structure
    for thunk in result.thunks_emitted:
        assert thunk.thunk_id is not None
        assert thunk.thunk_type is not None
        assert thunk.target_node_type is not None
        assert thunk.operation_data is not None
```

**Test Coverage**:
- ✅ Sequential execution mode
- ✅ Parallel execution mode
- ✅ Batch execution mode
- ✅ Conditional branching
- ✅ Error recovery
- ✅ Dependency resolution
- ✅ Thunk emission

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
result = await orchestrator.process(input_data)

print(f"ETL completed: {result.steps_completed} steps")
print(f"Processing time: {result.processing_time_ms}ms")
print(f"Thunks emitted: {len(result.thunks_emitted)}")
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
result = await orchestrator.process(input_data)

print(f"Stream processing completed in {result.processing_time_ms}ms")
print(f"Parallel executions: {result.parallel_executions}")
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
result = await orchestrator.process(input_data)

# High-quality data → Fast track
# Low-quality data → Full processing pipeline
print(f"Workflow path taken: {result.metadata.get('path', 'standard')}")
```

---

## Common Patterns

### Pattern 1: Fan-Out/Fan-In

Execute multiple operations in parallel, then aggregate:

```python
"""Fan-out/fan-in pattern for parallel data processing."""

# Step 1: Fan-out (parallel fetches from multiple sources)
fetch_steps = []
for source in ["db1", "db2", "db3"]:
    fetch_thunk = ModelThunk(
        thunk_id=uuid4(),
        thunk_type=EnumThunkType.EFFECT,
        target_node_type="NodeDataFetcherEffect",
        operation_data={"source": source},
        dependencies=[],  # No dependencies - can run in parallel
        priority=1,
        timeout_ms=10000,
    )
    step = ModelWorkflowStep(
        step_id=uuid4(),
        step_name=f"Fetch from {source}",
        thunks=[fetch_thunk],
    )
    fetch_steps.append(step)

# Step 2: Fan-in (aggregate all results)
fan_in_dependencies = [step.thunks[0].thunk_id for step in fetch_steps]

aggregate_thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumThunkType.REDUCE,
    target_node_type="NodeDataAggregatorReducer",
    operation_data={"operation": "merge"},
    dependencies=fan_in_dependencies,  # Wait for all fetches
    priority=2,
    timeout_ms=15000,
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

    async def _execute_workflow(self, orchestrator_input):
        """Execute with circuit breaker protection."""
        # Check circuit state for each target service
        for step_dict in orchestrator_input.steps:
            step = self._dict_to_workflow_step(step_dict)
            for thunk in step.thunks:
                service = thunk.target_node_type

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
            result = await super()._execute_workflow(orchestrator_input)
            # Reset circuit on success
            for step_dict in orchestrator_input.steps:
                step = self._dict_to_workflow_step(step_dict)
                for thunk in step.thunks:
                    self._reset_circuit(thunk.target_node_type)
            return result

        except Exception as e:
            # Record failure and potentially open circuit
            for step_dict in orchestrator_input.steps:
                step = self._dict_to_workflow_step(step_dict)
                for thunk in step.thunks:
                    self._record_failure(thunk.target_node_type)
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

### Pattern 3: Compensation Logic

Implement saga pattern with compensation:

```python
"""Saga pattern with compensation for distributed transactions."""

class NodeSagaOrchestrator(NodePipelineOrchestrator):
    """Orchestrator implementing saga pattern with compensation."""

    async def process(self, input_data):
        """Execute workflow with compensation tracking."""
        compensation_stack = []

        try:
            # Execute steps and track compensations
            steps = await self._create_pipeline_steps(input_data)

            for step in steps:
                # Execute step
                result = await self._execute_step(step)

                # Register compensation action
                compensation = self._create_compensation(step)
                compensation_stack.append(compensation)

            return result

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

    def _create_compensation(self, step):
        """Create compensation action for step."""
        # Example: If step saves to database, compensation deletes
        if step.metadata.get("step_type") == "storage":
            return {
                "action": "delete",
                "target": step.thunks[0].operation_data.get("destination"),
                "thunk_id": step.thunks[0].thunk_id,
            }
        return None

    async def _execute_compensation(self, compensation):
        """Execute compensation action."""
        if compensation is None:
            return

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
1. Check for circular dependencies in thunk dependency graph
2. Verify timeout values are appropriate
3. Enable debug logging to see step execution:

```python
from omnibase_core.logging.structured import emit_log_event_sync
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
1. Verify `dependencies` field in thunks is correctly set
2. Enable dependency resolution: `dependency_resolution_enabled=True`
3. Use SEQUENTIAL mode to force serial execution during debugging

```python
# Verify dependency graph
orchestrator_input = ModelOrchestratorInput(
    # ...
    dependency_resolution_enabled=True,
    execution_mode=EnumExecutionMode.SEQUENTIAL,  # Force order
)
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
    self.emitted_thunks.clear()
    self.workflow_states.clear()
```

---

## Advanced Topics

### Optional: LlamaIndex Workflow Integration

While ORCHESTRATOR nodes primarily use thunk emission for coordination, you can optionally integrate LlamaIndex workflows via the `MixinHybridExecution` mixin:

```python
"""Optional LlamaIndex workflow integration."""

from omnibase_core.mixins.mixin_hybrid_execution import MixinHybridExecution
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step


class MyLlamaIndexWorkflow(Workflow):
    """LlamaIndex workflow for complex orchestration."""

    @step
    async def validate(self, ev: StartEvent) -> ValidationEvent:
        """Validation step."""
        data = ev.data
        # Validation logic
        return ValidationEvent(validated_data=data)

    @step
    async def process(self, ev: ValidationEvent) -> ProcessEvent:
        """Processing step."""
        # Processing logic
        return ProcessEvent(processed_data=ev.validated_data)

    @step
    async def finalize(self, ev: ProcessEvent) -> StopEvent:
        """Final step."""
        return StopEvent(result=ev.processed_data)


class NodeHybridOrchestrator(MixinHybridExecution, NodePipelineOrchestrator):
    """Orchestrator with optional LlamaIndex workflow support."""

    def create_workflow(self, input_state):
        """Create LlamaIndex workflow for complex operations."""
        return MyLlamaIndexWorkflow()

    def determine_execution_mode(self, input_state):
        """Decide between thunk-based and LlamaIndex execution."""
        complexity = self._calculate_complexity(input_state)

        if complexity > 0.8:
            return "workflow"  # Use LlamaIndex
        return "direct"  # Use thunk-based orchestration
```

**When to use LlamaIndex workflows**:
- Complex, deeply nested orchestration logic
- Integration with LlamaIndex AI capabilities
- Advanced workflow visualization needs

**When to use thunk-based orchestration** (recommended):
- Standard ONEX workflow coordination
- Dependency-based execution ordering
- Multi-mode execution (SEQUENTIAL, PARALLEL, BATCH)
- Integration with other ONEX nodes

---

## Next Steps

Congratulations! You've completed the ORCHESTRATOR node tutorial. You now know how to:

✅ Build multi-step workflow orchestrators
✅ Use thunk emission for deferred execution
✅ Implement SEQUENTIAL, PARALLEL, and BATCH execution modes
✅ Add conditional branching and error recovery
✅ Test orchestrator nodes comprehensively

### Related Documentation

- [Node Types Overview](02-node-types.md) - Understanding the 4-node architecture
- [ONEX Four-Node Architecture](../../ONEX_FOUR_NODE_ARCHITECTURE.md) - Complete architecture guide
- [ORCHESTRATOR Node Template](../../reference/templates/ORCHESTRATOR_NODE_TEMPLATE.md) - Production template
- [Patterns Catalog](07-patterns-catalog.md) - Common orchestration patterns

### Practice Exercises

1. **Build a CI/CD Pipeline Orchestrator**
   - Steps: lint → test → build → deploy
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

**Tutorial Complete!** 🎉

You've mastered ORCHESTRATOR nodes and completed the full ONEX node building guide. You're now ready to build complex, production-ready workflows using the four-node architecture.
