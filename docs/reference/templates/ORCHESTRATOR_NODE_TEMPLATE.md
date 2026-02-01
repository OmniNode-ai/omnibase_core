> **Navigation**: [Home](../../index.md) > [Reference](../README.md) > Templates > ORCHESTRATOR Node

# ORCHESTRATOR Node Template

## Overview

This template provides the unified architecture pattern for ONEX ORCHESTRATOR nodes. ORCHESTRATOR nodes are responsible for coordinating multi-step workflows, managing dependencies between steps, and orchestrating parallel or sequential execution of work across the ONEX ecosystem.

## Key Characteristics

- **Workflow Coordination**: Multi-step workflow orchestration with dependency management
- **Lease-Based Semantics**: Single-writer coordination for distributed execution
- **ModelAction Pattern**: Actions emitted for deferred execution by target nodes
- **Execution Modes**: Sequential, parallel, conditional, batch, and streaming execution
- **Recovery Strategies**: Built-in retry, compensation, and failure recovery
- **Type Safety**: Full Pydantic validation with immutable input/output models

## Directory Structure

```
{REPOSITORY_NAME}/
├── src/
│   └── {REPOSITORY_NAME}/
│       └── nodes/
│           └── node_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator/
│               └── v1_0_0/
│                   ├── __init__.py
│                   ├── node.py
│                   ├── config.py
│                   ├── contracts/
│                   │   ├── __init__.py
│                   │   ├── orchestrator_contract.py
│                   │   └── subcontracts/
│                   │       ├── __init__.py
│                   │       ├── input_subcontract.yaml
│                   │       ├── output_subcontract.yaml
│                   │       ├── config_subcontract.yaml
│                   │       └── workflow_definition.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_input.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_output.py
│                   │   └── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_config.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   └── enum_{DOMAIN}_{MICROSERVICE_NAME}_workflow_type.py
│                   ├── utils/
│                   │   ├── __init__.py
│                   │   ├── step_executor.py
│                   │   ├── dependency_resolver.py
│                   │   └── recovery_handler.py
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_config.py
                    ├── test_contracts.py
                    └── test_models.py
```

## Template Files

### 1. Node Implementation (`node.py`)

```python
"""ONEX ORCHESTRATOR node for {DOMAIN} {MICROSERVICE_NAME} workflow coordination."""

import asyncio
from typing import Any
from uuid import UUID, uuid4
import time

# v0.4.0 unified node imports
from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    EnumActionType,
    EnumExecutionMode,
    EnumWorkflowStatus,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.utils.error_sanitizer import ErrorSanitizer

from .config import {DomainCamelCase}{MicroserviceCamelCase}OrchestratorConfig
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_workflow_type import Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType
from .utils.step_executor import StepExecutor
from .utils.dependency_resolver import DependencyResolver
from .utils.recovery_handler import RecoveryHandler


class Node{DomainCamelCase}{MicroserviceCamelCase}Orchestrator(NodeOrchestrator):
    """ORCHESTRATOR node for {DOMAIN} {MICROSERVICE_NAME} workflow coordination.

    This node provides workflow-driven coordination for {DOMAIN} domain
    operations, focusing on {MICROSERVICE_NAME} multi-step orchestration.

    Key Features:
    - Workflow-driven coordination via YAML contracts
    - ModelAction pattern for deferred execution
    - Lease-based single-writer semantics
    - Dependency-aware execution ordering
    - Configurable failure recovery strategies
    - Support for parallel, sequential, and conditional execution

    Thread Safety:
        NodeOrchestrator instances are NOT thread-safe due to mutable workflow state.
        Each thread should have its own instance. See docs/guides/THREADING.md.

    Example:
        ```python
        from uuid import uuid4
        from omnibase_core.nodes import EnumExecutionMode

        # Create orchestrator node
        node = Node{DomainCamelCase}{MicroserviceCamelCase}Orchestrator(container)

        # Set workflow definition (or load from YAML contract)
        node.workflow_definition = workflow_def

        # Define workflow steps
        input_data = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[
                {"step_name": "Fetch Data", "step_type": "effect", "timeout_ms": 10000},
                {"step_name": "Process Data", "step_type": "compute", "timeout_ms": 15000},
            ],
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        # Execute workflow
        result = await node.process(input_data)
        print(f"Status: {result.execution_status}")
        print(f"Completed: {len(result.completed_steps)} steps")
        ```
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the ORCHESTRATOR node with container.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Initialize orchestration components
        self._step_executor = StepExecutor()
        self._dependency_resolver = DependencyResolver()
        self._recovery_handler = RecoveryHandler()
        self._error_sanitizer = ErrorSanitizer()

        # Execution tracking
        self._active_workflows: dict[UUID, EnumWorkflowStatus] = {}
        self._step_results: dict[UUID, dict[str, Any]] = {}

    @standard_error_handling("Workflow orchestration")
    async def process(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """Process {DOMAIN} {MICROSERVICE_NAME} workflow orchestration.

        This is the primary workflow interface that coordinates multi-step
        execution with dependency management and failure handling.

        Args:
            input_data: Orchestrator input with workflow steps and configuration

        Returns:
            Orchestrator output with execution results and emitted actions

        Raises:
            ModelOnexError: If workflow definition not loaded or execution fails
            ValidationError: If input validation fails
            TimeoutError: If workflow exceeds global timeout

        Example:
            ```python
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[
                    {"step_name": "validate", "step_type": "compute"},
                    {"step_name": "persist", "step_type": "effect"},
                ],
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                failure_strategy="retry",
            )

            result = await node.process(input_data)
            if result.execution_status == "completed":
                print(f"Workflow completed in {result.execution_time_ms}ms")
            ```
        """
        # Validate workflow definition is loaded
        if not self.workflow_definition:
            raise ModelOnexError(
                message="Workflow definition not loaded",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Track workflow state
        workflow_id = input_data.workflow_id
        self._active_workflows[workflow_id] = EnumWorkflowStatus.RUNNING

        try:
            # Pre-execution validation
            await self._validate_workflow_input(input_data)

            # Resolve step dependencies and determine execution order
            execution_order = await self._resolve_execution_order(input_data)

            # Execute workflow based on execution mode
            if input_data.execution_mode == EnumExecutionMode.PARALLEL:
                result = await self._execute_parallel_workflow(
                    input_data, execution_order
                )
            elif input_data.execution_mode == EnumExecutionMode.CONDITIONAL:
                result = await self._execute_conditional_workflow(
                    input_data, execution_order
                )
            else:  # Default to SEQUENTIAL
                result = await self._execute_sequential_workflow(
                    input_data, execution_order
                )

            # Update workflow state
            self._active_workflows[workflow_id] = EnumWorkflowStatus.COMPLETED

            return result

        except asyncio.TimeoutError:
            self._active_workflows[workflow_id] = EnumWorkflowStatus.FAILED
            return self._create_timeout_output(input_data)

        except Exception as e:
            self._active_workflows[workflow_id] = EnumWorkflowStatus.FAILED
            # Recovery handling
            if input_data.failure_strategy == "retry":
                return await self._handle_retry(input_data, e)
            raise

    async def _validate_workflow_input(
        self,
        input_data: ModelOrchestratorInput,
    ) -> None:
        """Validate workflow input before execution.

        Args:
            input_data: Orchestrator input to validate

        Raises:
            ModelOnexError: If validation fails
        """
        if not input_data.steps:
            raise ModelOnexError(
                message="Workflow must have at least one step",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Validate steps against workflow definition
        workflow_steps = self.create_workflow_steps_from_config(input_data.steps)
        errors = await self.validate_workflow_steps(workflow_steps)

        if errors:
            raise ModelOnexError(
                message=f"Workflow validation failed: {errors}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

    async def _resolve_execution_order(
        self,
        input_data: ModelOrchestratorInput,
    ) -> list[UUID]:
        """Resolve step execution order based on dependencies.

        Args:
            input_data: Orchestrator input with steps

        Returns:
            List of step IDs in execution order

        Raises:
            ModelOnexError: If workflow contains cycles
        """
        workflow_steps = self.create_workflow_steps_from_config(input_data.steps)
        return self.get_execution_order_for_steps(workflow_steps)

    async def _execute_sequential_workflow(
        self,
        input_data: ModelOrchestratorInput,
        execution_order: list[UUID],
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps sequentially.

        Args:
            input_data: Orchestrator input
            execution_order: Ordered list of step IDs

        Returns:
            Orchestrator output with results
        """
        # Delegate to parent class workflow execution
        return await super().process(input_data)

    async def _execute_parallel_workflow(
        self,
        input_data: ModelOrchestratorInput,
        execution_order: list[UUID],
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps in parallel where dependencies allow.

        Args:
            input_data: Orchestrator input
            execution_order: Ordered list of step IDs

        Returns:
            Orchestrator output with results
        """
        # Use parent class with parallel execution mode
        return await super().process(input_data)

    async def _execute_conditional_workflow(
        self,
        input_data: ModelOrchestratorInput,
        execution_order: list[UUID],
    ) -> ModelOrchestratorOutput:
        """Execute workflow with conditional branching.

        Args:
            input_data: Orchestrator input
            execution_order: Ordered list of step IDs

        Returns:
            Orchestrator output with results
        """
        # Conditional execution delegates to parent with CONDITIONAL mode
        return await super().process(input_data)

    async def _handle_retry(
        self,
        input_data: ModelOrchestratorInput,
        error: Exception,
    ) -> ModelOrchestratorOutput:
        """Handle workflow retry on failure.

        Args:
            input_data: Original orchestrator input
            error: Exception that caused failure

        Returns:
            Orchestrator output from retry attempt
        """
        # Implement retry logic based on configuration
        return await self._recovery_handler.handle_retry(
            self, input_data, error
        )

    def _create_timeout_output(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """Create output for workflow timeout.

        Args:
            input_data: Original orchestrator input

        Returns:
            Orchestrator output indicating timeout
        """
        return ModelOrchestratorOutput(
            execution_status="failed",
            execution_time_ms=input_data.global_timeout_ms,
            start_time=input_data.timestamp.isoformat(),
            end_time=input_data.timestamp.isoformat(),
            failed_steps=["workflow_timeout"],
            errors=[{
                "step_id": "workflow",
                "error_type": "timeout",
                "message": f"Workflow exceeded {input_data.global_timeout_ms}ms timeout",
            }],
        )

    async def get_workflow_status(self, workflow_id: UUID) -> EnumWorkflowStatus:
        """Get current status of a workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Current workflow state

        Example:
            ```python
            status = await node.get_workflow_status(workflow_id)
            if status == EnumWorkflowStatus.RUNNING:
                print("Workflow is still executing")
            ```
        """
        return self._active_workflows.get(workflow_id, EnumWorkflowStatus.PENDING)

    async def cancel_workflow(self, workflow_id: UUID) -> bool:
        """Cancel a running workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            True if workflow was cancelled, False if not found or already complete

        Example:
            ```python
            cancelled = await node.cancel_workflow(workflow_id)
            if cancelled:
                print("Workflow cancelled successfully")
            ```
        """
        if workflow_id in self._active_workflows:
            current_state = self._active_workflows[workflow_id]
            if current_state == EnumWorkflowStatus.RUNNING:
                self._active_workflows[workflow_id] = EnumWorkflowStatus.CANCELLED
                return True
        return False

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status information
        """
        try:
            active_count = sum(
                1 for state in self._active_workflows.values()
                if state == EnumWorkflowStatus.RUNNING
            )

            return {
                "status": "healthy",
                "components": {
                    "step_executor": "healthy",
                    "dependency_resolver": "healthy",
                    "recovery_handler": "healthy",
                },
                "active_workflows": active_count,
                "workflow_definition_loaded": self.workflow_definition is not None,
            }

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "timestamp": time.time(),
            }
```

### 2. Configuration (`config.py`)

```python
"""Configuration for {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR node."""

from typing import Any, Type, TypeVar
from pydantic import BaseModel, ConfigDict, Field, field_validator


ConfigT = TypeVar('ConfigT', bound='BaseModel')


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )
    retry_delay_ms: int = Field(
        default=1000, ge=100, le=60000, description="Initial retry delay in milliseconds"
    )
    exponential_backoff: bool = Field(
        default=True, description="Enable exponential backoff for retries"
    )
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Multiplier for exponential backoff"
    )
    max_retry_delay_ms: int = Field(
        default=30000, ge=1000, le=300000, description="Maximum retry delay in milliseconds"
    )


class ParallelConfig(BaseModel):
    """Configuration for parallel execution."""

    max_parallel_steps: int = Field(
        default=5, ge=1, le=100, description="Maximum concurrent step execution"
    )
    batch_size: int = Field(
        default=10, ge=1, le=1000, description="Batch size for batch execution mode"
    )
    load_balancing_enabled: bool = Field(
        default=False, description="Enable load balancing across workers"
    )
    step_isolation: bool = Field(
        default=True, description="Isolate step execution for fault tolerance"
    )


class TimeoutConfig(BaseModel):
    """Configuration for timeout behavior."""

    global_timeout_ms: int = Field(
        default=300000, ge=1000, le=3600000, description="Global workflow timeout (5 minutes default)"
    )
    step_timeout_ms: int = Field(
        default=30000, ge=100, le=300000, description="Default step timeout"
    )
    shutdown_timeout_ms: int = Field(
        default=10000, ge=1000, le=60000, description="Graceful shutdown timeout"
    )


class {DomainCamelCase}{MicroserviceCamelCase}OrchestratorConfig(BaseModel):
    """Configuration for {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR operations."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Retry configuration
    retry_config: RetryConfig = Field(default_factory=RetryConfig)

    # Parallel execution configuration
    parallel_config: ParallelConfig = Field(default_factory=ParallelConfig)

    # Timeout configuration
    timeout_config: TimeoutConfig = Field(default_factory=TimeoutConfig)

    # Failure handling
    failure_strategy: str = Field(
        default="fail_fast",
        pattern="^(fail_fast|continue_on_error|retry|compensate)$",
        description="Strategy for handling step failures"
    )

    # Dependency resolution
    dependency_resolution_enabled: bool = Field(
        default=True, description="Enable automatic dependency resolution"
    )

    cycle_detection_enabled: bool = Field(
        default=True, description="Enable cycle detection in workflow graphs"
    )

    # Action tracking
    track_actions: bool = Field(
        default=True, description="Track emitted actions for debugging"
    )

    max_actions_per_workflow: int = Field(
        default=1000, ge=1, le=100000, description="Maximum actions per workflow"
    )

    # Domain-specific settings
    domain_specific_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific configuration parameters"
    )

    @field_validator('failure_strategy')
    @classmethod
    def validate_failure_strategy(cls, v: str) -> str:
        """Validate failure strategy value."""
        valid_strategies = {"fail_fast", "continue_on_error", "retry", "compensate"}
        if v not in valid_strategies:
            raise ValueError(f"Invalid failure strategy: {v}. Must be one of {valid_strategies}")
        return v

    @classmethod
    def for_environment(cls: Type[ConfigT], environment: str) -> ConfigT:
        """Create environment-specific configuration.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Environment-optimized configuration
        """
        if environment == "production":
            return cls(
                retry_config=RetryConfig(
                    max_retries=5,
                    retry_delay_ms=500,
                    exponential_backoff=True,
                ),
                parallel_config=ParallelConfig(
                    max_parallel_steps=10,
                    load_balancing_enabled=True,
                    step_isolation=True,
                ),
                timeout_config=TimeoutConfig(
                    global_timeout_ms=180000,  # 3 minutes
                    step_timeout_ms=20000,
                ),
                failure_strategy="retry",
            )

        elif environment == "staging":
            return cls(
                retry_config=RetryConfig(
                    max_retries=3,
                    retry_delay_ms=1000,
                ),
                parallel_config=ParallelConfig(
                    max_parallel_steps=5,
                ),
                timeout_config=TimeoutConfig(
                    global_timeout_ms=300000,  # 5 minutes
                ),
                failure_strategy="continue_on_error",
            )

        else:  # development
            return cls(
                retry_config=RetryConfig(
                    max_retries=1,
                    retry_delay_ms=100,
                    exponential_backoff=False,
                ),
                parallel_config=ParallelConfig(
                    max_parallel_steps=2,
                    load_balancing_enabled=False,
                ),
                timeout_config=TimeoutConfig(
                    global_timeout_ms=600000,  # 10 minutes
                    step_timeout_ms=60000,
                ),
                failure_strategy="fail_fast",
            )
```

### 3. Input Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_input.py`)

```python
"""Input model for {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR operations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.nodes import EnumExecutionMode


class Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput(BaseModel):
    """Input model for {DOMAIN} {MICROSERVICE_NAME} workflow orchestration.

    Strongly typed input wrapper for workflow coordination with comprehensive
    configuration for execution modes, parallelism, timeouts, and failure
    handling.

    This model is immutable (frozen=True) and thread-safe. Once created,
    instances cannot be modified.

    Example:
        >>> from uuid import uuid4
        >>> workflow = Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput(
        ...     workflow_id=uuid4(),
        ...     steps=[
        ...         {"step_name": "validate", "step_type": "compute"},
        ...         {"step_name": "persist", "step_type": "effect"},
        ...     ],
        ...     execution_mode=EnumExecutionMode.SEQUENTIAL,
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )

    # Workflow identification
    workflow_id: UUID = Field(
        ..., description="Unique workflow identifier"
    )

    workflow_type: str = Field(
        default="standard",
        description="Type of workflow being executed"
    )

    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID for tracing across services"
    )

    # Step definitions
    steps: list[dict[str, Any]] = Field(
        ..., description="Workflow step definitions"
    )

    # Execution configuration
    execution_mode: EnumExecutionMode = Field(
        default=EnumExecutionMode.SEQUENTIAL,
        description="Execution mode for workflow steps"
    )

    max_parallel_steps: int = Field(
        default=5, ge=1, le=100,
        description="Maximum concurrent steps in parallel mode"
    )

    # Timeout configuration
    global_timeout_ms: int = Field(
        default=300000, ge=1000, le=3600000,
        description="Global workflow timeout in milliseconds"
    )

    # Failure handling
    failure_strategy: str = Field(
        default="fail_fast",
        description="Strategy for handling step failures"
    )

    continue_on_error: bool = Field(
        default=False,
        description="Continue workflow execution on step errors"
    )

    # Dependencies
    dependency_resolution_enabled: bool = Field(
        default=True,
        description="Enable automatic dependency resolution"
    )

    # Load balancing
    load_balancing_enabled: bool = Field(
        default=False,
        description="Enable load balancing for distributed execution"
    )

    # Context and metadata
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow execution context"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional workflow metadata"
    )

    # Timestamps
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Workflow creation timestamp"
    )
```

### 4. Output Model (`model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_output.py`)

```python
"""Output model for {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR operations."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(BaseModel):
    """Output model for {DOMAIN} {MICROSERVICE_NAME} workflow orchestration.

    Type-safe orchestrator output providing structured result storage
    for workflow execution with validation.

    This model is immutable (frozen=True) and thread-safe.

    Example:
        >>> result = Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(
        ...     execution_status="completed",
        ...     execution_time_ms=1500,
        ...     start_time="2025-01-01T00:00:00Z",
        ...     end_time="2025-01-01T00:00:01Z",
        ...     completed_steps=["validate", "process", "persist"],
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    # Execution summary
    execution_status: str = Field(
        ..., description="Overall execution status (pending, running, completed, failed, cancelled)"
    )

    execution_time_ms: int = Field(
        ..., ge=0, description="Total execution time in milliseconds"
    )

    start_time: str = Field(
        ..., description="Workflow start timestamp (ISO format)"
    )

    end_time: str = Field(
        ..., description="Workflow end timestamp (ISO format)"
    )

    # Step tracking
    completed_steps: list[str] = Field(
        default_factory=list,
        description="List of completed step IDs"
    )

    failed_steps: list[str] = Field(
        default_factory=list,
        description="List of failed step IDs"
    )

    skipped_steps: list[str] = Field(
        default_factory=list,
        description="List of skipped step IDs"
    )

    # Step outputs
    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Outputs from each completed step"
    )

    # Final result
    final_result: Any | None = Field(
        default=None,
        description="Final workflow result (if aggregated)"
    )

    output_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Output variables from the workflow"
    )

    # Actions emitted (ModelAction pattern)
    actions_emitted: list[Any] = Field(
        default_factory=list,
        description="Actions emitted for deferred execution by target nodes"
    )

    # Error information
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of errors with step_id, error_type, and message"
    )

    # Metrics
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Execution performance metrics"
    )

    # Parallel execution tracking
    parallel_executions: int = Field(
        default=0, ge=0,
        description="Number of parallel execution batches completed"
    )
```

### 5. Workflow Type Enum (`enum_{DOMAIN}_{MICROSERVICE_NAME}_workflow_type.py`)

```python
"""Workflow type enumeration for {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR operations."""

from enum import Enum


class Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType(str, Enum):
    """Enumeration of supported {DOMAIN} {MICROSERVICE_NAME} workflow types."""

    DATA_PIPELINE = "data_pipeline"
    """Multi-stage data processing workflow."""

    BATCH_PROCESSING = "batch_processing"
    """Batch processing workflow for bulk operations."""

    EVENT_DRIVEN = "event_driven"
    """Event-driven workflow with conditional branching."""

    SAGA = "saga"
    """Distributed transaction workflow with compensation."""

    ETL = "etl"
    """Extract-Transform-Load workflow pattern."""

    APPROVAL = "approval"
    """Multi-step approval workflow with gates."""

    NOTIFICATION = "notification"
    """Notification dispatch workflow."""

    HEALTH_CHECK = "health_check"
    """System health validation workflow."""

    @classmethod
    def get_long_running_workflows(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType"]:
        """Get workflow types that typically run longer."""
        return [
            cls.DATA_PIPELINE,
            cls.BATCH_PROCESSING,
            cls.ETL,
            cls.SAGA,
        ]

    @classmethod
    def get_interactive_workflows(cls) -> list["Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType"]:
        """Get workflow types requiring user interaction."""
        return [
            cls.APPROVAL,
        ]

    def requires_compensation(self) -> bool:
        """Check if this workflow type requires compensation on failure."""
        return self == type(self).SAGA

    def supports_parallel_execution(self) -> bool:
        """Check if this workflow type supports parallel step execution."""
        return self in [
            type(self).DATA_PIPELINE,
            type(self).BATCH_PROCESSING,
            type(self).ETL,
        ]

    def get_default_timeout_ms(self) -> int:
        """Get default timeout for this workflow type."""
        timeout_map = {
            type(self).DATA_PIPELINE: 600000,  # 10 minutes
            type(self).BATCH_PROCESSING: 1800000,  # 30 minutes
            type(self).EVENT_DRIVEN: 60000,  # 1 minute
            type(self).SAGA: 300000,  # 5 minutes
            type(self).ETL: 3600000,  # 1 hour
            type(self).APPROVAL: 86400000,  # 24 hours
            type(self).NOTIFICATION: 30000,  # 30 seconds
            type(self).HEALTH_CHECK: 10000,  # 10 seconds
        }
        return timeout_map.get(self, 300000)
```

### 6. YAML Subcontracts

#### Workflow Definition (`subcontracts/workflow_definition.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR Workflow Definition
# Defines the workflow coordination contract

api_version: "v1.0.0"
kind: "WorkflowDefinition"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-orchestrator-workflow"
  description: "Workflow definition for {DOMAIN} {MICROSERVICE_NAME} orchestration"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "ORCHESTRATOR"

workflow_metadata:
  workflow_name: "{DOMAIN}_{MICROSERVICE_NAME}_pipeline"
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  execution_mode: "sequential"
  description: "Multi-stage {DOMAIN} {MICROSERVICE_NAME} workflow"

execution_graph:
  nodes:
    - node_id: "validate_input"
      node_type: "compute"
      description: "Validate incoming data"
      timeout_ms: 5000
      retry_count: 2

    - node_id: "fetch_data"
      node_type: "effect"
      description: "Fetch data from external sources"
      timeout_ms: 30000
      retry_count: 3
      depends_on: ["validate_input"]

    - node_id: "process_data"
      node_type: "compute"
      description: "Transform and process data"
      timeout_ms: 60000
      depends_on: ["fetch_data"]

    - node_id: "persist_results"
      node_type: "effect"
      description: "Persist processed results"
      timeout_ms: 15000
      depends_on: ["process_data"]

    - node_id: "notify_completion"
      node_type: "effect"
      description: "Send completion notification"
      timeout_ms: 5000
      depends_on: ["persist_results"]
      continue_on_error: true

coordination_rules:
  parallel_execution_allowed: false
  failure_recovery_strategy: "retry"
  max_retries: 3
  timeout_ms: 300000
  circuit_breaker_enabled: true
  dead_letter_queue_enabled: true
```

#### Input Subcontract (`subcontracts/input_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR Input Subcontract
# Defines the expected input structure for workflow orchestration

api_version: "v1.0.0"
kind: "InputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-orchestrator-input"
  description: "Input contract for {DOMAIN} {MICROSERVICE_NAME} workflow orchestration"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "ORCHESTRATOR"

schema:
  type: "object"
  required:
    - "workflow_id"
    - "steps"

  properties:
    workflow_id:
      type: "string"
      format: "uuid"
      description: "Unique workflow identifier"

    workflow_type:
      type: "string"
      enum:
        - "data_pipeline"
        - "batch_processing"
        - "event_driven"
        - "saga"
        - "etl"
        - "approval"
        - "notification"
        - "health_check"
      default: "data_pipeline"
      description: "Type of workflow being executed"

    correlation_id:
      type: "string"
      format: "uuid"
      description: "Correlation ID for distributed tracing"

    steps:
      type: "array"
      minItems: 1
      description: "Workflow step definitions"
      items:
        type: "object"
        required:
          - "step_name"
          - "step_type"
        properties:
          step_id:
            type: "string"
            format: "uuid"
            description: "Unique step identifier"
          step_name:
            type: "string"
            minLength: 1
            maxLength: 200
            description: "Human-readable step name"
          step_type:
            type: "string"
            enum:
              - "compute"
              - "effect"
              - "reducer"
              - "orchestrator"
              - "conditional"
              - "parallel"
              - "custom"
            description: "Type of step execution"
          timeout_ms:
            type: "integer"
            minimum: 100
            maximum: 300000
            default: 30000
            description: "Step timeout in milliseconds"
          retry_count:
            type: "integer"
            minimum: 0
            maximum: 10
            default: 3
            description: "Number of retry attempts"
          depends_on:
            type: "array"
            items:
              type: "string"
              format: "uuid"
            description: "Step IDs this step depends on"

    execution_mode:
      type: "string"
      enum:
        - "sequential"
        - "parallel"
        - "conditional"
        - "batch"
        - "streaming"
      default: "sequential"
      description: "Execution mode for workflow steps"

    max_parallel_steps:
      type: "integer"
      minimum: 1
      maximum: 100
      default: 5
      description: "Maximum concurrent steps in parallel mode"

    global_timeout_ms:
      type: "integer"
      minimum: 1000
      maximum: 3600000
      default: 300000
      description: "Global workflow timeout in milliseconds"

    failure_strategy:
      type: "string"
      enum:
        - "fail_fast"
        - "continue_on_error"
        - "retry"
        - "compensate"
      default: "fail_fast"
      description: "Strategy for handling step failures"

    context:
      type: "object"
      description: "Workflow execution context"
      additionalProperties: true

    metadata:
      type: "object"
      description: "Additional workflow metadata"
      additionalProperties: true

validation_rules:
  - name: "steps_have_unique_names"
    description: "All step names must be unique within the workflow"
    rule: |
      step_names = [step["step_name"] for step in steps]
      assert len(step_names) == len(set(step_names))

  - name: "dependencies_exist"
    description: "All step dependencies must reference existing steps"
    rule: |
      step_ids = {step.get("step_id") for step in steps}
      for step in steps:
        for dep_id in step.get("depends_on", []):
          assert dep_id in step_ids

examples:
  - name: "sequential_workflow"
    description: "Sequential data processing workflow"
    data:
      workflow_id: "550e8400-e29b-41d4-a716-446655440000"
      workflow_type: "data_pipeline"
      steps:
        - step_name: "validate"
          step_type: "compute"
          timeout_ms: 5000
        - step_name: "fetch"
          step_type: "effect"
          timeout_ms: 30000
        - step_name: "process"
          step_type: "compute"
          timeout_ms: 60000
      execution_mode: "sequential"
      failure_strategy: "retry"

  - name: "parallel_workflow"
    description: "Parallel batch processing workflow"
    data:
      workflow_id: "550e8400-e29b-41d4-a716-446655440001"
      workflow_type: "batch_processing"
      steps:
        - step_name: "batch_1"
          step_type: "compute"
        - step_name: "batch_2"
          step_type: "compute"
        - step_name: "batch_3"
          step_type: "compute"
      execution_mode: "parallel"
      max_parallel_steps: 3
```

#### Output Subcontract (`subcontracts/output_subcontract.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR Output Subcontract
# Defines the expected output structure for workflow orchestration

api_version: "v1.0.0"
kind: "OutputSubcontract"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-orchestrator-output"
  description: "Output contract for {DOMAIN} {MICROSERVICE_NAME} workflow orchestration"
  version: "1.0.0"
  domain: "{DOMAIN}"
  node_type: "ORCHESTRATOR"

schema:
  type: "object"
  required:
    - "execution_status"
    - "execution_time_ms"
    - "start_time"
    - "end_time"

  properties:
    execution_status:
      type: "string"
      enum:
        - "pending"
        - "running"
        - "paused"
        - "completed"
        - "failed"
        - "cancelled"
      description: "Overall workflow execution status"

    execution_time_ms:
      type: "integer"
      minimum: 0
      description: "Total execution time in milliseconds"

    start_time:
      type: "string"
      format: "date-time"
      description: "Workflow start timestamp (ISO format)"

    end_time:
      type: "string"
      format: "date-time"
      description: "Workflow end timestamp (ISO format)"

    completed_steps:
      type: "array"
      items:
        type: "string"
      description: "List of completed step IDs"

    failed_steps:
      type: "array"
      items:
        type: "string"
      description: "List of failed step IDs"

    skipped_steps:
      type: "array"
      items:
        type: "string"
      description: "List of skipped step IDs"

    step_outputs:
      type: "object"
      additionalProperties:
        type: "object"
      description: "Outputs from each completed step"

    final_result:
      description: "Final workflow result (if aggregated)"

    output_variables:
      type: "object"
      additionalProperties: true
      description: "Output variables from the workflow"

    actions_emitted:
      type: "array"
      description: "Actions emitted for deferred execution (ModelAction pattern)"
      items:
        type: "object"
        properties:
          action_id:
            type: "string"
            format: "uuid"
          action_type:
            type: "string"
            enum:
              - "compute"
              - "effect"
              - "reduce"
              - "orchestrate"
              - "custom"
          target_node:
            type: "string"
          payload:
            type: "object"

    errors:
      type: "array"
      items:
        type: "object"
        required:
          - "step_id"
          - "error_type"
          - "message"
        properties:
          step_id:
            type: "string"
          error_type:
            type: "string"
          message:
            type: "string"
      description: "List of errors encountered during execution"

    metrics:
      type: "object"
      additionalProperties:
        type: "number"
      description: "Execution performance metrics"

    parallel_executions:
      type: "integer"
      minimum: 0
      description: "Number of parallel execution batches completed"

validation_rules:
  - name: "status_consistency"
    description: "Validate status consistency with step results"
    rule: |
      if execution_status == "completed":
        assert len(failed_steps) == 0
      if execution_status == "failed":
        assert len(failed_steps) > 0 or len(errors) > 0

examples:
  - name: "successful_workflow"
    description: "Successfully completed workflow"
    data:
      execution_status: "completed"
      execution_time_ms: 5432
      start_time: "2025-01-15T10:00:00Z"
      end_time: "2025-01-15T10:00:05Z"
      completed_steps: ["validate", "fetch", "process", "persist"]
      failed_steps: []
      step_outputs:
        validate: { valid: true }
        fetch: { records: 1000 }
        process: { processed: 1000 }
        persist: { written: 1000 }
      metrics:
        completed_count: 4.0
        actions_count: 0.0
        avg_step_time_ms: 1358.0

  - name: "failed_workflow"
    description: "Workflow with step failure"
    data:
      execution_status: "failed"
      execution_time_ms: 2100
      start_time: "2025-01-15T10:00:00Z"
      end_time: "2025-01-15T10:00:02Z"
      completed_steps: ["validate", "fetch"]
      failed_steps: ["process"]
      errors:
        - step_id: "process"
          error_type: "timeout"
          message: "Step exceeded 60000ms timeout"
```

### 7. Manifest (`manifest.yaml`)

```yaml
# {DOMAIN} {MICROSERVICE_NAME} ORCHESTRATOR Node Manifest
# Defines metadata, dependencies, and deployment specifications

api_version: "v1.0.0"
kind: "NodeManifest"
metadata:
  name: "{DOMAIN}-{MICROSERVICE_NAME}-orchestrator"
  description: "ORCHESTRATOR node for {DOMAIN} {MICROSERVICE_NAME} workflow coordination"
  version: "1.0.0"
  domain: "{DOMAIN}"
  microservice_name: "{MICROSERVICE_NAME}"
  node_type: "ORCHESTRATOR"
  created_at: "2025-01-15T10:00:00Z"
  updated_at: "2025-01-15T10:00:00Z"
  maintainers:
    - "team@{DOMAIN}.com"
  tags:
    - "orchestrator"
    - "workflow"
    - "coordination"
    - "{DOMAIN}"
    - "onex-v4"

specification:
  # Node classification
  node_class: "ORCHESTRATOR"
  processing_type: "asynchronous"
  stateful: true

  # Workflow characteristics
  workflow:
    supports_sequential: true
    supports_parallel: true
    supports_conditional: true
    supports_compensation: true
    max_workflow_depth: 10
    max_steps_per_workflow: 100

  # Performance characteristics
  performance:
    expected_latency_ms: 100
    max_latency_ms: 1000
    throughput_workflows_per_second: 100
    memory_requirement_mb: 512
    cpu_requirement_cores: 2.0
    scaling_factor: "horizontal"

  # Reliability
  reliability:
    availability_target: "99.9%"
    error_rate_target: "0.1%"
    recovery_time_target_seconds: 30
    circuit_breaker_enabled: true
    retry_policy: "exponential_backoff"
    compensation_supported: true

# Dependencies
dependencies:
  runtime:
    python: ">=3.12,<4.0"
    pydantic: ">=2.11.0"
    asyncio: "builtin"

  internal:
    omnibase_core:
      version: ">=0.4.0"
      components:
        - "nodes.node_orchestrator"
        - "models.container.model_onex_container"
        - "models.orchestrator.model_orchestrator_input"
        - "models.orchestrator.model_orchestrator_output"
        - "enums.enum_workflow_execution"
        - "decorators.decorator_error_handling"
        - "errors.model_onex_error"

# Interface contracts
contracts:
  input:
    contract_file: "subcontracts/input_subcontract.yaml"
    validation_level: "strict"

  output:
    contract_file: "subcontracts/output_subcontract.yaml"
    validation_level: "strict"

  config:
    contract_file: "subcontracts/config_subcontract.yaml"
    validation_level: "strict"

  workflow:
    contract_file: "subcontracts/workflow_definition.yaml"
    validation_level: "strict"

# Testing requirements
testing:
  unit_tests:
    coverage_minimum: 90
    test_files:
      - "test_node.py"
      - "test_config.py"
      - "test_models.py"
      - "test_contracts.py"

  integration_tests:
    required: true
    test_scenarios:
      - "sequential_workflow"
      - "parallel_workflow"
      - "conditional_workflow"
      - "failure_recovery"
      - "compensation"
      - "timeout_handling"

# Monitoring
monitoring:
  metrics:
    - name: "workflow_duration_seconds"
      type: "histogram"
      description: "Time spent on workflow execution"
      labels: ["workflow_type", "execution_status"]

    - name: "workflow_step_count"
      type: "gauge"
      description: "Number of steps in workflow"

    - name: "actions_emitted_total"
      type: "counter"
      description: "Total actions emitted"
      labels: ["action_type"]

    - name: "workflow_errors_total"
      type: "counter"
      description: "Total workflow errors"
      labels: ["error_type", "workflow_type"]

    - name: "active_workflows"
      type: "gauge"
      description: "Number of currently active workflows"

  alerts:
    - name: "high_workflow_error_rate"
      condition: "error_rate > 5%"
      severity: "warning"

    - name: "workflow_timeout"
      condition: "workflow_duration > global_timeout"
      severity: "critical"
```

## Usage Instructions

### Template Customization

Replace the following placeholders throughout all files:

- `{REPOSITORY_NAME}`: Target repository name (e.g., "omniplan")
- `{DOMAIN}`: Business domain (e.g., "data", "finance", "analytics")
- `{MICROSERVICE_NAME}`: Specific microservice name (e.g., "pipeline_coordinator")
- `{DomainCamelCase}`: Domain in CamelCase (e.g., "Data", "Finance")
- `{MicroserviceCamelCase}`: Microservice in CamelCase (e.g., "PipelineCoordinator")

### Key Architectural Features

1. **Workflow-Driven Design**: All coordination logic defined in YAML contracts
2. **ModelAction Pattern**: Actions emitted for deferred execution by target nodes
3. **Lease-Based Semantics**: Single-writer coordination for distributed execution
4. **Dependency Resolution**: Automatic topological ordering of workflow steps
5. **Execution Modes**: Sequential, parallel, conditional, batch, and streaming
6. **Failure Recovery**: Built-in retry, compensation, and circuit breaker patterns
7. **Type Safety**: Immutable Pydantic models (frozen=True) for thread safety

### Implementation Checklist

- [ ] Replace all template placeholders
- [ ] Define workflow steps in `workflow_definition.yaml`
- [ ] Implement domain-specific step executors in `step_executor.py`
- [ ] Implement dependency resolution logic in `dependency_resolver.py`
- [ ] Implement recovery handlers in `recovery_handler.py`
- [ ] Update enum values to match domain requirements
- [ ] Write comprehensive unit tests for all execution modes
- [ ] Validate contract compliance
- [ ] Set up monitoring and alerting

### Thread Safety Considerations

ORCHESTRATOR nodes are NOT thread-safe by default due to:
- Active workflow state tracking
- Step completion status
- Workflow context accumulation

**Best Practice**: Use one node instance per thread, or implement explicit synchronization.
See `docs/guides/THREADING.md` for detailed patterns.

### v0.4.0 Import Reference

```python
# Node class
from omnibase_core.nodes import NodeOrchestrator

# Input/Output models
from omnibase_core.nodes import ModelOrchestratorInput, ModelOrchestratorOutput

# Workflow enums
from omnibase_core.nodes import (
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowStatus,
)

# Container for DI
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Error handling
from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
```

This template ensures all ORCHESTRATOR nodes follow the unified ONEX architecture with workflow-driven coordination, ModelAction patterns, and lease-based distributed execution semantics.
