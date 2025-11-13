"""
VERSION: 1.0.0
STABILITY GUARANTEE: Abstract method signatures frozen.
Breaking changes require major version bump.

NodeOrchestrator - Workflow Coordination Node for 4-Node Architecture.

Specialized node type for workflow coordination and control flow management.
Focuses on thunk emission patterns, conditional branching, and parallel execution coordination.

Key Capabilities:
- Workflow coordination with control flow
- Thunk emission patterns for deferred execution
- Conditional branching based on runtime state
- Parallel execution coordination
- RSD Workflow Management (ticket lifecycle state transitions)
- Dependency-aware execution ordering
- Batch processing coordination with load balancing
- Error recovery and partial failure handling

STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.
Code generators can target this stable interface.

Author: ONEX Framework Team
"""

import asyncio
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.infrastructure.node_config_provider import NodeConfigProvider
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_load_balancer import ModelLoadBalancer
from omnibase_core.models.model_orchestrator_input import ModelOrchestratorInput
from omnibase_core.models.orchestrator import ModelOrchestratorOutput
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.workflows.model_dependency_graph import ModelDependencyGraph
from omnibase_core.models.workflows.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)


class NodeOrchestrator(NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Workflow coordination node for control flow management.

    Implements workflow coordination with action emission for deferred execution,
    conditional branching, and parallel coordination. Optimized for RSD workflow
    management including ticket lifecycle transitions and dependency-aware ordering.

    Key Features:
    - Action emission patterns for deferred execution
    - Conditional branching based on runtime state
    - Parallel execution coordination with load balancing
    - Dependency-aware execution ordering
    - Error recovery and partial failure handling
    - Performance monitoring and optimization

    RSD Workflow Management:
    - Ticket lifecycle state transitions
    - Dependency-aware execution ordering
    - Batch processing coordination with load balancing
    - Error recovery and partial failure handling
    """

    # Class attribute declarations for mypy
    max_concurrent_workflows: int
    default_step_timeout_ms: int
    action_emission_enabled: bool
    active_workflows: dict[UUID, ModelOrchestratorInput]
    workflow_states: dict[UUID, EnumWorkflowState]
    load_balancer: ModelLoadBalancer
    emitted_actions: dict[UUID, list[ModelAction]]
    workflow_semaphore: asyncio.Semaphore
    orchestration_metrics: dict[str, dict[str, float]]
    condition_functions: dict[str, Callable[..., Any]]

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeOrchestrator with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Use object.__setattr__() to bypass Pydantic validation for internal state
        # Orchestrator-specific configuration (defaults, overridden in _initialize_node_resources)
        # These defaults are used if ProtocolNodeConfiguration is not available
        object.__setattr__(self, "max_concurrent_workflows", 5)
        object.__setattr__(self, "default_step_timeout_ms", 30000)
        object.__setattr__(self, "action_emission_enabled", True)

        # Active workflows tracking (UUID keys for workflow_id)
        object.__setattr__(self, "active_workflows", {})
        object.__setattr__(self, "workflow_states", {})

        # Load balancer for operation distribution
        object.__setattr__(
            self, "load_balancer", ModelLoadBalancer(max_concurrent_operations=20)
        )

        # Action emission registry (UUID keys for workflow_id)
        object.__setattr__(self, "emitted_actions", {})

        # Workflow execution semaphore
        object.__setattr__(
            self, "workflow_semaphore", asyncio.Semaphore(self.max_concurrent_workflows)
        )

        # Performance tracking
        object.__setattr__(self, "orchestration_metrics", {})

        # Conditional functions registry
        object.__setattr__(self, "condition_functions", {})

        # Register built-in condition functions
        self._register_builtin_conditions()

    async def process(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        REQUIRED: Execute workflow coordination with thunk emission.

        STABLE INTERFACE: This method signature is frozen for code generation.

        Args:
            input_data: Strongly typed orchestration input with workflow configuration

        Returns:
            Strongly typed orchestration output with execution results

        Raises:
            ModelOnexError: If workflow coordination fails
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_orchestrator_input(input_data)

            # Acquire workflow semaphore
            async with self.workflow_semaphore:
                # Register active workflow
                self.active_workflows[input_data.workflow_id] = input_data
                self.workflow_states[input_data.workflow_id] = EnumWorkflowState.RUNNING

                # Build dependency graph if enabled
                dependency_graph = None
                if input_data.dependency_resolution_enabled:
                    dependency_graph = self._build_dependency_graph(input_data.steps)

                    # Check for cycles
                    if dependency_graph.has_cycles():
                        raise ModelOnexError(
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            message="Workflow contains dependency cycles",
                            context={
                                "node_id": str(self.node_id),
                                "workflow_id": str(input_data.workflow_id),
                                "operation_id": str(input_data.operation_id),
                            },
                        )

                # Execute workflow based on mode
                if input_data.execution_mode == EnumExecutionMode.SEQUENTIAL:
                    result = await self._execute_sequential_workflow(
                        input_data,
                        dependency_graph,
                    )
                elif input_data.execution_mode == EnumExecutionMode.PARALLEL:
                    result = await self._execute_parallel_workflow(
                        input_data,
                        dependency_graph,
                    )
                elif input_data.execution_mode == EnumExecutionMode.BATCH:
                    result = await self._execute_batch_workflow(
                        input_data,
                        dependency_graph,
                    )
                else:
                    result = await self._execute_sequential_workflow(
                        input_data,
                        dependency_graph,
                    )

                # Update workflow state
                self.workflow_states[input_data.workflow_id] = (
                    EnumWorkflowState.COMPLETED
                )

                processing_time = (time.time() - start_time) * 1000

                # Update metrics
                await self._update_orchestration_metrics(
                    input_data.execution_mode.value,
                    processing_time,
                    True,
                    len(input_data.steps),
                )
                await self._update_processing_metrics(processing_time, True)

                emit_log_event(
                    LogLevel.INFO,
                    f"Workflow orchestration completed: {input_data.workflow_id}",
                    {
                        "node_id": str(self.node_id),
                        "workflow_id": str(input_data.workflow_id),
                        "operation_id": str(input_data.operation_id),
                        "processing_time_ms": processing_time,
                        "steps_completed": len(result.completed_steps),
                        "failed_steps": len(result.failed_steps),
                    },
                )

                return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # Update workflow state and metrics
            if input_data.workflow_id in self.workflow_states:
                self.workflow_states[input_data.workflow_id] = EnumWorkflowState.FAILED

            await self._update_orchestration_metrics(
                input_data.execution_mode.value,
                processing_time,
                False,
                len(input_data.steps),
            )
            await self._update_processing_metrics(processing_time, False)

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Workflow orchestration failed: {e!s}",
                context={
                    "node_id": str(self.node_id),
                    "workflow_id": str(input_data.workflow_id),
                    "operation_id": str(input_data.operation_id),
                    "processing_time_ms": processing_time,
                    "error": str(e),
                },
            ) from e

        finally:
            # Cleanup active workflow
            if input_data.workflow_id in self.active_workflows:
                del self.active_workflows[input_data.workflow_id]

    async def orchestrate_rsd_ticket_lifecycle(
        self,
        ticket_id: UUID,
        current_state: str,
        target_state: str,
        dependency_tickets: list[UUID] | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate RSD ticket lifecycle state transitions.

        Creates workflow for transitioning ticket through states while
        respecting dependencies and applying validation at each step.

        Args:
            ticket_id: Unique ticket identifier (UUID)
            current_state: Current ticket state
            target_state: Desired target state
            dependency_tickets: List of dependent ticket IDs (UUIDs)

        Returns:
            Workflow execution results with state transition details

        Raises:
            ModelOnexError: If workflow creation or execution fails
        """
        # Create workflow steps for state transition
        steps = self._create_ticket_lifecycle_steps(
            ticket_id,
            current_state,
            target_state,
            dependency_tickets or [],
        )

        workflow_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            dependency_resolution_enabled=True,
            failure_strategy="rollback",
            metadata={
                "ticket_id": str(ticket_id),
                "current_state": current_state,
                "target_state": target_state,
                "rsd_operation": "ticket_lifecycle",
            },
        )

        result = await self.process(workflow_input)

        return {
            "ticket_id": str(ticket_id),
            "workflow_id": str(workflow_input.workflow_id),
            "state_transition": f"{current_state} -> {target_state}",
            "steps_completed": len(result.completed_steps),
            "processing_time_ms": result.execution_time_ms,
            "failed_steps": len(result.failed_steps),
            "success": result.execution_status == "completed",
        }

    async def emit_action(
        self,
        action_type: EnumActionType,
        target_node_type: str,
        payload: dict[str, Any],
        dependencies: list[UUID] | None = None,
        priority: int = 1,
        timeout_ms: int = 30000,
        lease_id: UUID | None = None,
        epoch: int = 0,
    ) -> ModelAction:
        """
        Emit action for deferred execution.

        Args:
            action_type: Type of action to emit
            target_node_type: Target node type for execution
            payload: Data payload for the operation
            dependencies: List of dependency action IDs (UUIDs)
            priority: Execution priority (higher = more urgent)
            timeout_ms: Execution timeout in milliseconds
            lease_id: Lease ID for ownership tracking (auto-generated if None)
            epoch: Version number for action (default 0)

        Returns:
            Created action instance
        """
        action = ModelAction(
            action_id=uuid4(),
            action_type=action_type,
            target_node_type=target_node_type,
            payload=payload,
            dependencies=dependencies or [],
            priority=priority,
            timeout_ms=timeout_ms,
            lease_id=lease_id or uuid4(),
            epoch=epoch,
            retry_count=0,
            metadata={
                "emitted_by": str(self.node_id),
                "emission_time": datetime.now().isoformat(),
            },
            created_at=datetime.now(),
        )

        # Store emitted action (workflow_id should be UUID from payload)
        workflow_id_value = payload.get("workflow_id")
        if workflow_id_value is not None:
            # Ensure workflow_id is UUID type
            if isinstance(workflow_id_value, str):
                workflow_id = UUID(workflow_id_value)
            else:
                workflow_id = workflow_id_value

            if workflow_id not in self.emitted_actions:
                self.emitted_actions[workflow_id] = []
            self.emitted_actions[workflow_id].append(action)

        emit_log_event(
            LogLevel.INFO,
            f"Action emitted: {action_type.value} -> {target_node_type}",
            {
                "node_id": str(self.node_id),
                "action_id": str(action.action_id),
                "action_type": action_type.value,
                "target_node_type": target_node_type,
                "priority": priority,
                "dependencies": len(dependencies or []),
            },
        )

        return action

    def register_condition_function(
        self,
        condition_name: str,
        function: Callable[..., Any],
    ) -> None:
        """
        Register custom condition function for branching.

        Args:
            condition_name: Name for the condition
            function: Function that returns True/False for branching

        Raises:
            ModelOnexError: If condition already registered or function invalid
        """
        if condition_name in self.condition_functions:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Condition function already registered: {condition_name}",
                context={
                    "node_id": str(self.node_id),
                    "condition_name": condition_name,
                },
            )

        if not callable(function):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Condition function must be callable: {condition_name}",
                context={
                    "node_id": str(self.node_id),
                    "condition_name": condition_name,
                },
            )

        self.condition_functions[condition_name] = function

        emit_log_event(
            LogLevel.INFO,
            f"Condition function registered: {condition_name}",
            {"node_id": str(self.node_id), "condition_name": condition_name},
        )

    async def get_orchestration_metrics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed orchestration performance metrics.

        Returns:
            Dictionary of metrics by execution mode
        """
        load_balancer_stats = self.load_balancer.get_stats()

        return {
            **self.orchestration_metrics,
            "load_balancing": {
                "active_operations": float(load_balancer_stats["active_operations"]),
                "max_concurrent": float(load_balancer_stats["max_concurrent"]),
                "utilization": load_balancer_stats["utilization"],
                "total_operations": float(load_balancer_stats["total_operations"]),
            },
            "workflow_management": {
                "active_workflows": float(len(self.active_workflows)),
                "max_concurrent_workflows": float(self.max_concurrent_workflows),
                "total_actions_emitted": float(
                    sum(len(actions) for actions in self.emitted_actions.values()),
                ),
                "condition_functions_registered": float(len(self.condition_functions)),
            },
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize orchestrator-specific resources."""
        # Load configuration from NodeConfigProvider if available
        config = self.container.get_service_optional(NodeConfigProvider)
        if config:
            # Load performance configurations
            max_workflows_value = await config.get_performance_config(
                "orchestrator.max_concurrent_workflows",
                default=self.max_concurrent_workflows,
            )

            # Load timeout configurations
            step_timeout_value = await config.get_timeout_ms(
                "orchestrator.default_step_timeout_ms",
                default_ms=self.default_step_timeout_ms,
            )

            # Load business logic configurations
            action_emission_value = await config.get_business_logic_config(
                "orchestrator.action_emission_enabled",
                default=self.action_emission_enabled,
            )

            # Update configuration values with type checking
            if isinstance(max_workflows_value, (int, float)):
                self.max_concurrent_workflows = int(max_workflows_value)
                # Update semaphore with new value
                self.workflow_semaphore = asyncio.Semaphore(
                    self.max_concurrent_workflows
                )
            if isinstance(step_timeout_value, int):
                self.default_step_timeout_ms = step_timeout_value
            if isinstance(action_emission_value, bool):
                self.action_emission_enabled = action_emission_value

            emit_log_event(
                LogLevel.INFO,
                "NodeOrchestrator loaded configuration from NodeConfigProvider",
                {
                    "node_id": str(self.node_id),
                    "max_concurrent_workflows": self.max_concurrent_workflows,
                    "default_step_timeout_ms": self.default_step_timeout_ms,
                    "action_emission_enabled": self.action_emission_enabled,
                },
            )

        emit_log_event(
            LogLevel.INFO,
            "NodeOrchestrator resources initialized",
            {
                "node_id": str(self.node_id),
                "max_concurrent_workflows": self.max_concurrent_workflows,
                "action_emission_enabled": self.action_emission_enabled,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup orchestrator-specific resources."""
        # Cancel active workflows
        for workflow_id in list(self.active_workflows.keys()):
            self.workflow_states[workflow_id] = EnumWorkflowState.CANCELLED
            emit_log_event(
                LogLevel.WARNING,
                f"Cancelled active workflow during cleanup: {workflow_id}",
                {"node_id": str(self.node_id), "workflow_id": str(workflow_id)},
            )

        self.active_workflows.clear()
        self.emitted_actions.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeOrchestrator resources cleaned up",
            {"node_id": str(self.node_id)},
        )

    def _validate_orchestrator_input(self, input_data: ModelOrchestratorInput) -> None:
        """
        Validate orchestrator input data.

        Args:
            input_data: Input data to validate

        Raises:
            ModelOnexError: If validation fails
        """
        super()._validate_input_data(input_data)

        if not input_data.workflow_id:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Workflow ID cannot be empty",
                context={
                    "node_id": str(self.node_id),
                    "operation_id": str(input_data.operation_id),
                },
            )

        if not input_data.steps:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Workflow must have at least one step",
                context={
                    "node_id": str(self.node_id),
                    "workflow_id": str(input_data.workflow_id),
                },
            )

        if not isinstance(input_data.execution_mode, EnumExecutionMode):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Execution mode must be valid EnumExecutionMode enum",
                context={
                    "node_id": str(self.node_id),
                    "execution_mode": str(input_data.execution_mode),
                },
            )

    def _build_dependency_graph(
        self, steps: list[dict[str, Any]]
    ) -> ModelDependencyGraph:
        """Build dependency graph from workflow steps."""
        graph = ModelDependencyGraph()

        # Convert dict steps to ModelWorkflowStep (simplified for now)
        workflow_steps = [self._dict_to_workflow_step(step_dict) for step_dict in steps]

        # Add all steps
        for step in workflow_steps:
            graph.add_step(step)

        # Add dependencies based on action dependencies
        for step in workflow_steps:
            for action in step.thunks:
                for dep_id in action.dependencies:
                    # Find step containing dependency action
                    for other_step in workflow_steps:
                        if any(a.action_id == dep_id for a in other_step.thunks):
                            graph.add_dependency(other_step.step_id, step.step_id)
                            break

        return graph

    def _dict_to_workflow_step(
        self, step_dict: dict[str, Any]
    ) -> ModelWorkflowStepExecution:
        """Convert dictionary to ModelWorkflowStepExecution."""
        # Handle step_id - convert to UUID if string
        step_id_value = step_dict.get("step_id")
        if step_id_value is None:
            step_id = uuid4()
        elif isinstance(step_id_value, str):
            step_id = UUID(step_id_value)
        else:
            step_id = step_id_value

        return ModelWorkflowStepExecution(
            step_id=step_id,
            step_name=step_dict.get("step_name", "Unnamed Step"),
            execution_mode=step_dict.get(
                "execution_mode", EnumExecutionMode.SEQUENTIAL
            ),
            thunks=[
                ModelAction(**thunk_dict) for thunk_dict in step_dict.get("actions", [])
            ],
            condition=step_dict.get("condition"),
            condition_function=None,
            timeout_ms=step_dict.get("timeout_ms", 30000),
            retry_count=step_dict.get("retry_count", 0),
            metadata=step_dict.get("metadata", {}),
            started_at=None,
            completed_at=None,
            error=None,
        )

    async def _execute_sequential_workflow(
        self,
        input_data: ModelOrchestratorInput,
        dependency_graph: ModelDependencyGraph | None,
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps sequentially."""
        completed_step_ids: list[str] = []
        failed_step_ids: list[str] = []
        all_actions = []
        all_results: list[Any] = []
        start_time = datetime.now()

        # Convert dict steps to ModelWorkflowStep
        workflow_steps = [
            self._dict_to_workflow_step(step_dict) for step_dict in input_data.steps
        ]

        # Determine execution order
        if dependency_graph:
            execution_order = self._get_topological_order(dependency_graph)
            ordered_steps = [
                next(s for s in workflow_steps if s.step_id == UUID(step_id))
                for step_id in execution_order
            ]
        else:
            ordered_steps = workflow_steps

        for step in ordered_steps:
            try:
                # Check condition if specified
                if step.condition and not await self._evaluate_condition(
                    step,
                    all_results,
                ):
                    emit_log_event(
                        LogLevel.INFO,
                        f"Step skipped due to condition: {step.step_name}",
                        {
                            "step_id": str(step.step_id),
                            "condition": step.condition.value,
                        },
                    )
                    continue

                step.state = EnumWorkflowState.RUNNING
                step.started_at = datetime.now()

                # Execute step actions
                step_results = []
                for action in step.thunks:
                    if self.action_emission_enabled:
                        emitted_action = await self.emit_action(
                            action.action_type,
                            action.target_node_type,
                            {
                                **action.payload,
                                "workflow_id": input_data.workflow_id,
                            },
                            action.dependencies,
                            action.priority,
                            action.timeout_ms,
                            action.lease_id,
                            action.epoch,
                        )
                        all_actions.append(emitted_action)

                    # Simulate action execution result
                    step_results.append(
                        {"action_id": str(action.action_id), "status": "executed"},
                    )

                step.results = step_results
                step.state = EnumWorkflowState.COMPLETED
                step.completed_at = datetime.now()
                completed_step_ids.append(str(step.step_id))
                all_results.extend(step_results)

                # Update dependency graph
                if dependency_graph:
                    dependency_graph.mark_completed(step.step_id)

            except Exception as e:
                step.state = EnumWorkflowState.FAILED
                step.error = e
                failed_step_ids.append(str(step.step_id))

                if input_data.failure_strategy == "fail_fast":
                    raise
                # Continue for other failure strategies

        end_time = datetime.now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return ModelOrchestratorOutput(
            execution_status="completed" if len(failed_step_ids) == 0 else "failed",
            execution_time_ms=execution_time_ms,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            completed_steps=completed_step_ids,
            failed_steps=failed_step_ids,
            final_result=all_results if all_results else None,
            actions_emitted=all_actions,
        )

    async def _execute_parallel_workflow(
        self,
        input_data: ModelOrchestratorInput,
        dependency_graph: ModelDependencyGraph | None,
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps in parallel respecting dependencies."""
        completed_step_ids: list[str] = []
        failed_step_ids: list[str] = []
        all_actions = []
        all_results = []
        parallel_executions = 0
        start_time = datetime.now()

        # Convert dict steps to ModelWorkflowStep
        workflow_steps = [
            self._dict_to_workflow_step(step_dict) for step_dict in input_data.steps
        ]

        if dependency_graph:
            # Execute in waves based on dependencies
            while True:
                # Get ready steps - convert UUID to string for comparison
                ready_step_ids_set = set(dependency_graph.get_ready_steps())
                ready_steps = [
                    step
                    for step in workflow_steps
                    if str(step.step_id) in ready_step_ids_set
                ]

                if not ready_steps:
                    break

                # Execute ready steps in parallel, processing in batches
                max_parallel = input_data.max_parallel_steps or len(ready_steps)

                # Process ready steps in batches
                for batch_start in range(0, len(ready_steps), max_parallel):
                    parallel_executions += 1
                    batch_end = min(batch_start + max_parallel, len(ready_steps))
                    batch_steps = ready_steps[batch_start:batch_end]

                    tasks = []
                    for step in batch_steps:
                        task = asyncio.create_task(
                            self._execute_single_step(step, input_data.workflow_id),
                        )
                        tasks.append((step, task))

                    # Wait for all tasks in batch to complete
                    for step, task in tasks:
                        try:
                            step_result = await task
                            step.state = EnumWorkflowState.COMPLETED
                            completed_step_ids.append(str(step.step_id))
                            all_results.extend(step_result)
                            dependency_graph.mark_completed(step.step_id)

                            # Collect actions
                            for action in step.thunks:
                                if self.action_emission_enabled:
                                    emitted_action = await self.emit_action(
                                        action.action_type,
                                        action.target_node_type,
                                        {
                                            **action.payload,
                                            "workflow_id": input_data.workflow_id,
                                        },
                                        action.dependencies,
                                        action.priority,
                                        action.timeout_ms,
                                        action.lease_id,
                                        action.epoch,
                                    )
                                    all_actions.append(emitted_action)

                        except Exception as e:
                            step.state = EnumWorkflowState.FAILED
                            step.error = e
                            failed_step_ids.append(str(step.step_id))

                            if input_data.failure_strategy == "fail_fast":
                                # Cancel remaining tasks
                                for _, remaining_task in tasks:
                                    if not remaining_task.done():
                                        remaining_task.cancel()
                                raise
        else:
            # Execute all steps in parallel, processing in batches
            max_parallel = input_data.max_parallel_steps or len(workflow_steps)

            # Process all steps in batches
            for batch_start in range(0, len(workflow_steps), max_parallel):
                parallel_executions += 1
                batch_end = min(batch_start + max_parallel, len(workflow_steps))
                batch_steps = workflow_steps[batch_start:batch_end]

                tasks = []
                for step in batch_steps:
                    task = asyncio.create_task(
                        self._execute_single_step(step, input_data.workflow_id),
                    )
                    tasks.append((step, task))

                for step, task in tasks:
                    try:
                        step_result = await task
                        step.state = EnumWorkflowState.COMPLETED
                        completed_step_ids.append(str(step.step_id))
                        all_results.extend(step_result)

                        # Collect actions from step thunks
                        for action in step.thunks:
                            if self.action_emission_enabled:
                                emitted_action = await self.emit_action(
                                    action.action_type,
                                    action.target_node_type,
                                    {
                                        **action.payload,
                                        "workflow_id": input_data.workflow_id,
                                    },
                                    action.dependencies,
                                    action.priority,
                                    action.timeout_ms,
                                    action.lease_id,
                                    action.epoch,
                                )
                                all_actions.append(emitted_action)
                    except Exception as e:
                        step.state = EnumWorkflowState.FAILED
                        step.error = e
                        failed_step_ids.append(str(step.step_id))

        end_time = datetime.now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return ModelOrchestratorOutput(
            execution_status="completed" if len(failed_step_ids) == 0 else "failed",
            execution_time_ms=execution_time_ms,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            completed_steps=completed_step_ids,
            failed_steps=failed_step_ids,
            final_result=all_results if all_results else None,
            actions_emitted=all_actions,
            parallel_executions=parallel_executions,
        )

    async def _execute_batch_workflow(
        self,
        input_data: ModelOrchestratorInput,
        dependency_graph: ModelDependencyGraph | None,
    ) -> ModelOrchestratorOutput:
        """Execute workflow with load balancing and batch processing."""
        load_balanced_operations = 0

        # Convert dict steps to ModelWorkflowStep
        workflow_steps = [
            self._dict_to_workflow_step(step_dict) for step_dict in input_data.steps
        ]

        # For batch processing, group similar operations
        step_groups = self._group_steps_by_type(workflow_steps)

        for _group_type, steps in step_groups.items():
            for step in steps:
                # Use load balancer for operation distribution
                operation_acquired = await self.load_balancer.acquire(step.step_id)
                if operation_acquired:
                    load_balanced_operations += 1
                    try:
                        # Execute step
                        await self._execute_single_step(step, input_data.workflow_id)
                    finally:
                        self.load_balancer.release(step.step_id)

        # Use sequential execution with load balancing metadata
        result = await self._execute_sequential_workflow(input_data, dependency_graph)
        result.metrics["load_balanced_operations"] = float(load_balanced_operations)
        result.metrics["execution_mode_batch"] = 1.0

        return result

    async def _execute_single_step(
        self,
        step: ModelWorkflowStepExecution,
        workflow_id: UUID,
    ) -> list[Any]:
        """Execute a single workflow step."""
        step.state = EnumWorkflowState.RUNNING
        step.started_at = datetime.now()

        results = []
        for action in step.thunks:
            # Simulate action execution
            result = {
                "action_id": str(action.action_id),
                "action_type": action.action_type.value,
                "target_node_type": action.target_node_type,
                "status": "executed",
                "execution_time": datetime.now().isoformat(),
            }
            results.append(result)

        step.results = results
        step.completed_at = datetime.now()

        return results

    async def _evaluate_condition(
        self,
        step: ModelWorkflowStepExecution,
        previous_results: list[Any],
    ) -> bool:
        """Evaluate step condition for branching."""
        if not step.condition:
            return True

        if step.condition == EnumBranchCondition.IF_TRUE:
            return True
        if step.condition == EnumBranchCondition.IF_FALSE:
            return False
        if step.condition == EnumBranchCondition.CUSTOM and step.condition_function:
            return bool(step.condition_function(step, previous_results))
        # Default to true for unhandled conditions
        return True

    def _get_topological_order(
        self, dependency_graph: ModelDependencyGraph
    ) -> list[str]:
        """Get topological ordering of steps based on dependencies."""
        # Kahn's algorithm
        in_degree = dependency_graph.in_degree.copy()
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in dependency_graph.edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _group_steps_by_type(
        self,
        steps: list[ModelWorkflowStepExecution],
    ) -> dict[str, list[ModelWorkflowStepExecution]]:
        """Group steps by their action types for batch processing."""
        groups: dict[str, list[ModelWorkflowStepExecution]] = {}
        for step in steps:
            # Group by first action type
            if step.thunks:
                group_key = step.thunks[0].action_type.value
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(step)

        return groups

    def _create_ticket_lifecycle_steps(
        self,
        ticket_id: UUID,
        current_state: str,
        target_state: str,
        dependencies: list[UUID],
    ) -> list[dict[str, Any]]:
        """Create workflow steps for RSD ticket lifecycle transition."""
        steps = []

        # Step 1: Validate current state
        validate_action_id = uuid4()
        validate_action = ModelAction(
            action_id=validate_action_id,
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeCompute",
            payload={
                "computation_type": "state_validation",
                "ticket_id": str(ticket_id),
                "current_state": current_state,
            },
            dependencies=[],
            priority=1,
            timeout_ms=5000,
            lease_id=uuid4(),
            epoch=0,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )

        validate_step = {
            "step_id": str(uuid4()),
            "step_name": "Validate Current State",
            "execution_mode": EnumExecutionMode.SEQUENTIAL,
            "actions": [validate_action.model_dump()],
        }
        steps.append(validate_step)

        # Step 2: Check dependencies
        dep_action_id = None
        if dependencies:
            dep_action_id = uuid4()
            dep_action = ModelAction(
                action_id=dep_action_id,
                action_type=EnumActionType.REDUCE,
                target_node_type="NodeReducer",
                payload={
                    "reduction_type": "dependency_check",
                    "ticket_id": str(ticket_id),
                    "dependencies": [str(dep) for dep in dependencies],
                },
                dependencies=[validate_action_id],
                priority=1,
                timeout_ms=10000,
                lease_id=uuid4(),
                epoch=0,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )

            dep_step = {
                "step_id": str(uuid4()),
                "step_name": "Check Dependencies",
                "execution_mode": EnumExecutionMode.SEQUENTIAL,
                "actions": [dep_action.model_dump()],
            }
            steps.append(dep_step)

        # Step 3: Execute state transition
        transition_deps = [validate_action_id]
        if dep_action_id:
            transition_deps.append(dep_action_id)

        transition_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeEffect",
            payload={
                "effect_type": "ticket_state_transition",
                "ticket_id": str(ticket_id),
                "from_state": current_state,
                "to_state": target_state,
            },
            dependencies=transition_deps,
            priority=2,
            timeout_ms=15000,
            lease_id=uuid4(),
            epoch=0,
            retry_count=1,
            metadata={},
            created_at=datetime.now(),
        )

        transition_step = {
            "step_id": str(uuid4()),
            "step_name": "Execute State Transition",
            "execution_mode": EnumExecutionMode.SEQUENTIAL,
            "actions": [transition_action.model_dump()],
        }
        steps.append(transition_step)

        return steps

    async def _update_orchestration_metrics(
        self,
        execution_mode: str,
        processing_time_ms: float,
        success: bool,
        steps_count: int,
    ) -> None:
        """Update orchestration-specific metrics."""
        if execution_mode not in self.orchestration_metrics:
            self.orchestration_metrics[execution_mode] = {
                "total_workflows": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "total_steps_processed": 0.0,
                "avg_processing_time_ms": 0.0,
                "avg_steps_per_workflow": 0.0,
                "min_processing_time_ms": float("inf"),
                "max_processing_time_ms": 0.0,
            }

        metrics = self.orchestration_metrics[execution_mode]
        metrics["total_workflows"] += 1
        metrics["total_steps_processed"] += steps_count

        if success:
            metrics["success_count"] += 1
        else:
            metrics["error_count"] += 1

        # Update timing metrics
        metrics["min_processing_time_ms"] = min(
            metrics["min_processing_time_ms"],
            processing_time_ms,
        )
        metrics["max_processing_time_ms"] = max(
            metrics["max_processing_time_ms"],
            processing_time_ms,
        )

        # Update rolling averages
        total_workflows = metrics["total_workflows"]
        current_avg_time = metrics["avg_processing_time_ms"]
        metrics["avg_processing_time_ms"] = (
            current_avg_time * (total_workflows - 1) + processing_time_ms
        ) / total_workflows

        metrics["avg_steps_per_workflow"] = (
            metrics["total_steps_processed"] / total_workflows
        )

    def _register_builtin_conditions(self) -> None:
        """Register built-in condition functions."""

        def always_true(step: ModelWorkflowStep, previous_results: list[Any]) -> bool:
            return True

        def always_false(step: ModelWorkflowStep, previous_results: list[Any]) -> bool:
            return False

        def has_previous_results(
            step: ModelWorkflowStep,
            previous_results: list[Any],
        ) -> bool:
            return len(previous_results) > 0

        def previous_step_success(
            step: ModelWorkflowStep,
            previous_results: list[Any],
        ) -> bool:
            if not previous_results:
                return True
            last_result = previous_results[-1]
            return (
                isinstance(last_result, dict)
                and last_result.get("status") == "executed"
            )

        # Register conditions
        self.condition_functions["always_true"] = always_true
        self.condition_functions["always_false"] = always_false
        self.condition_functions["has_previous_results"] = has_previous_results
        self.condition_functions["previous_step_success"] = previous_step_success
