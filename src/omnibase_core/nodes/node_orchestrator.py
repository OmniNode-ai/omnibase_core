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

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.enum_orchestrator_types import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumThunkType,
    EnumWorkflowState,
)
from omnibase_core.nodes.model_dependency_graph import ModelDependencyGraph
from omnibase_core.nodes.model_load_balancer import ModelLoadBalancer
from omnibase_core.nodes.model_orchestrator_input import ModelOrchestratorInput
from omnibase_core.nodes.model_orchestrator_output import ModelOrchestratorOutput
from omnibase_core.nodes.model_thunk import ModelThunk
from omnibase_core.nodes.model_workflow_step import ModelWorkflowStep


class NodeOrchestrator(NodeCoreBase):
    """
    STABLE INTERFACE v1.0.0 - DO NOT CHANGE without major version bump.

    Workflow coordination node for control flow management.

    Implements workflow coordination with thunk emission for deferred execution,
    conditional branching, and parallel coordination. Optimized for RSD workflow
    management including ticket lifecycle transitions and dependency-aware ordering.

    Key Features:
    - Thunk emission patterns for deferred execution
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

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize NodeOrchestrator with ModelONEXContainer dependency injection.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Orchestrator-specific configuration
        self.max_concurrent_workflows = 5
        self.default_step_timeout_ms = 30000
        self.thunk_emission_enabled = True

        # Active workflows tracking (UUID keys for workflow_id)
        self.active_workflows: dict[UUID, ModelOrchestratorInput] = {}
        self.workflow_states: dict[UUID, EnumWorkflowState] = {}

        # Load balancer for operation distribution
        self.load_balancer = ModelLoadBalancer(max_concurrent_operations=20)

        # Thunk emission registry (UUID keys for workflow_id)
        self.emitted_thunks: dict[UUID, list[ModelThunk]] = {}

        # Workflow execution semaphore
        self.workflow_semaphore = asyncio.Semaphore(self.max_concurrent_workflows)

        # Performance tracking
        self.orchestration_metrics: dict[str, dict[str, float]] = {}

        # Conditional functions registry
        self.condition_functions: dict[str, Callable[..., Any]] = {}

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
                        "steps_completed": result.steps_completed,
                        "thunks_emitted": len(result.thunks_emitted),
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
            "workflow_id": str(result.workflow_id),
            "state_transition": f"{current_state} -> {target_state}",
            "steps_completed": result.steps_completed,
            "processing_time_ms": result.processing_time_ms,
            "thunks_emitted": len(result.thunks_emitted),
            "success": result.workflow_state == EnumWorkflowState.COMPLETED,
        }

    async def emit_thunk(
        self,
        thunk_type: EnumThunkType,
        target_node_type: str,
        operation_data: dict[str, Any],
        dependencies: list[UUID] | None = None,
        priority: int = 1,
        timeout_ms: int = 30000,
    ) -> ModelThunk:
        """
        Emit thunk for deferred execution.

        Args:
            thunk_type: Type of thunk to emit
            target_node_type: Target node type for execution
            operation_data: Data for the operation
            dependencies: List of dependency thunk IDs (UUIDs)
            priority: Execution priority (higher = more urgent)
            timeout_ms: Execution timeout in milliseconds

        Returns:
            Created thunk instance
        """
        thunk = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=thunk_type,
            target_node_type=target_node_type,
            operation_data=operation_data,
            dependencies=dependencies or [],
            priority=priority,
            timeout_ms=timeout_ms,
            retry_count=0,
            metadata={
                "emitted_by": str(self.node_id),
                "emission_time": datetime.now().isoformat(),
            },
            created_at=datetime.now(),
        )

        # Store emitted thunk (workflow_id should be UUID from operation_data)
        workflow_id_value = operation_data.get("workflow_id")
        if workflow_id_value is not None:
            # Ensure workflow_id is UUID type
            if isinstance(workflow_id_value, str):
                workflow_id = UUID(workflow_id_value)
            else:
                workflow_id = workflow_id_value

            if workflow_id not in self.emitted_thunks:
                self.emitted_thunks[workflow_id] = []
            self.emitted_thunks[workflow_id].append(thunk)

        emit_log_event(
            LogLevel.INFO,
            f"Thunk emitted: {thunk_type.value} -> {target_node_type}",
            {
                "node_id": str(self.node_id),
                "thunk_id": str(thunk.thunk_id),
                "thunk_type": thunk_type.value,
                "target_node_type": target_node_type,
                "priority": priority,
                "dependencies": len(dependencies or []),
            },
        )

        return thunk

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
                "total_thunks_emitted": float(
                    sum(len(thunks) for thunks in self.emitted_thunks.values()),
                ),
                "condition_functions_registered": float(len(self.condition_functions)),
            },
        }

    async def _initialize_node_resources(self) -> None:
        """Initialize orchestrator-specific resources."""
        emit_log_event(
            LogLevel.INFO,
            "NodeOrchestrator resources initialized",
            {
                "node_id": str(self.node_id),
                "max_concurrent_workflows": self.max_concurrent_workflows,
                "thunk_emission_enabled": self.thunk_emission_enabled,
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
        self.emitted_thunks.clear()

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

        # Add dependencies based on thunk dependencies
        for step in workflow_steps:
            for thunk in step.thunks:
                for dep_id in thunk.dependencies:
                    # Find step containing dependency thunk
                    for other_step in workflow_steps:
                        if any(t.thunk_id == dep_id for t in other_step.thunks):
                            graph.add_dependency(other_step.step_id, step.step_id)
                            break

        return graph

    def _dict_to_workflow_step(self, step_dict: dict[str, Any]) -> ModelWorkflowStep:
        """Convert dictionary to ModelWorkflowStep."""
        # Handle step_id - convert to UUID if string
        step_id_value = step_dict.get("step_id")
        if step_id_value is None:
            step_id = uuid4()
        elif isinstance(step_id_value, str):
            step_id = UUID(step_id_value)
        else:
            step_id = step_id_value

        return ModelWorkflowStep(
            step_id=step_id,
            step_name=step_dict.get("step_name", "Unnamed Step"),
            execution_mode=step_dict.get(
                "execution_mode", EnumExecutionMode.SEQUENTIAL
            ),
            thunks=[
                ModelThunk(**thunk_dict) for thunk_dict in step_dict.get("thunks", [])
            ],
            condition=step_dict.get("condition"),
            timeout_ms=step_dict.get("timeout_ms", 30000),
            retry_count=step_dict.get("retry_count", 0),
            metadata=step_dict.get("metadata", {}),
        )

    async def _execute_sequential_workflow(
        self,
        input_data: ModelOrchestratorInput,
        dependency_graph: ModelDependencyGraph | None,
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps sequentially."""
        steps_completed = 0
        steps_failed = 0
        all_thunks = []
        all_results: list[Any] = []

        # Convert dict steps to ModelWorkflowStep
        workflow_steps = [
            self._dict_to_workflow_step(step_dict) for step_dict in input_data.steps
        ]

        # Determine execution order
        if dependency_graph:
            execution_order = self._get_topological_order(dependency_graph)
            ordered_steps = [
                next(s for s in workflow_steps if s.step_id == step_id)
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

                # Execute step thunks
                step_results = []
                for thunk in step.thunks:
                    if self.thunk_emission_enabled:
                        emitted_thunk = await self.emit_thunk(
                            thunk.thunk_type,
                            thunk.target_node_type,
                            {
                                **thunk.operation_data,
                                "workflow_id": input_data.workflow_id,
                            },
                            thunk.dependencies,
                            thunk.priority,
                            thunk.timeout_ms,
                        )
                        all_thunks.append(emitted_thunk)

                    # Simulate thunk execution result
                    step_results.append(
                        {"thunk_id": str(thunk.thunk_id), "status": "executed"},
                    )

                step.results = step_results
                step.state = EnumWorkflowState.COMPLETED
                step.completed_at = datetime.now()
                steps_completed += 1
                all_results.extend(step_results)

                # Update dependency graph
                if dependency_graph:
                    dependency_graph.mark_completed(step.step_id)

            except Exception as e:
                step.state = EnumWorkflowState.FAILED
                step.error = e
                steps_failed += 1

                if input_data.failure_strategy == "fail_fast":
                    raise
                # Continue for other failure strategies

        return ModelOrchestratorOutput(
            workflow_id=input_data.workflow_id,
            operation_id=input_data.operation_id,
            workflow_state=(
                EnumWorkflowState.COMPLETED
                if steps_failed == 0
                else EnumWorkflowState.FAILED
            ),
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            thunks_emitted=all_thunks,
            processing_time_ms=(time.time() * 1000)
            - (input_data.timestamp.timestamp() * 1000),
            results=all_results,
            metadata={"execution_mode": "sequential"},
        )

    async def _execute_parallel_workflow(
        self,
        input_data: ModelOrchestratorInput,
        dependency_graph: ModelDependencyGraph | None,
    ) -> ModelOrchestratorOutput:
        """Execute workflow steps in parallel respecting dependencies."""
        steps_completed = 0
        steps_failed = 0
        all_thunks = []
        all_results = []
        parallel_executions = 0

        # Convert dict steps to ModelWorkflowStep
        workflow_steps = [
            self._dict_to_workflow_step(step_dict) for step_dict in input_data.steps
        ]

        if dependency_graph:
            # Execute in waves based on dependencies
            while True:
                ready_steps = [
                    step
                    for step in workflow_steps
                    if step.step_id in dependency_graph.get_ready_steps()
                ]

                if not ready_steps:
                    break

                # Execute ready steps in parallel
                parallel_executions += 1
                tasks = []
                for step in ready_steps[: input_data.max_parallel_steps]:
                    task = asyncio.create_task(
                        self._execute_single_step(step, input_data.workflow_id),
                    )
                    tasks.append((step, task))

                # Wait for all tasks to complete
                for step, task in tasks:
                    try:
                        step_result = await task
                        step.state = EnumWorkflowState.COMPLETED
                        steps_completed += 1
                        all_results.extend(step_result)
                        dependency_graph.mark_completed(step.step_id)

                        # Collect thunks
                        for thunk in step.thunks:
                            if self.thunk_emission_enabled:
                                emitted_thunk = await self.emit_thunk(
                                    thunk.thunk_type,
                                    thunk.target_node_type,
                                    {
                                        **thunk.operation_data,
                                        "workflow_id": input_data.workflow_id,
                                    },
                                    thunk.dependencies,
                                    thunk.priority,
                                    thunk.timeout_ms,
                                )
                                all_thunks.append(emitted_thunk)

                    except Exception as e:
                        step.state = EnumWorkflowState.FAILED
                        step.error = e
                        steps_failed += 1

                        if input_data.failure_strategy == "fail_fast":
                            # Cancel remaining tasks
                            for _, remaining_task in tasks:
                                if not remaining_task.done():
                                    remaining_task.cancel()
                            raise
        else:
            # Execute all steps in parallel
            parallel_executions = 1
            tasks = []
            for step in workflow_steps[: input_data.max_parallel_steps]:
                task = asyncio.create_task(
                    self._execute_single_step(step, input_data.workflow_id),
                )
                tasks.append((step, task))

            for step, task in tasks:
                try:
                    step_result = await task
                    step.state = EnumWorkflowState.COMPLETED
                    steps_completed += 1
                    all_results.extend(step_result)
                except Exception as e:
                    step.state = EnumWorkflowState.FAILED
                    step.error = e
                    steps_failed += 1

        return ModelOrchestratorOutput(
            workflow_id=input_data.workflow_id,
            operation_id=input_data.operation_id,
            workflow_state=(
                EnumWorkflowState.COMPLETED
                if steps_failed == 0
                else EnumWorkflowState.FAILED
            ),
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            thunks_emitted=all_thunks,
            processing_time_ms=(time.time() * 1000)
            - (input_data.timestamp.timestamp() * 1000),
            parallel_executions=parallel_executions,
            results=all_results,
            metadata={"execution_mode": "parallel"},
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
        result.load_balanced_operations = load_balanced_operations
        result.metadata["execution_mode"] = "batch"

        return result

    async def _execute_single_step(
        self,
        step: ModelWorkflowStep,
        workflow_id: UUID,
    ) -> list[Any]:
        """Execute a single workflow step."""
        step.state = EnumWorkflowState.RUNNING
        step.started_at = datetime.now()

        results = []
        for thunk in step.thunks:
            # Simulate thunk execution
            result = {
                "thunk_id": str(thunk.thunk_id),
                "thunk_type": thunk.thunk_type.value,
                "target_node_type": thunk.target_node_type,
                "status": "executed",
                "execution_time": datetime.now().isoformat(),
            }
            results.append(result)

        step.results = results
        step.completed_at = datetime.now()

        return results

    async def _evaluate_condition(
        self,
        step: ModelWorkflowStep,
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
    ) -> list[UUID]:
        """Get topological ordering of steps based on dependencies."""
        # Kahn's algorithm
        in_degree = dependency_graph.in_degree.copy()
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result: list[UUID] = []

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
        steps: list[ModelWorkflowStep],
    ) -> dict[str, list[ModelWorkflowStep]]:
        """Group steps by their thunk types for batch processing."""
        groups: dict[str, list[ModelWorkflowStep]] = {}
        for step in steps:
            # Group by first thunk type
            if step.thunks:
                group_key = step.thunks[0].thunk_type.value
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
        validate_thunk_id = uuid4()
        validate_thunk = ModelThunk(
            thunk_id=validate_thunk_id,
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={
                "computation_type": "state_validation",
                "ticket_id": str(ticket_id),
                "current_state": current_state,
            },
            dependencies=[],
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )

        validate_step = {
            "step_id": str(uuid4()),
            "step_name": "Validate Current State",
            "execution_mode": EnumExecutionMode.SEQUENTIAL,
            "thunks": [validate_thunk.model_dump()],
        }
        steps.append(validate_step)

        # Step 2: Check dependencies
        dep_thunk_id = None
        if dependencies:
            dep_thunk_id = uuid4()
            dep_thunk = ModelThunk(
                thunk_id=dep_thunk_id,
                thunk_type=EnumThunkType.REDUCE,
                target_node_type="NodeReducer",
                operation_data={
                    "reduction_type": "dependency_check",
                    "ticket_id": str(ticket_id),
                    "dependencies": [str(dep) for dep in dependencies],
                },
                dependencies=[validate_thunk_id],
                priority=1,
                timeout_ms=10000,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )

            dep_step = {
                "step_id": str(uuid4()),
                "step_name": "Check Dependencies",
                "execution_mode": EnumExecutionMode.SEQUENTIAL,
                "thunks": [dep_thunk.model_dump()],
            }
            steps.append(dep_step)

        # Step 3: Execute state transition
        transition_deps = [validate_thunk_id]
        if dep_thunk_id:
            transition_deps.append(dep_thunk_id)

        transition_thunk = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.EFFECT,
            target_node_type="NodeEffect",
            operation_data={
                "effect_type": "ticket_state_transition",
                "ticket_id": str(ticket_id),
                "from_state": current_state,
                "to_state": target_state,
            },
            dependencies=transition_deps,
            priority=2,
            timeout_ms=15000,
            retry_count=1,
            metadata={},
            created_at=datetime.now(),
        )

        transition_step = {
            "step_id": str(uuid4()),
            "step_name": "Execute State Transition",
            "execution_mode": EnumExecutionMode.SEQUENTIAL,
            "thunks": [transition_thunk.model_dump()],
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
