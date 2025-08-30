"""
Enhanced Workflow Reducer Protocol for LlamaIndex integration.

This module provides the enhanced reducer protocol that supports both
traditional synchronous state transitions and LlamaIndex workflow-based
asynchronous orchestration with observable state changes.

Author: ONEX Framework Team
"""

import asyncio
from abc import abstractmethod
from typing import Any, Dict, Optional, Protocol

from llama_index.core.workflow import Workflow

from omnibase_core.core.monadic.model_node_result import NodeResult
from omnibase_core.model.core.model_reducer import ActionModel, ModelState


class ProtocolWorkflowReducer(Protocol):
    """
    Enhanced reducer protocol with LlamaIndex workflow support.

    Extends the basic reducer pattern to support:
    - Asynchronous workflow-based state transitions
    - Observable state changes via NodeResult
    - Complex orchestration through LlamaIndex workflows
    - Monadic composition with error handling
    - Event emission for monitoring and coordination
    """

    @abstractmethod
    def initial_state(self) -> ModelState:
        """
        Returns the initial state for the reducer.

        Returns:
            ModelState: The initial state object
        """
        ...

    @abstractmethod
    def dispatch(self, state: ModelState, action: ActionModel) -> ModelState:
        """
        Synchronous state transition for simple operations.

        Args:
            state: Current state
            action: Action to process

        Returns:
            ModelState: New state after applying action
        """
        ...

    @abstractmethod
    async def dispatch_async(
        self, state: ModelState, action: ActionModel
    ) -> NodeResult[ModelState]:
        """
        Asynchronous workflow-based state transition.

        This method enables complex state transitions that may involve:
        - Multiple async operations
        - External service calls
        - Error recovery and retry logic
        - Observable state change events
        - Integration with LlamaIndex workflows

        Args:
            state: Current state
            action: Action to process

        Returns:
            NodeResult[ModelState]: Monadic result with new state,
                                  context, events, and error handling
        """
        ...

    @abstractmethod
    def create_workflow(self) -> Optional[Workflow]:
        """
        Factory method for creating LlamaIndex workflow instances.

        Returns:
            Optional[Workflow]: Workflow instance for complex orchestration,
                              or None if using synchronous dispatch only
        """
        ...

    def validate_state_transition(
        self, from_state: ModelState, action: ActionModel, to_state: ModelState
    ) -> bool:
        """
        Validate that a state transition is legal.

        Args:
            from_state: Source state
            action: Action being applied
            to_state: Target state

        Returns:
            bool: True if transition is valid, False otherwise
        """
        # Default implementation allows all transitions
        return True

    def get_state_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get the schema definition for this reducer's state.

        Returns:
            Optional[Dict[str, Any]]: JSON schema for state validation,
                                    or None if not available
        """
        return None

    def get_action_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get the schema definition for actions this reducer handles.

        Returns:
            Optional[Dict[str, Any]]: JSON schema for action validation,
                                    or None if not available
        """
        return None


class SimpleWorkflowReducer(ProtocolWorkflowReducer):
    """
    Base implementation of ProtocolWorkflowReducer for simple cases.

    Provides default implementations that delegate async operations
    to synchronous dispatch, suitable for reducers that don't need
    complex workflow orchestration.
    """

    async def dispatch_async(
        self, state: ModelState, action: ActionModel
    ) -> NodeResult[ModelState]:
        """
        Default async implementation that wraps synchronous dispatch.

        For simple reducers that don't need workflow orchestration,
        this provides async compatibility by wrapping the sync dispatch.
        """
        try:
            new_state = self.dispatch(state, action)

            return NodeResult.success(
                value=new_state,
                provenance=[f"{self.__class__.__name__}.dispatch"],
                trust_score=1.0,
                metadata={
                    "action_type": getattr(action, "type", "unknown"),
                    "sync_dispatch": True,
                },
                state_delta={
                    "previous_state": (
                        state.__dict__ if hasattr(state, "__dict__") else str(state)
                    ),
                    "new_state": (
                        new_state.__dict__
                        if hasattr(new_state, "__dict__")
                        else str(new_state)
                    ),
                },
            )

        except Exception as e:
            from omnibase_core.core.monadic.model_node_result import (
                ErrorInfo, ErrorType)

            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Synchronous dispatch failed: {str(e)}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                retryable=False,
            )

            return NodeResult.failure(
                error=error_info,
                provenance=[f"{self.__class__.__name__}.dispatch.failed"],
            )

    def create_workflow(self) -> Optional[Workflow]:
        """
        Default implementation returns None (no workflow needed).

        Override this method in subclasses that need LlamaIndex workflows.
        """
        return None


class WorkflowOrchestrationMixin:
    """
    Mixin providing common workflow orchestration patterns.

    This mixin can be used by reducers that need to coordinate
    multiple workflow steps or handle complex async operations.
    """

    async def run_workflow_step(
        self,
        workflow: Workflow,
        step_name: str,
        input_data: Any,
        timeout: Optional[float] = None,
    ) -> NodeResult[Any]:
        """
        Run a single workflow step with error handling and observability.

        Args:
            workflow: LlamaIndex workflow instance
            step_name: Name of the step for logging/tracing
            input_data: Input data for the workflow step
            timeout: Optional timeout for the step

        Returns:
            NodeResult[Any]: Result with context, events, and error handling
        """
        from datetime import datetime

        from omnibase_core.core.monadic.model_node_result import (ErrorInfo,
                                                                  ErrorType,
                                                                  Event)

        start_time = datetime.now()

        try:
            # Run workflow step with optional timeout
            if timeout:
                result = await asyncio.wait_for(
                    workflow.run(**input_data), timeout=timeout
                )
            else:
                result = await workflow.run(**input_data)

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return NodeResult.success(
                value=result,
                provenance=[f"workflow.{step_name}"],
                trust_score=0.9,  # Workflows have slight uncertainty
                metadata={
                    "step_name": step_name,
                    "duration_ms": duration_ms,
                    "workflow_type": type(workflow).__name__,
                },
                events=[
                    Event(
                        type=f"workflow.step.{step_name}.completed",
                        payload={
                            "step_name": step_name,
                            "duration_ms": duration_ms,
                            "input_size": len(str(input_data)),
                            "output_size": len(str(result)),
                        },
                        timestamp=end_time,
                        source=f"workflow.{step_name}",
                    )
                ],
            )

        except asyncio.TimeoutError:
            error_info = ErrorInfo(
                error_type=ErrorType.TIMEOUT,
                message=f"Workflow step '{step_name}' timed out after {timeout}s",
                retryable=True,
                backoff_strategy="exponential",
                max_attempts=3,
            )

            return NodeResult.failure(
                error=error_info, provenance=[f"workflow.{step_name}.timeout"]
            )

        except Exception as e:
            error_info = ErrorInfo(
                error_type=ErrorType.PERMANENT,
                message=f"Workflow step '{step_name}' failed: {str(e)}",
                trace=str(e.__traceback__) if e.__traceback__ else None,
                retryable=False,
            )

            return NodeResult.failure(
                error=error_info, provenance=[f"workflow.{step_name}.failed"]
            )

    async def coordinate_workflow_sequence(
        self, workflow_steps: list, initial_data: Any
    ) -> NodeResult[Any]:
        """
        Coordinate a sequence of workflow steps with data flow.

        Args:
            workflow_steps: List of (workflow, step_name, transform_fn) tuples
            initial_data: Initial input data

        Returns:
            NodeResult[Any]: Final result after all steps complete
        """
        current_data = initial_data
        all_events = []
        combined_provenance = []
        combined_metadata = {}

        for workflow, step_name, transform_fn in workflow_steps:
            # Run workflow step
            step_result = await self.run_workflow_step(
                workflow, step_name, current_data
            )

            if step_result.is_failure:
                # Propagate failure with accumulated context
                step_result.events = all_events + step_result.events
                step_result.context.provenance = (
                    combined_provenance + step_result.context.provenance
                )
                return step_result

            # Transform data for next step
            if transform_fn:
                current_data = transform_fn(step_result.value)
            else:
                current_data = step_result.value

            # Accumulate context
            all_events.extend(step_result.events)
            combined_provenance.extend(step_result.context.provenance)
            combined_metadata.update(step_result.context.metadata)

        return NodeResult.success(
            value=current_data,
            provenance=combined_provenance,
            trust_score=0.8,  # Multi-step workflows have accumulated uncertainty
            metadata=combined_metadata,
            events=all_events,
        )
