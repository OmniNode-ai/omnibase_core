> **Navigation**: [Home](../../index.md) > [Guides](../README.md) > Templates > ORCHESTRATOR Node Template

# ORCHESTRATOR Node Template

## Overview

This template provides the unified architecture pattern for ONEX ORCHESTRATOR nodes. ORCHESTRATOR nodes are responsible for coordinating complex workflows, managing multi-step operations, and orchestrating interactions between other node types within the ONEX ecosystem.

## Key Characteristics

- **Workflow Orchestration**: Coordinate multi-step business processes
- **Node Communication**: Manage interactions between COMPUTE, EFFECT, and REDUCER nodes
- **State Management**: Maintain workflow state and progress tracking
- **Error Recovery**: Handle failures and implement retry/compensation logic
- **Performance Monitoring**: Track end-to-end workflow performance

## Action Pattern & Lease Management

ORCHESTRATOR nodes use the **Action pattern** for delegating work to other nodes:

- **ModelAction**: Encapsulates a unit of work with ownership and execution metadata
- **lease_id**: UUID proving orchestrator ownership - prevents other nodes from claiming the action
- **epoch**: Integer counter for optimistic concurrency - detects conflicting updates
- **action_type**: Specifies the type of work (EXECUTE_WORKFLOW, EXECUTE_COMPUTATION, etc.)
- **payload**: Contains the actual work data and parameters

### Lease Management Benefits

1. **Ownership Tracking**: Each action has a unique lease_id from the creating orchestrator
2. **Conflict Detection**: Epoch increments after each workflow, enabling stale update detection
3. **Distributed Safety**: Multiple orchestrators can coordinate without race conditions
4. **Audit Trail**: Clear provenance of who created and owns each action

### Example Action Creation

```
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.EXECUTE_WORKFLOW,
    target_node_type="NodeCompute",
    payload={"data": value},
    lease_id=self.lease_id,  # Orchestrator ownership
    epoch=self.current_epoch,  # Optimistic concurrency
    priority=5,
)
```

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
│                   │       └── config_subcontract.yaml
│                   ├── models/
│                   │   ├── __init__.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_input.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_output.py
│                   │   ├── model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_config.py
│                   │   ├── model_workflow_step.py
│                   │   └── model_workflow_state.py
│                   ├── enums/
│                   │   ├── __init__.py
│                   │   ├── enum_{DOMAIN}_{MICROSERVICE_NAME}_workflow_type.py
│                   │   ├── enum_workflow_status.py
│                   │   └── enum_step_status.py
│                   ├── workflows/
│                   │   ├── __init__.py
│                   │   ├── base_workflow.py
│                   │   ├── {DOMAIN}_workflow.py
│                   │   └── workflow_registry.py
│                   ├── utils/
│                   │   ├── __init__.py
│                   │   ├── node_client.py
│                   │   ├── state_manager.py
│                   │   ├── retry_handler.py
│                   │   └── workflow_scheduler.py
│                   └── manifest.yaml
└── tests/
    └── {REPOSITORY_NAME}/
        └── nodes/
            └── node_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator/
                └── v1_0_0/
                    ├── test_node.py
                    ├── test_config.py
                    ├── test_contracts.py
                    ├── test_models.py
                    └── test_workflows.py
```

## Template Files

### 1. Node Implementation (`node.py`)

```
"""ONEX ORCHESTRATOR node for {DOMAIN} {MICROSERVICE_NAME} operations."""

import asyncio
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4
import time
from contextlib import asynccontextmanager
from enum import Enum

from pydantic import ValidationError
# v0.4.0 unified node imports
from omnibase_core.nodes import (
    NodeOrchestrator,
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
    # Workflow-related enums for coordination
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowStatus,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_onex_warning import ModelONEXWarning
from omnibase_core.utils.error_sanitizer import ErrorSanitizer
from omnibase_core.utils.circuit_breaker import CircuitBreakerMixin

from .config import {DomainCamelCase}{MicroserviceCamelCase}OrchestratorConfig
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_input import Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput
from .models.model_{DOMAIN}_{MICROSERVICE_NAME}_orchestrator_output import Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput
from .models.model_workflow_step import ModelWorkflowStep
from .models.model_workflow_state import ModelWorkflowState
from .enums.enum_{DOMAIN}_{MICROSERVICE_NAME}_workflow_type import Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType
from .enums.enum_workflow_status import EnumWorkflowStatus
from .enums.enum_step_status import EnumStepStatus
from .workflows.workflow_registry import WorkflowRegistry
from .utils.node_client import NodeClient
from .utils.state_manager import StateManager
from .utils.retry_handler import RetryHandler
from .utils.workflow_scheduler import WorkflowScheduler


class Node{DomainCamelCase}{MicroserviceCamelCase}Orchestrator(
    NodeOrchestrator[
        Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput,
        Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput,
        {DomainCamelCase}{MicroserviceCamelCase}OrchestratorConfig
    ],
    CircuitBreakerMixin
):
    """Workflow-driven ORCHESTRATOR node for {DOMAIN} {MICROSERVICE_NAME} coordination.

    This node provides comprehensive workflow orchestration services for {DOMAIN}
    domain operations, managing complex multi-step processes and node interactions.

    v0.4.0 Architecture:
    - NodeOrchestrator provides MixinWorkflowExecution for workflow-driven coordination
    - Uses EnumActionType, EnumBranchCondition, EnumExecutionMode, EnumWorkflowStatus
    - Lease-based ownership with optimistic concurrency control

    Key Features:
    - Sub-{PERFORMANCE_TARGET}ms workflow initiation
    - Multi-node coordination and communication
    - State persistence and recovery
    - Comprehensive error handling and retries
    - Performance monitoring and optimization

    Action Pattern & Lease Management:
    - Creates Actions for delegating work to other nodes
    - lease_id: Unique identifier proving this orchestrator owns the action
    - epoch: Optimistic concurrency counter to detect conflicting updates
    - Actions encapsulate work units with ownership and execution tracking
    """

    def __init__(self, config: {DomainCamelCase}{MicroserviceCamelCase}OrchestratorConfig):
        """Initialize the ORCHESTRATOR node with configuration.

        Args:
            config: Configuration for the orchestration operations
        """
        super().__init__(config)
        CircuitBreakerMixin.__init__(
            self,
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout,
            expected_exception=Exception
        )

        # Initialize orchestration components
        self._workflow_registry = WorkflowRegistry(config.workflow_config)
        self._node_client = NodeClient(config.node_client_config)
        self._state_manager = StateManager(config.state_config)
        self._retry_handler = RetryHandler(config.retry_config)
        self._scheduler = WorkflowScheduler(config.scheduler_config)
        self._error_sanitizer = ErrorSanitizer()

        # Orchestration state
        self._active_workflows = {}
        self._workflow_metrics = []
        self._node_health_cache = {}
        self._performance_stats = {"total_workflows": 0, "successful_workflows": 0}

        # Lease management for action ownership
        self.lease_id = uuid4()  # Unique lease ID for this orchestrator instance
        self.current_epoch = 0  # Optimistic concurrency control counter

    @asynccontextmanager
    async def _workflow_tracking(self, workflow_type: Enum{DomainCamelCase}{MicroserviceCamelCase}WorkflowType):
        """Track workflow performance metrics."""
        start_time = time.perf_counter()
        workflow_id = str(uuid4())

        try:
            self._performance_stats["total_workflows"] += 1
            yield workflow_id
            self._performance_stats["successful_workflows"] += 1
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            self._workflow_metrics.append({
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })

    async def process(
        self,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput
    ) -> Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput:
        """Process {DOMAIN} {MICROSERVICE_NAME} orchestration with typed interface.

        This is the business logic interface that provides type-safe workflow
        orchestration without ONEX infrastructure concerns.

        Args:
            input_data: Validated input data for orchestration

        Returns:
            Orchestration output with workflow results and state

        Raises:
            ValidationError: If input validation fails
            WorkflowError: If workflow execution fails
            TimeoutError: If workflow exceeds time limits
        """
        async with self._workflow_tracking(input_data.workflow_type) as workflow_id:
            try:
                # Initialize workflow state
                workflow_state = await self._initialize_workflow(workflow_id, input_data)

                # Execute workflow steps
                workflow_result = await self._execute_workflow(workflow_state, input_data)

                # Finalize workflow
                final_state = await self._finalize_workflow(workflow_state, workflow_result)

                return Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(
                    workflow_type=input_data.workflow_type,
                    workflow_id=UUID(workflow_id),
                    workflow_result=workflow_result,
                    final_state=final_state,
                    success=True,
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=(
                        self._workflow_metrics[-1]["duration_ms"]
                        if self._workflow_metrics else 0.0
                    ),
                    steps_executed=len(final_state.completed_steps),
                    nodes_involved=len(set(step.node_type for step in final_state.completed_steps)),
                    metadata={
                        "workflow_version": final_state.workflow_version,
                        "retry_count": final_state.retry_count,
                        "compensation_applied": final_state.compensation_applied,
                        "performance_tier": self._get_performance_tier()
                    }
                )

            except ValidationError as e:
                sanitized_error = self._error_sanitizer.sanitize_validation_error(str(e))
                return Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(
                    workflow_type=input_data.workflow_type,
                    workflow_id=UUID(workflow_id),
                    success=False,
                    error_message=f"Input validation failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0,
                    steps_executed=0,
                    nodes_involved=0
                )

            except asyncio.TimeoutError:
                # Attempt workflow compensation
                await self._compensate_workflow(workflow_id)

                return Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(
                    workflow_type=input_data.workflow_type,
                    workflow_id=UUID(workflow_id),
                    success=False,
                    error_message="Workflow timeout exceeded",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=self.config.orchestration_timeout_ms,
                    steps_executed=0,
                    nodes_involved=0
                )

            except Exception as e:
                sanitized_error = self._error_sanitizer.sanitize_error(str(e))
                # Attempt workflow compensation
                await self._compensate_workflow(workflow_id)

                return Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorOutput(
                    workflow_type=input_data.workflow_type,
                    workflow_id=UUID(workflow_id),
                    success=False,
                    error_message=f"Workflow execution failed: {sanitized_error}",
                    correlation_id=input_data.correlation_id,
                    timestamp=time.time(),
                    processing_time_ms=0.0,
                    steps_executed=0,
                    nodes_involved=0
                )

    async def _initialize_workflow(
        self,
        workflow_id: str,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput
    ) -> ModelWorkflowState:
        """Initialize workflow state and prepare execution plan."""

        # Get workflow definition
        workflow_definition = self._workflow_registry.get_workflow(input_data.workflow_type)

        # Create initial workflow state
        workflow_state = ModelWorkflowState(
            workflow_id=UUID(workflow_id),
            workflow_type=input_data.workflow_type,
            workflow_version=workflow_definition.version,
            status=EnumWorkflowStatus.INITIALIZING,
            current_step_index=0,
            total_steps=len(workflow_definition.steps),
            completed_steps=[],
            failed_steps=[],
            retry_count=0,
            compensation_applied=False,
            created_at=time.time(),
            updated_at=time.time(),
            context=input_data.workflow_context or {}
        )

        # Persist initial state
        await self._state_manager.save_workflow_state(workflow_state)

        # Add to active workflows
        self._active_workflows[workflow_id] = workflow_state

        return workflow_state

    async def _execute_workflow(
        self,
        workflow_state: ModelWorkflowState,
        input_data: Model{DomainCamelCase}{MicroserviceCamelCase}OrchestratorInput
    ) -> Dict[str, Any]:
        """Execute workflow steps in sequence."""

        workflow_definition = self._workflow_registry.get_workflow(input_data.workflow_type)
        workflow_result = {"steps": [], "final_output": None}

        # Update status to running
        workflow_state.status = EnumWorkflowStatus.RUNNING
        await self._state_manager.save_workflow_state(workflow_state)

        # Execute each step
        for step_index, step_definition in enumerate(workflow_definition.steps):
            workflow_state.current_step_index = step_index

            try:
                # Apply circuit breaker protection
                async with self.circuit_breaker():
                    step_result = await self._execute_step(
                        step_definition,
                        workflow_state,
                        input_data.step_inputs.get(step_definition.name, {})
                    )

                # Record successful step
                completed_step = ModelWorkflowStep(
                    step_name=step_definition.name,
                    step_index=step_index,
                    node_type=step_definition.node_type,
                    status=EnumStepStatus.COMPLETED,
                    input_data=input_data.step_inputs.get(step_definition.name, {}),
                    output_data=step_result,
                    execution_time_ms=step_result.get("processing_time_ms", 0.0),
                    retry_count=0,
                    started_at=time.time() - (step_result.get("processing_time_ms", 0.0) / 1000),
                    completed_at=time.time()
                )

                workflow_state.completed_steps.append(completed_step)
                workflow_result["steps"].append({
                    "step_name": step_definition.name,
                    "result": step_result,
                    "success": True
                })

                # Update workflow context with step results
                workflow_state.context[f"step_{step_definition.name}_result"] = step_result

            except Exception as e:
                # Handle step failure
                failed_step = ModelWorkflowStep(
                    step_name=step_definition.name,
                    step_index=step_index,
                    node_type=step_definition.node_type,
                    status=EnumStepStatus.FAILED,
                    input_data=input_data.step_inputs.get(step_definition.name, {}),
                    error_message=str(e),
                    retry_count=0,
                    started_at=time.time(),
                    completed_at=time.time()
                )

                workflow_state.failed_steps.append(failed_step)

                # Attempt retry if configured
                if step_definition.retry_config and step_definition.retry_config.max_retries > 0:
                    retry_success = await self._retry_step(
                        step_definition,
                        workflow_state,
                        input_data.step_inputs.get(step_definition.name, {}),
                        failed_step
                    )

                    if not retry_success:
                        # Step failed after retries
                        workflow_state.status = EnumWorkflowStatus.FAILED
                        await self._state_manager.save_workflow_state(workflow_state)
                        raise Exception(f"Step {step_definition.name} failed after retries: {e}")
                else:
                    # No retry configured, fail workflow
                    workflow_state.status = EnumWorkflowStatus.FAILED
                    await self._state_manager.save_workflow_state(workflow_state)
                    raise Exception(f"Step {step_definition.name} failed: {e}")

            # Save state after each step
            workflow_state.updated_at = time.time()
            await self._state_manager.save_workflow_state(workflow_state)

        # Set final output
        if workflow_state.completed_steps:
            workflow_result["final_output"] = workflow_state.completed_steps[-1].output_data

        return workflow_result

    async def _execute_step(
        self,
        step_definition: Any,
        workflow_state: ModelWorkflowState,
        step_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step using Action-based delegation.

        Actions encapsulate work to be performed by other nodes, with lease
        management ensuring orchestrator ownership and optimistic concurrency.
        """

        # Create action for this workflow step
        action = await self._create_action_for_step(
            step_definition,
            workflow_state,
            step_input
        )

        # Prepare step input with workflow context
        enriched_input = {
            **step_input,
            "workflow_context": workflow_state.context,
            "correlation_id": str(workflow_state.workflow_id),
            "action": action  # Pass action to node for execution tracking
        }

        # Execute based on node type
        if step_definition.node_type == "COMPUTE":
            return await self._node_client.call_compute_node(
                step_definition.node_endpoint,
                enriched_input,
                timeout_ms=step_definition.timeout_ms
            )

        elif step_definition.node_type == "EFFECT":
            return await self._node_client.call_effect_node(
                step_definition.node_endpoint,
                enriched_input,
                timeout_ms=step_definition.timeout_ms
            )

        elif step_definition.node_type == "REDUCER":
            return await self._node_client.call_reducer_node(
                step_definition.node_endpoint,
                enriched_input,
                timeout_ms=step_definition.timeout_ms
            )

        elif step_definition.node_type == "ORCHESTRATOR":
            # Nested orchestration
            return await self._node_client.call_orchestrator_node(
                step_definition.node_endpoint,
                enriched_input,
                timeout_ms=step_definition.timeout_ms
            )

        else:
            raise ValueError(f"Unsupported node type: {step_definition.node_type}")

    async def _create_action_for_step(
        self,
        step_definition: Any,
        workflow_state: ModelWorkflowState,
        step_input: Dict[str, Any]
    ) -> "ModelAction":
        """Create an Action for workflow step delegation with lease management.

        Actions encapsulate work units with ownership tracking and optimistic
        concurrency control, enabling safe distributed workflow execution.

        Returns:
            ModelAction with lease_id and epoch for orchestrator ownership
        """
        # EnumActionType already imported from omnibase_core.nodes
        from omnibase_core.models.orchestrator.model_action import ModelAction

        # Map step definition to action type
        action_type_mapping = {
            "COMPUTE": EnumActionType.EXECUTE_COMPUTATION,
            "EFFECT": EnumActionType.EXECUTE_SIDE_EFFECT,
            "REDUCER": EnumActionType.EXECUTE_AGGREGATION,
            "ORCHESTRATOR": EnumActionType.EXECUTE_WORKFLOW
        }

        action_type = action_type_mapping.get(
            step_definition.node_type,
            EnumActionType.EXECUTE_WORKFLOW
        )

        # Create action with lease management
        action = ModelAction(
            action_id=uuid4(),
            action_type=action_type,
            target_node_type=step_definition.node_type,
            payload={
                "step_name": step_definition.name,
                "step_input": step_input,
                "workflow_id": str(workflow_state.workflow_id),
                "step_index": workflow_state.current_step_index
            },
            lease_id=self.lease_id,  # Orchestrator owns this action - prevents other nodes from claiming it
            epoch=self.current_epoch,  # Optimistic concurrency - detects conflicting updates
            priority=step_definition.priority if hasattr(step_definition, 'priority') else 5,
            created_at=time.time(),
            metadata={
                "workflow_type": str(workflow_state.workflow_type),
                "correlation_id": str(workflow_state.workflow_id),
                "timeout_ms": step_definition.timeout_ms
            }
        )

        return action

    async def _retry_step(
        self,
        step_definition: Any,
        workflow_state: ModelWorkflowState,
        step_input: Dict[str, Any],
        failed_step: ModelWorkflowStep
    ) -> bool:
        """Retry a failed workflow step."""

        retry_config = step_definition.retry_config
        max_retries = retry_config.max_retries

        for retry_attempt in range(1, max_retries + 1):
            try:
                # Wait before retry
                await asyncio.sleep(retry_config.retry_delay_ms / 1000.0)

                # Execute step with retry context
                retry_input = {
                    **step_input,
                    "retry_attempt": retry_attempt,
                    "original_error": failed_step.error_message
                }

                step_result = await self._execute_step(step_definition, workflow_state, retry_input)

                # Retry succeeded
                completed_step = ModelWorkflowStep(
                    step_name=step_definition.name,
                    step_index=failed_step.step_index,
                    node_type=step_definition.node_type,
                    status=EnumStepStatus.COMPLETED,
                    input_data=retry_input,
                    output_data=step_result,
                    execution_time_ms=step_result.get("processing_time_ms", 0.0),
                    retry_count=retry_attempt,
                    started_at=time.time() - (step_result.get("processing_time_ms", 0.0) / 1000),
                    completed_at=time.time()
                )

                # Replace failed step with successful retry
                workflow_state.failed_steps.remove(failed_step)
                workflow_state.completed_steps.append(completed_step)
                workflow_state.retry_count += retry_attempt

                return True

            except Exception as retry_error:
                # Update failed step with retry information
                failed_step.retry_count = retry_attempt
                failed_step.error_message = f"Retry {retry_attempt}: {str(retry_error)}"

                if retry_attempt == max_retries:
                    # All retries exhausted
                    workflow_state.retry_count += retry_attempt
                    return False

        return False

    async def _finalize_workflow(
        self,
        workflow_state: ModelWorkflowState,
        workflow_result: Dict[str, Any]
    ) -> ModelWorkflowState:
        """Finalize workflow execution and clean up resources."""

        # Update final status
        if workflow_state.failed_steps:
            workflow_state.status = EnumWorkflowStatus.FAILED
        else:
            workflow_state.status = EnumWorkflowStatus.COMPLETED

        workflow_state.updated_at = time.time()

        # Save final state
        await self._state_manager.save_workflow_state(workflow_state)

        # Remove from active workflows
        workflow_id_str = str(workflow_state.workflow_id)
        if workflow_id_str in self._active_workflows:
            del self._active_workflows[workflow_id_str]

        # Increment epoch for next workflow - optimistic concurrency
        self._increment_epoch()

        return workflow_state

    def _increment_epoch(self):
        """Increment epoch counter for optimistic concurrency control.

        The epoch counter is incremented after each workflow execution,
        ensuring that any Actions created in the next workflow will have
        a higher epoch value. This enables detection of stale or conflicting
        updates in distributed systems.
        """
        self.current_epoch += 1

    def _validate_action_ownership(self, action: "ModelAction") -> bool:
        """Validate that this orchestrator owns the given action.

        Checks lease_id to ensure the action was created by this orchestrator
        instance and validates epoch to detect stale actions.

        Args:
            action: The action to validate

        Returns:
            True if action is owned by this orchestrator and epoch is valid

        Raises:
            ValueError: If lease_id doesn't match or epoch is too old
        """
        # Verify lease ownership
        if action.lease_id != self.lease_id:
            raise ValueError(
                f"Action lease_id mismatch: expected {self.lease_id}, "
                f"got {action.lease_id}"
            )

        # Verify epoch is not stale (allow current or future epochs)
        if action.epoch < self.current_epoch:
            raise ValueError(
                f"Stale action detected: action epoch {action.epoch} < "
                f"current epoch {self.current_epoch}"
            )

        return True

    async def _compensate_workflow(self, workflow_id: str):
        """Perform compensation actions for failed workflow."""

        if workflow_id not in self._active_workflows:
            return

        workflow_state = self._active_workflows[workflow_id]

        try:
            # Execute compensation steps in reverse order
            for completed_step in reversed(workflow_state.completed_steps):
                if hasattr(completed_step, 'compensation_action'):
                    await self._execute_compensation(completed_step)

            workflow_state.compensation_applied = True
            await self._state_manager.save_workflow_state(workflow_state)

        except Exception as e:
            # Log compensation failure but don't raise
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            workflow_state.context["compensation_error"] = sanitized_error
            await self._state_manager.save_workflow_state(workflow_state)

    async def _execute_compensation(self, completed_step: ModelWorkflowStep):
        """Execute compensation action for a completed step."""
        # Implementation depends on specific compensation strategies
        pass

    def _get_performance_tier(self) -> str:
        """Get current performance tier based on metrics."""
        if not self._workflow_metrics:
            return "optimal"

        recent_metrics = self._workflow_metrics[-10:]  # Last 10 workflows
        avg_duration = sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)

        if avg_duration < self.config.performance_threshold_ms * 0.5:
            return "optimal"
        elif avg_duration < self.config.performance_threshold_ms:
            return "good"
        elif avg_duration < self.config.performance_threshold_ms * 2:
            return "degraded"
        else:
            return "poor"

    async def get_workflow_status(self, workflow_id: UUID) -> Optional[ModelWorkflowState]:
        """Get status of a specific workflow."""
        workflow_id_str = str(workflow_id)

        # Check active workflows first
        if workflow_id_str in self._active_workflows:
            return self._active_workflows[workflow_id_str]

        # Check persistent storage
        return await self._state_manager.load_workflow_state(workflow_id)

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for monitoring."""
        if not self._workflow_metrics:
            return {
                "total_workflows": self._performance_stats["total_workflows"],
                "successful_workflows": self._performance_stats["successful_workflows"],
                "success_rate": 0.0,
                "average_duration_ms": 0.0,
                "active_workflows": 0
            }

        total_workflows = len(self._workflow_metrics)
        average_duration = sum(m["duration_ms"] for m in self._workflow_metrics) / total_workflows
        success_rate = (self._performance_stats["successful_workflows"] /
                       self._performance_stats["total_workflows"]) * 100

        return {
            "total_workflows": self._performance_stats["total_workflows"],
            "successful_workflows": self._performance_stats["successful_workflows"],
            "success_rate": round(success_rate, 2),
            "average_duration_ms": round(average_duration, 2),
            "max_duration_ms": max(m["duration_ms"] for m in self._workflow_metrics),
            "min_duration_ms": min(m["duration_ms"] for m in self._workflow_metrics),
            "active_workflows": len(self._active_workflows),
            "performance_tier": self._get_performance_tier(),
            "circuit_breaker_status": self.circuit_breaker_status
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Test core components
            registry_healthy = await self._workflow_registry.health_check()
            client_healthy = await self._node_client.health_check()
            state_manager_healthy = await self._state_manager.health_check()
            scheduler_healthy = await self._scheduler.health_check()

            # Check active workflow health
            active_workflow_count = len(self._active_workflows)
            workflow_capacity_healthy = active_workflow_count < self.config.max_concurrent_workflows

            # Check recent performance
            recent_metrics = [
                m for m in self._workflow_metrics
                if time.time() - m["timestamp"] < 300  # Last 5 minutes
            ]

            avg_performance = (
                sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)
                if recent_metrics else 0.0
            )

            performance_healthy = avg_performance < self.config.performance_threshold_ms

            overall_healthy = all([
                registry_healthy,
                client_healthy,
                state_manager_healthy,
                scheduler_healthy,
                workflow_capacity_healthy,
                performance_healthy
            ])

            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": {
                    "workflow_registry": "healthy" if registry_healthy else "unhealthy",
                    "node_client": "healthy" if client_healthy else "unhealthy",
                    "state_manager": "healthy" if state_manager_healthy else "unhealthy",
                    "scheduler": "healthy" if scheduler_healthy else "unhealthy"
                },
                "capacity": {
                    "active_workflows": active_workflow_count,
                    "max_concurrent": self.config.max_concurrent_workflows,
                    "utilization_percent": round((active_workflow_count / self.config.max_concurrent_workflows) * 100, 2)
                },
                "performance": {
                    "average_duration_ms": round(avg_performance, 2),
                    "threshold_ms": self.config.performance_threshold_ms,
                    "recent_workflows": len(recent_metrics),
                    "success_rate": round((self._performance_stats["successful_workflows"] /
                                         max(1, self._performance_stats["total_workflows"])) * 100, 2)
                },
                "circuit_breaker": self.circuit_breaker_status
            }

        except Exception as e:
            sanitized_error = self._error_sanitizer.sanitize_error(str(e))
            return {
                "status": "unhealthy",
                "error": sanitized_error,
                "timestamp": time.time()
            }
```

This template provides the complete ORCHESTRATOR node implementation with workflow orchestration, state management, error recovery, and comprehensive monitoring. The full template would continue with the remaining files (configuration, models, enums, workflows, utils, subcontracts, and manifest) following the same unified architecture patterns established in the previous templates.
