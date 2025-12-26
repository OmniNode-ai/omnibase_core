# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Input model for NodeOrchestrator operations.

This module provides the ModelOrchestratorInput class that wraps workflow
coordination operations with comprehensive configuration for execution modes,
parallelism, timeouts, and failure handling strategies.

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

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator import ModelOrchestratorInput
    >>> from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
    >>>
    >>> # Simple sequential workflow
    >>> workflow = ModelOrchestratorInput(
    ...     workflow_id=uuid4(),
    ...     steps=[
    ...         {"name": "validate", "action": "validate_input"},
    ...         {"name": "process", "action": "transform_data"},
    ...         {"name": "persist", "action": "save_result"},
    ...     ],
    ...     execution_mode=EnumExecutionMode.SEQUENTIAL,
    ... )
    >>>
    >>> # Parallel workflow with load balancing
    >>> parallel_workflow = ModelOrchestratorInput(
    ...     workflow_id=uuid4(),
    ...     steps=[{"name": f"worker_{i}", "action": "process"} for i in range(10)],
    ...     execution_mode=EnumExecutionMode.PARALLEL,
    ...     max_parallel_steps=5,
    ...     load_balancing_enabled=True,
    ...     failure_strategy="continue_on_error",
    ... )

See Also:
    - omnibase_core.models.orchestrator.model_orchestrator_output: Output model
    - omnibase_core.nodes.node_orchestrator: NodeOrchestrator implementation
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.orchestrator.model_orchestrator_input_metadata import (
    ModelOrchestratorInputMetadata,
)


class ModelOrchestratorInput(BaseModel):
    """
    Input model for NodeOrchestrator operations.

    Strongly typed input wrapper for workflow coordination with comprehensive
    configuration for execution modes, parallelism, timeouts, and failure
    handling. Used by NodeOrchestrator to coordinate multi-step workflows.

    Attributes:
        workflow_id: Unique identifier for this workflow instance.
        steps: List of workflow step definitions. Each step is a dictionary
            containing at minimum 'name' and 'action' keys.
        operation_id: Unique identifier for tracking this operation.
            Auto-generated UUID by default.
        execution_mode: How steps should be executed (SEQUENTIAL, PARALLEL,
            CONDITIONAL). Defaults to SEQUENTIAL.
        max_parallel_steps: Maximum number of steps to run concurrently when
            using PARALLEL execution mode. Defaults to 5.
        global_timeout_ms: Maximum time for entire workflow completion in
            milliseconds. Defaults to 300000 (5 minutes).
        failure_strategy: How to handle step failures. Options: 'fail_fast'
            (stop immediately), 'continue_on_error', 'retry'. Defaults to 'fail_fast'.
        load_balancing_enabled: Whether to use load balancer for distributing
            operations. Defaults to False.
        dependency_resolution_enabled: Whether to automatically resolve step
            dependencies based on declared inputs/outputs. Defaults to True.
        metadata: Typed workflow metadata for observability, FSM control, and persistence.
        timestamp: When this input was created. Auto-generated to current time.

    Example:
        >>> # Conditional workflow with dependencies
        >>> workflow = ModelOrchestratorInput(
        ...     workflow_id=uuid4(),
        ...     steps=[
        ...         {"name": "fetch", "action": "fetch_data"},
        ...         {"name": "validate", "action": "validate", "depends_on": ["fetch"]},
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
    steps: list[dict[str, Any]] = Field(  # ONEX_EXCLUDE: dict_str_any - heterogeneous
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
    metadata: ModelOrchestratorInputMetadata = Field(
        default_factory=ModelOrchestratorInputMetadata,
        description="Typed workflow metadata for observability, FSM control, and persistence",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Workflow creation timestamp"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=False,
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
