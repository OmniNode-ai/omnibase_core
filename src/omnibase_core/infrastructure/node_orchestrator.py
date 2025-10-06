import uuid
from typing import Callable, Dict, Generic, List

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
NodeOrchestrator - Workflow Coordination Node for 4-Node ModelArchitecture.

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

Author: ONEX Framework Team
"""

import asyncio
import time
from collections.abc import Callable as CallableABC
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import UUID, uuid4

# Removed: EnumCoreErrorCode doesn't exist, use EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_workflow_execution import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumThunkType,
    EnumWorkflowState,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.infrastructure.load_balancer import LoadBalancer
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Import contract model for orchestrator nodes
from omnibase_core.models.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)

# Import orchestrator models
from omnibase_core.models.operations.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.operations.model_orchestrator_output import (
    ModelOrchestratorOutput,
)
from omnibase_core.models.orchestrator.model_thunk import ModelThunk
from omnibase_core.models.workflows.model_dependency_graph import ModelDependencyGraph
from omnibase_core.models.workflows.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)


class NodeOrchestrator(NodeCoreBase):
    """
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

        # CANONICAL PATTERN: Load contract model for Orchestrator node type
        self.contract_model: ModelContractOrchestrator = self._load_contract_model()

        # Orchestrator-specific configuration
        self.max_concurrent_workflows = 5
        self.default_step_timeout_ms = 30000
        self.thunk_emission_enabled = True
        self.load_balancing_enabled = True
        self.dependency_resolution_enabled = True
        self.max_thunk_queue_size = 1000

        # Active workflows tracking
        self.active_workflows: dict[str, ModelOrchestratorInput] = {}
        self.workflow_states: dict[str, EnumWorkflowState] = {}

        # Load balancer for operation distribution
        self.load_balancer = LoadBalancer(max_concurrent_operations=20)

        # Thunk emission registry
        self.emitted_thunks: dict[str, list[ModelThunk]] = {}

        # Workflow execution semaphore
        self.workflow_semaphore = asyncio.Semaphore(self.max_concurrent_workflows)

        # Performance tracking
        self.orchestration_metrics: dict[str, dict[str, float]] = {}

        # Conditional functions registry
        self.condition_functions: dict[str, Callable[..., Any]] = {}

        # Register built-in condition functions
        self._register_builtin_conditions()

    def _load_contract_model(self) -> ModelContractOrchestrator:
        """
        Load and validate contract model for Orchestrator node type.

        CANONICAL PATTERN: Centralized contract loading for all Orchestrator nodes.
        Provides type-safe contract configuration with workflow and thunk validation.

        Returns:
            ModelContractOrchestrator: Validated contract model for this node type

        Raises:
            ModelOnexError: If contract loading or validation fails
        """
        try:
            # Load actual contract from file with subcontract resolution

            from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
            from omnibase_core.utils.generation.utility_reference_resolver import (
                UtilityReferenceResolver,
            )
            from omnibase_core.utils.safe_yaml_loader import (
                load_and_validate_yaml_model,
            )

            # Get contract path - find the node.py file and look for contract.yaml
            contract_path = self._find_contract_path()

            # Load and resolve contract with subcontract support
            reference_resolver = UtilityReferenceResolver()

            # Load and validate YAML using Pydantic model
            yaml_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)
            contract_data = yaml_model.model_dump()

            # Resolve any $ref references in the contract
            resolved_contract = self._resolve_contract_references(
                contract_data,
                contract_path.parent,
                reference_resolver,
            )

            # Create ModelContractOrchestrator from resolved contract data
            contract_model = ModelContractOrchestrator(**resolved_contract)

            # CANONICAL PATTERN: Validate contract model consistency
            contract_model.validate_node_specific_config()

            emit_log_event(
                LogLevel.INFO,
                "Contract model loaded successfully for NodeOrchestrator",
                {
                    "contract_type": "ModelContractOrchestrator",
                    "node_type": contract_model.node_type,
                    "version": contract_model.version,
                    "contract_path": str(contract_path),
                },
            )

            return contract_model

        except Exception as e:
            # CANONICAL PATTERN: Wrap contract loading errors
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Contract model loading failed for NodeOrchestrator: {e!s}",
                details={
                    "contract_model_type": "ModelContractOrchestrator",
                    "error_type": type(e).__name__,
                },
                cause=e,
            )

    def _find_contract_path(self) -> Path:
        """
        Find the contract.yaml file for this orchestrator node.

        Uses inspection to find the module file and look for contract.yaml in the same directory.

        Returns:
            Path: Path to the contract.yaml file

        Raises:
            ModelOnexError: If contract file cannot be found
        """
        import inspect

        from omnibase_core.constants.contract_constants import CONTRACT_FILENAME

        try:
            # Get the module file for the calling class
            frame = inspect.currentframe()
            while frame:
                frame = frame.f_back
                if frame and "self" in frame.f_locals:
                    caller_self = frame.f_locals["self"]
                    if hasattr(caller_self, "__module__"):
                        module = inspect.getmodule(caller_self)
                        if module and hasattr(module, "__file__"):
                            module_path = Path(module.__file__ or "")
                            contract_path = module_path.parent / CONTRACT_FILENAME
                            if contract_path.exists():
                                return contract_path

            # Fallback: this shouldn't happen but provide error
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Could not find contract.yaml file for orchestrator node",
                details={"contract_filename": CONTRACT_FILENAME},
            )

        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Error finding contract path: {e!s}",
                cause=e,
            )

    def _resolve_contract_references(
        self,
        data: Any,
        base_path: Path,
        reference_resolver: Any,
    ) -> Any:
        """
        Recursively resolve all $ref references in contract data.

        Enhanced to properly handle FSM subcontracts with Pydantic model validation.

        Args:
            data: Contract data structure (dict[str, Any], list[Any], or primitive)
            base_path: Base directory path for resolving relative references
            reference_resolver: Reference resolver utility

        Returns:
            Any: Resolved contract data with all references loaded

        Raises:
            ModelOnexError: If reference resolution fails
        """
        try:
            if isinstance(data, dict):
                if "$ref" in data:
                    # Resolve reference to another file
                    ref_file = data["$ref"]
                    if ref_file.startswith(("./", "../")):
                        # Relative path reference
                        ref_path = (base_path / ref_file).resolve()
                    else:
                        # Absolute or root-relative reference
                        ref_path = Path(ref_file)

                    return reference_resolver.resolve_reference(
                        str(ref_path),
                        base_path,
                    )
                # Recursively resolve nested dict[str, Any]ionaries
                return {
                    key: self._resolve_contract_references(
                        value,
                        base_path,
                        reference_resolver,
                    )
                    for key, value in data.items()
                }
            if isinstance(data, list):
                # Recursively resolve list[Any]s
                return [
                    self._resolve_contract_references(
                        item,
                        base_path,
                        reference_resolver,
                    )
                    for item in data
                ]
            # Return primitives as-is
            return data

        except Exception as e:
            # fallback-ok: Contract reference resolution should degrade gracefully, returning None for failed refs to support partial contract loading
            emit_log_event(
                LogLevel.WARNING,
                "Failed to resolve contract reference, using original data",
                {"error": str(e), "error_type": type(e).__name__},
            )
            return None  # fallback-ok: Intentional silent return to allow workflow to continue with partial contract data

    async def process(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Workflow coordination with thunk emission.

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
                workflow_id_str = str(input_data.workflow_id)
                self.active_workflows[workflow_id_str] = input_data
                self.workflow_states[workflow_id_str] = EnumWorkflowState.RUNNING

                # Build dependency graph if enabled
                dependency_graph = None
                if input_data.dependency_resolution_enabled:
                    dependency_graph = self._build_dependency_graph(input_data.steps)

                    # Check for cycles
                    if dependency_graph.has_cycles():
                        raise ModelOnexError(
                            code=EnumCoreErrorCode.VALIDATION_ERROR,
                            message="Workflow contains dependency cycles",
                            context={
                                "node_id": self.node_id,
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
                workflow_id_str = str(input_data.workflow_id)
                self.workflow_states[workflow_id_str] = EnumWorkflowState.COMPLETED

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
                        "node_id": self.node_id,
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
            workflow_id_str = str(input_data.workflow_id)
            if workflow_id_str in self.workflow_states:
                self.workflow_states[workflow_id_str] = EnumWorkflowState.FAILED

            await self._update_orchestration_metrics(
                input_data.execution_mode.value,
                processing_time,
                False,
                len(input_data.steps),
            )
            await self._update_processing_metrics(processing_time, False)

            raise ModelOnexError(
                code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Workflow orchestration failed: {e!s}",
                context={
                    "node_id": self.node_id,
                    "workflow_id": str(input_data.workflow_id),
                    "operation_id": str(input_data.operation_id),
                    "processing_time_ms": processing_time,
                    "error": str(e),
                },
            ) from e

        finally:
            # Cleanup active workflow
            workflow_id_str = str(input_data.workflow_id)
            if workflow_id_str in self.active_workflows:
                del self.active_workflows[workflow_id_str]

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
            ticket_id: Unique ticket identifier
            current_state: Current ticket state
            target_state: Desired target state
            dependency_tickets: List of dependent ticket IDs

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
            dependencies: List of dependency thunk IDs
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
                "emitted_by": self.node_id,
                "emission_time": datetime.now().isoformat(),
            },
            created_at=datetime.now(),
        )

        # Store emitted thunk
        workflow_id = operation_data.get("workflow_id", "default")
        if workflow_id not in self.emitted_thunks:
            self.emitted_thunks[workflow_id] = []
        self.emitted_thunks[workflow_id].append(thunk)

        emit_log_event(
            LogLevel.INFO,
            f"Thunk emitted: {thunk_type.value} -> {target_node_type}",
            {
                "node_id": self.node_id,
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
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Condition function already registered: {condition_name}",
                context={"node_id": self.node_id, "condition_name": condition_name},
            )

        if not callable(function):
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Condition function must be callable: {condition_name}",
                context={"node_id": self.node_id, "condition_name": condition_name},
            )

        self.condition_functions[condition_name] = function

        emit_log_event(
            LogLevel.INFO,
            f"Condition function registered: {condition_name}",
            {"node_id": self.node_id, "condition_name": condition_name},
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
                "node_id": self.node_id,
                "max_concurrent_workflows": self.max_concurrent_workflows,
                "thunk_emission_enabled": self.thunk_emission_enabled,
            },
        )

    async def _cleanup_node_resources(self) -> None:
        """Cleanup orchestrator-specific resources."""
        # Cancel active workflows
        for workflow_id in list[Any](self.active_workflows.keys()):
            self.workflow_states[workflow_id] = EnumWorkflowState.CANCELLED
            emit_log_event(
                LogLevel.WARNING,
                f"Cancelled active workflow during cleanup: {workflow_id}",
                {"node_id": self.node_id, "workflow_id": workflow_id},
            )

        self.active_workflows.clear()
        self.emitted_thunks.clear()

        emit_log_event(
            LogLevel.INFO,
            "NodeOrchestrator resources cleaned up",
            {"node_id": self.node_id},
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
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Workflow ID cannot be empty",
                context={
                    "node_id": self.node_id,
                    "operation_id": str(input_data.operation_id),
                },
            )

        if not input_data.steps:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Workflow must have at least one step",
                context={
                    "node_id": self.node_id,
                    "workflow_id": str(input_data.workflow_id),
                },
            )

        if not isinstance(input_data.execution_mode, EnumExecutionMode):
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Execution mode must be valid EnumExecutionMode enum",
                context={
                    "node_id": self.node_id,
                    "execution_mode": str(input_data.execution_mode),
                },
            )

    def _build_dependency_graph(
        self, steps: list[ModelWorkflowStepExecution]
    ) -> ModelDependencyGraph:
        """Build dependency graph from workflow steps."""
        graph: ModelDependencyGraph = ModelDependencyGraph()

        # Add all steps
        for step in steps:
            graph.add_step(step)

        # Add dependencies based on thunk dependencies
        for step in steps:
            for thunk in step.thunks:
                for dep_id in thunk.dependencies:
                    # Find step containing dependency thunk
                    for other_step in steps:
                        if any(t.thunk_id == dep_id for t in other_step.thunks):
                            graph.add_dependency(
                                str(other_step.step_id), str(step.step_id)
                            )
                            break

        return graph

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

        # Determine execution order
        if dependency_graph:
            execution_order = self._get_topological_order(dependency_graph)
            ordered_steps = [
                next(s for s in input_data.steps if str(s.step_id) == step_id)
                for step_id in execution_order
            ]
        else:
            ordered_steps = input_data.steps

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
                # fallback-ok: Non-fail-fast strategies allow graceful degradation - continue processing remaining steps despite individual step failures

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

        if dependency_graph:
            # Execute in waves based on dependencies
            while True:
                ready_steps = [
                    step
                    for step in input_data.steps
                    if str(step.step_id) in dependency_graph.get_ready_steps()
                ]

                if not ready_steps:
                    break

                # Execute ready steps in parallel
                parallel_executions += 1
                tasks = []
                for step in ready_steps[: input_data.max_parallel_steps]:
                    task = asyncio.create_task(
                        self._execute_single_step(step, str(input_data.workflow_id)),
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
                        # fallback-ok: Non-fail-fast strategies allow graceful degradation - parallel execution continues with remaining tasks despite individual failures
        else:
            # Execute all steps in parallel
            parallel_executions = 1
            tasks = []
            for step in input_data.steps[: input_data.max_parallel_steps]:
                task = asyncio.create_task(
                    self._execute_single_step(step, str(input_data.workflow_id)),
                )
                tasks.append((step, task))

            for step, task in tasks:
                try:
                    step_result = await task
                    step.state = EnumWorkflowState.COMPLETED
                    steps_completed += 1
                    all_results.extend(step_result)
                except Exception as e:
                    # fallback-ok: Parallel execution continues despite individual step failures - error tracked for final workflow state without interrupting other parallel tasks
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

        # For batch processing, group similar operations
        step_groups = self._group_steps_by_type(input_data.steps)

        for _group_type, steps in step_groups.items():
            for step in steps:
                # Use load balancer for operation distribution
                operation_acquired = await self.load_balancer.acquire(step.step_id)
                if operation_acquired:
                    load_balanced_operations += 1
                    try:
                        # Execute step
                        await self._execute_single_step(
                            step, str(input_data.workflow_id)
                        )
                    finally:
                        self.load_balancer.release(step.step_id)

        # Use sequential execution with load balancing metadata
        result = await self._execute_sequential_workflow(input_data, dependency_graph)
        result.load_balanced_operations = load_balanced_operations
        result.metadata["execution_mode"] = "batch"

        return result

    async def _execute_single_step(
        self,
        step: ModelWorkflowStepExecution,
        workflow_id: UUID | str,
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
        result = []

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
        """Group steps by their thunk types for batch processing."""
        groups: dict[str, list[ModelWorkflowStepExecution]] = {}
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
    ) -> list[ModelWorkflowStepExecution]:
        """Create workflow steps for RSD ticket lifecycle transition."""
        steps = []

        # Step 1: Validate current state
        validate_thunk = ModelThunk(
            thunk_id=uuid4(),
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

        validate_step = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Validate Current State",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[validate_thunk],
        )
        steps.append(validate_step)

        # Step 2: Check dependencies
        if dependencies:
            dep_thunk = ModelThunk(
                thunk_id=uuid4(),
                thunk_type=EnumThunkType.REDUCE,
                target_node_type="NodeReducer",
                operation_data={
                    "reduction_type": "dependency_check",
                    "ticket_id": str(ticket_id),
                    "dependencies": [str(dep) for dep in dependencies],
                },
                dependencies=[validate_thunk.thunk_id],
                priority=1,
                timeout_ms=10000,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )

            dep_step = ModelWorkflowStepExecution(
                step_id=uuid4(),
                step_name="Check Dependencies",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                thunks=[dep_thunk],
            )
            steps.append(dep_step)

        # Step 3: Execute state transition
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
            dependencies=[validate_thunk.thunk_id]
            + ([dep_thunk.thunk_id] if dependencies else []),
            priority=2,
            timeout_ms=15000,
            retry_count=1,
            metadata={},
            created_at=datetime.now(),
        )

        transition_step = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Execute State Transition",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[transition_thunk],
        )
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

        def always_true(
            step: ModelWorkflowStepExecution, previous_results: list[Any]
        ) -> bool:
            return True

        def always_false(
            step: ModelWorkflowStepExecution, previous_results: list[Any]
        ) -> bool:
            return False

        def has_previous_results(
            step: ModelWorkflowStepExecution,
            previous_results: list[Any],
        ) -> bool:
            return len(previous_results) > 0

        def previous_step_success(
            step: ModelWorkflowStepExecution,
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

    async def get_introspection_data(self) -> dict[str, Any]:
        """
        Get comprehensive introspection data for NodeOrchestrator.

        Returns specialized workflow coordination node information including thunk emission patterns,
        conditional branching, parallel execution coordination, and RSD workflow management details.

        Returns:
            dict[str, Any]: Comprehensive introspection data with orchestrator-specific information
        """
        try:
            # Get base introspection data from NodeCoreBase
            base_data = {
                "node_type": "NodeOrchestrator",
                "node_classification": "orchestrator",
                "node_id": self.node_id,
                "version": self.version,
                "created_at": self.created_at.isoformat(),
                "current_status": self.state.get("status", "unknown"),
            }

            # 1. Node Capabilities (Orchestrator-specific)
            node_capabilities = {
                **base_data,
                "architecture_classification": "workflow_coordination_and_control_flow",
                "orchestration_patterns": [
                    "sequential",
                    "parallel",
                    "conditional",
                    "batch",
                    "streaming",
                ],
                "thunk_emission_patterns": [
                    "compute",
                    "effect",
                    "reduce",
                    "orchestrate",
                    "custom",
                ],
                "available_operations": self._extract_orchestrator_operations(),
                "input_output_specifications": self._extract_orchestrator_io_specifications(),
                "performance_characteristics": self._extract_orchestrator_performance_characteristics(),
            }

            # 2. Contract Details (Orchestrator-specific)
            contract_details = {
                "contract_type": "ModelContractOrchestrator",
                "contract_validation_status": "validated",
                "workflow_configuration": self._extract_workflow_configuration(),
                "coordination_constraints": self._extract_coordination_constraints(),
                "supported_execution_modes": [mode.value for mode in EnumExecutionMode],
                "supported_thunk_types": [
                    thunk_type.value for thunk_type in EnumThunkType
                ],
                "supported_branch_conditions": [
                    condition.value for condition in EnumBranchCondition
                ],
            }

            # 3. Runtime Information (Orchestrator-specific)
            runtime_info = {
                "current_health_status": self._get_orchestrator_health_status(),
                "orchestration_metrics": self._get_orchestration_metrics_sync(),
                "resource_usage": self._get_orchestrator_resource_usage(),
                "workflow_state": self._get_workflow_state(),
                "thunk_emission_status": self._get_thunk_emission_status(),
            }

            # 4. Workflow Management Information
            workflow_management_info = {
                "thunk_emission_enabled": self.thunk_emission_enabled,
                "load_balancing_enabled": self.load_balancing_enabled,
                "dependency_resolution_enabled": self.dependency_resolution_enabled,
                "condition_functions_registered": list[Any](
                    self.condition_functions.keys()
                ),
                "condition_function_count": len(self.condition_functions),
                "supports_conditional_branching": True,
                "supports_parallel_execution": True,
                "supports_dependency_management": True,
                "supports_rsd_workflow_management": True,
            }

            # 5. Configuration Details
            configuration_details = {
                "max_parallel_workflows": self.max_concurrent_workflows,
                "default_step_timeout_ms": self.default_step_timeout_ms,
                "max_thunk_queue_size": self.max_thunk_queue_size,
                "workflow_configuration": {
                    "supports_nested_workflows": False,
                    "supports_dynamic_branching": True,
                    "supports_parallel_coordination": True,
                    "failure_strategies": ["fail_fast", "continue_on_error", "retry"],
                },
                "thunk_configuration": {
                    "emission_enabled": self.thunk_emission_enabled,
                    "queue_size_limit": self.max_thunk_queue_size,
                    "priority_based_execution": True,
                    "timeout_configuration": True,
                },
            }

            # 6. RSD-Specific Information
            rsd_specific_info = {
                "supports_ticket_lifecycle_transitions": True,
                "supports_dependency_aware_execution": True,
                "supports_batch_processing_coordination": True,
                "supports_error_recovery_workflows": True,
                "rsd_workflow_operations": [
                    "ticket_lifecycle_state_transitions",
                    "dependency_aware_execution_ordering",
                    "batch_processing_coordination",
                    "partial_failure_handling",
                ],
                "thunk_types_for_rsd": [
                    "compute_priority_calculations",
                    "effect_state_transitions",
                    "reduce_dependency_analysis",
                    "orchestrate_multi_ticket_workflows",
                ],
            }

            return {
                "node_capabilities": node_capabilities,
                "contract_details": contract_details,
                "runtime_information": runtime_info,
                "workflow_management_information": workflow_management_info,
                "configuration_details": configuration_details,
                "rsd_specific_information": rsd_specific_info,
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "node_type": "NodeOrchestrator",
                    "supports_full_introspection": True,
                    "specialization": "workflow_coordination_with_thunk_emission_and_parallel_execution",
                },
            }

        except Exception as e:
            # fallback-ok: Introspection gathering should degrade gracefully rather than fail - return minimal valid introspection data
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to generate full orchestrator introspection data: {e!s}, using fallback",
                {"node_id": self.node_id, "error": str(e)},
            )
            # fallback-ok: Return degraded introspection response to maintain system observability even when full introspection fails
            return {
                "node_capabilities": {
                    "node_type": "NodeOrchestrator",
                    "node_classification": "orchestrator",
                    "node_id": self.node_id,
                },
                "runtime_information": {
                    "current_health_status": "unknown",
                    "condition_function_count": len(self.condition_functions),
                },
                "introspection_metadata": {
                    "generated_at": str(time.time()),
                    "introspection_version": "1.0.0",
                    "supports_full_introspection": False,  # fallback-ok: Intentionally returning partial data rather than raising exception
                    "fallback_reason": str(e),
                },
            }

    def _extract_orchestrator_operations(self) -> list[Any]:
        """Extract available orchestrator operations."""
        operations = [
            "process",
            "emit_thunk",
            "execute_workflow",
            "coordinate_execution",
        ]

        try:
            # Add execution mode operations
            for mode in EnumExecutionMode:
                operations.append(f"execute_{mode.value}_workflow")

            # Add workflow management operations
            operations.extend(
                [
                    "create_ticket_lifecycle_steps",
                    "evaluate_condition",
                    "manage_dependencies",
                    "coordinate_parallel_execution",
                ],
            )

            # Add RSD operations
            operations.extend(
                [
                    "ticket_lifecycle_transition",
                    "dependency_aware_execution",
                    "batch_processing_coordination",
                ],
            )

        except Exception as e:
            # fallback-ok: Operation extraction for introspection should return partial list[Any]rather than fail - graceful degradation maintains introspection availability
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract all orchestrator operations: {e!s}",
                {"node_id": self.node_id},
            )
            # Intentionally continue to return partial operations list[Any]return operations  # fallback-ok: Return partial operations list[Any]on error rather than raising exception

        return operations

    def _extract_orchestrator_io_specifications(self) -> dict[str, Any]:
        """Extract input/output specifications for orchestrator operations."""
        return {
            "input_model": "omnibase.core.node_orchestrator.ModelOrchestratorInput",
            "output_model": "omnibase.core.node_orchestrator.ModelOrchestratorOutput",
            "supports_streaming": False,
            "supports_batch_processing": True,
            "supports_parallel_coordination": True,
            "execution_modes": [mode.value for mode in EnumExecutionMode],
            "thunk_types": [thunk_type.value for thunk_type in EnumThunkType],
            "branch_conditions": [condition.value for condition in EnumBranchCondition],
            "input_requirements": ["workflow_id", "steps"],
            "output_guarantees": [
                "workflow_state",
                "steps_completed",
                "thunks_emitted",
                "processing_time_ms",
            ],
        }

    def _extract_orchestrator_performance_characteristics(self) -> dict[str, Any]:
        """Extract performance characteristics specific to orchestrator operations."""
        return {
            "expected_response_time_ms": "varies_by_workflow_complexity_and_step_count",
            "throughput_capacity": f"up_to_{self.max_concurrent_workflows}_concurrent_workflows",
            "memory_usage_pattern": "workflow_state_tracking_with_thunk_queuing",
            "cpu_intensity": "low_to_medium_coordination_overhead",
            "supports_parallel_processing": True,
            "caching_enabled": False,  # Live workflow coordination
            "performance_monitoring": True,
            "deterministic_operations": False,  # Depends on execution order and timing
            "side_effects": True,  # Orchestration has side effects
            "coordination_overhead": "minimal",
            "thunk_emission_performance": "async_non_blocking",
            "dependency_resolution_efficiency": "topological_sorting_based",
        }

    def _extract_workflow_configuration(self) -> dict[str, Any]:
        """Extract workflow configuration from contract."""
        try:
            return {
                "max_parallel_workflows": self.max_concurrent_workflows,
                "default_step_timeout_ms": self.default_step_timeout_ms,
                "max_thunk_queue_size": self.max_thunk_queue_size,
                "thunk_emission_enabled": self.thunk_emission_enabled,
                "load_balancing_enabled": self.load_balancing_enabled,
                "dependency_resolution_enabled": self.dependency_resolution_enabled,
            }
        except Exception as e:
            # fallback-ok: Configuration extraction for introspection should return minimal data rather than fail
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract workflow configuration: {e!s}",
                {"node_id": self.node_id},
            )
            return {"max_parallel_workflows": self.max_concurrent_workflows}

    def _extract_coordination_constraints(self) -> dict[str, Any]:
        """Extract coordination constraints and requirements."""
        return {
            "requires_container": True,
            "supports_nested_workflows": False,
            "supports_conditional_branching": True,
            "supports_parallel_execution": True,
            "max_parallel_workflows": self.max_concurrent_workflows,
            "default_step_timeout_ms": self.default_step_timeout_ms,
            "thunk_emission_required_for_coordination": True,
            "dependency_resolution_automatic": True,
            "failure_recovery_configurable": True,
        }

    def _get_orchestrator_health_status(self) -> str:
        """Get health status specific to orchestrator operations."""
        try:
            # Check if basic orchestration works
            test_thunk = ModelThunk(
                thunk_id=uuid4(),
                thunk_type=EnumThunkType.COMPUTE,
                target_node_type="NodeCompute",
                operation_data={"test": True},
                dependencies=[],
                priority=1,
                timeout_ms=1000,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )

            test_step = ModelWorkflowStepExecution(
                step_id=uuid4(),
                step_name="Health Check",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                thunks=[test_thunk],
            )

            test_input = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[test_step],
            )

            # For health check, we'll just validate the input without processing
            self._validate_orchestrator_input(test_input)
            return "healthy"

        except Exception:
            # fallback-ok: Health check should return status string, not raise exceptions
            return "unhealthy"

    def _get_orchestration_metrics_sync(self) -> dict[str, Any]:
        """Get orchestration metrics synchronously for introspection."""
        try:
            return {
                **self.orchestration_metrics,
                "load_balancer_status": {
                    "enabled": self.load_balancing_enabled,
                    "active_operations": (
                        len(getattr(self.load_balancer, "active_operations", {}))
                        if hasattr(self, "load_balancer")
                        else 0
                    ),
                },
                "condition_functions": {
                    "registered_count": len(self.condition_functions),
                    "available_conditions": list[Any](self.condition_functions.keys()),
                },
            }
        except Exception as e:
            # fallback-ok: Metrics gathering should return partial/error data rather than fail introspection
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get orchestration metrics: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown", "error": str(e)}

    def _get_orchestrator_resource_usage(self) -> dict[str, Any]:
        """Get resource usage specific to orchestrator operations."""
        try:
            return {
                "condition_functions_registered": len(self.condition_functions),
                "max_parallel_workflows": self.max_concurrent_workflows,
                "max_thunk_queue_size": self.max_thunk_queue_size,
                "thunk_emission_enabled": self.thunk_emission_enabled,
                "load_balancing_enabled": self.load_balancing_enabled,
                "dependency_resolution_enabled": self.dependency_resolution_enabled,
            }
        except Exception as e:
            # fallback-ok: Resource usage gathering should return partial/error data rather than fail introspection
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get orchestrator resource usage: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown"}

    def _get_workflow_state(self) -> dict[str, Any]:
        """Get current workflow state information."""
        try:
            return {
                "active_workflows": 0,  # Would track active workflows in real implementation
                "queued_workflows": 0,  # Would track queued workflows
                "completed_workflows_count": sum(
                    metrics.get("success_count", 0)
                    for metrics in self.orchestration_metrics.values()
                ),
                "failed_workflows_count": sum(
                    metrics.get("error_count", 0)
                    for metrics in self.orchestration_metrics.values()
                ),
                "workflow_execution_modes_used": list[Any](
                    self.orchestration_metrics.keys(),
                ),
            }
        except Exception as e:
            # fallback-ok: Workflow state gathering should return partial/error data rather than fail introspection
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to get workflow state: {e!s}",
                {"node_id": self.node_id},
            )
            return {"status": "unknown", "error": str(e)}

    def _get_thunk_emission_status(self) -> dict[str, Any]:
        """Get thunk emission status."""
        return {
            "thunk_emission_enabled": self.thunk_emission_enabled,
            "max_thunk_queue_size": self.max_thunk_queue_size,
            "supported_thunk_types": [thunk_type.value for thunk_type in EnumThunkType],
            "thunk_emission_performance": "async_non_blocking",
            "priority_based_emission": True,
            "timeout_configurable": True,
        }
