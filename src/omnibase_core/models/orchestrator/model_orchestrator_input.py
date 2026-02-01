"""
Input model for NodeOrchestrator operations.

This module provides the ModelOrchestratorInput class that wraps workflow
coordination operations with comprehensive configuration for execution modes,
parallelism, timeouts, and failure handling strategies.

v1.0.2 Normative:
    Steps MUST arrive as typed ModelWorkflowStep instances. YAML is compiled
    into typed Pydantic models upstream during contract load by SPI/Infra.
    Core receives fully typed models. Core does NOT parse YAML. Core does NOT
    coerce dicts into models.

Thread Safety:
    ModelOrchestratorInput itself is frozen (frozen=True), meaning top-level
    fields cannot be reassigned after creation. However, the `metadata` field
    contains a mutable ModelOrchestratorInputMetadata object that can be
    modified in place. If thread safety is required, either:
    (a) Do not mutate metadata after creation, or
    (b) Use appropriate synchronization when accessing metadata across threads.

Key Features:
    - Multiple execution modes (SEQUENTIAL, PARALLEL, CONDITIONAL)
    - Configurable parallelism with max concurrent steps
    - Global timeout with per-step override support
    - Failure strategies (fail_fast, continue_on_error, retry)
    - Load balancing integration for distributed execution
    - Automatic dependency resolution between steps

v1.0.x Note:
    This model uses the `steps` list with `depends_on` for workflow execution.
    The `execution_graph` field in ModelWorkflowDefinition is reserved for v1.1+
    and MUST NOT be consulted by the v1.0 executor. See:
    - models/contracts/subcontracts/model_execution_graph.py for v1.1+ roadmap
    - docs/architecture/CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md for v1.0 spec

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator import ModelOrchestratorInput
    >>> from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
    >>> from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
    >>>
    >>> # Define step IDs for dependency tracking
    >>> step1_id = uuid4()
    >>> step2_id = uuid4()
    >>> step3_id = uuid4()
    >>>
    >>> # Simple sequential workflow with typed steps (v1.0.2 compliant)
    >>> workflow = ModelOrchestratorInput(
    ...     workflow_id=uuid4(),
    ...     steps=[
    ...         ModelWorkflowStep(
    ...             step_id=step1_id,
    ...             step_name="validate",
    ...             step_type="compute",
    ...         ),
    ...         ModelWorkflowStep(
    ...             step_id=step2_id,
    ...             step_name="process",
    ...             step_type="compute",
    ...             depends_on=[step1_id],
    ...         ),
    ...         ModelWorkflowStep(
    ...             step_id=step3_id,
    ...             step_name="persist",
    ...             step_type="effect",
    ...             depends_on=[step2_id],
    ...         ),
    ...     ],
    ...     execution_mode=EnumExecutionMode.SEQUENTIAL,
    ... )

See Also:
    - omnibase_core.models.orchestrator.model_orchestrator_output: Output model
    - omnibase_core.nodes.node_orchestrator: NodeOrchestrator implementation
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.constants.constants_field_limits import MAX_TIMEOUT_MS
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.orchestrator.model_orchestrator_input_metadata import (
    ModelOrchestratorInputMetadata,
)


class ModelOrchestratorInput(BaseModel):
    """
    Input model for NodeOrchestrator operations.

    Strongly typed input wrapper for workflow coordination with comprehensive
    configuration for execution modes, parallelism, timeouts, and failure
    handling. Used by NodeOrchestrator to coordinate multi-step workflows.

    v1.0.2 Normative:
        Steps MUST be typed ModelWorkflowStep instances. Dict coercion is NOT
        supported. YAML is compiled into typed Pydantic models upstream during
        contract load by SPI/Infra. Core receives fully typed models. Core does
        NOT parse YAML. Core does NOT coerce dicts into models.

    Thread Safety:
        This model is top-level frozen (frozen=True), meaning you cannot reassign
        fields after creation. However, the `metadata` field contains a mutable
        ModelOrchestratorInputMetadata object that CAN be modified in place.

        Warning:
            Do NOT mutate nested metadata across threads without synchronization.
            If thread safety is required, either:
            (a) Treat metadata as read-only after creation, or
            (b) Use explicit locks when accessing metadata across threads, or
            (c) Create new instances using `model_copy(update={"metadata": ...})`

    Attributes:
        workflow_id: Unique identifier for this workflow instance.
        steps: List of typed ModelWorkflowStep instances. Each step contains
            step_id, step_name, step_type, timeout_ms, depends_on, and other
            execution configuration. Steps MUST be typed - no dict coercion.
        operation_id: Unique identifier for tracking this operation.
            Auto-generated UUID by default.
        execution_mode: How steps should be executed (SEQUENTIAL, PARALLEL,
            CONDITIONAL). Defaults to SEQUENTIAL.
        max_parallel_steps: Maximum number of steps to run concurrently when
            using PARALLEL execution mode. Defaults to 5.
        global_timeout_ms: Maximum time for entire workflow completion in
            milliseconds. Defaults to TIMEOUT_LONG_MS (5 minutes).
            See omnibase_core.constants for timeout constant values.
        failure_strategy: How to handle step failures. Options: 'fail_fast'
            (stop immediately), 'continue_on_error', 'retry'. Defaults to 'fail_fast'.
        load_balancing_enabled: Whether to use load balancer for distributing
            operations. Defaults to False.
        dependency_resolution_enabled: Whether to automatically resolve step
            dependencies based on declared inputs/outputs. Defaults to True.
        metadata: Typed workflow metadata for observability, FSM control, and persistence.
        timestamp: When this input was created. Auto-generated to current time.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
        >>>
        >>> # Workflow with typed steps and dependencies (v1.0.2 compliant)
        >>> fetch_id = uuid4()
        >>> validate_id = uuid4()
        >>> workflow = ModelOrchestratorInput(
        ...     workflow_id=uuid4(),
        ...     steps=[
        ...         ModelWorkflowStep(
        ...             step_id=fetch_id,
        ...             step_name="fetch",
        ...             step_type="effect",
        ...         ),
        ...         ModelWorkflowStep(
        ...             step_id=validate_id,
        ...             step_name="validate",
        ...             step_type="compute",
        ...             depends_on=[fetch_id],
        ...         ),
        ...     ],
        ...     dependency_resolution_enabled=True,
        ... )
        >>>
        >>> # To "update" a frozen model, use model_copy
        >>> original = ModelOrchestratorInput(workflow_id=uuid4(), steps=[])
        >>> new_meta = ModelOrchestratorInputMetadata(source="updated")
        >>> updated = original.model_copy(update={"metadata": new_meta})
    """

    workflow_id: UUID = Field(..., description="Unique workflow identifier")
    steps: list[ModelWorkflowStep] = Field(
        ...,
        description="Typed ModelWorkflowStep instances. Steps MUST be typed - no dict coercion.",
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
        default=TIMEOUT_LONG_MS,
        ge=100,  # v1.0.3: Minimum timeout validation for consistency with per-step timeouts
        le=MAX_TIMEOUT_MS,  # Max 24 hours - prevents DoS via excessively long timeouts
        description="Global workflow timeout (5 minutes default)",
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
    metadata: ModelOrchestratorInputMetadata = Field(
        default_factory=ModelOrchestratorInputMetadata,
        description="Typed workflow metadata for observability, FSM control, and persistence",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )

    model_config = ConfigDict(
        # v1.0.2: Steps are now typed ModelWorkflowStep instances (not dicts),
        # so arbitrary_types_allowed is no longer needed for heterogeneous structures.
        use_enum_values=False,
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelOrchestratorInput"]
