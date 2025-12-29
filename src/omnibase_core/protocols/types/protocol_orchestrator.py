"""
ProtocolOrchestrator - Protocol for orchestration nodes.

This module provides the protocol definition for nodes that implement
the ORCHESTRATOR pattern with workflow coordination capabilities.

OMN-662: Node Protocol Definitions for ONEX Four-Node Architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
    from omnibase_core.models.orchestrator.model_orchestrator_input import (
        ModelOrchestratorInput,
    )
    from omnibase_core.models.orchestrator.model_orchestrator_output import (
        ModelOrchestratorOutput,
    )
    from omnibase_core.models.state.model_workflow_state_snapshot import (
        ModelWorkflowStateSnapshot,
    )


@runtime_checkable
class ProtocolOrchestrator(Protocol):
    """
    Protocol for workflow orchestration nodes.

    Defines the interface for nodes that implement the ORCHESTRATOR pattern
    with workflow coordination, dependency resolution, and state management.

    ORCHESTRATOR nodes are:
    - Coordinators: Manage step execution order and dependencies
    - Pure: No side effects - emit Actions for deferred execution
    - Stateful: Track workflow progress and can snapshot/restore
    - Validatable: Can validate workflows before execution

    CRITICAL CONSTRAINT: Orchestrators CANNOT return typed results.
    They can only emit events and intents. Only COMPUTE nodes return
    typed results. This enforces separation between coordination
    (ORCHESTRATOR) and transformation (COMPUTE).

    Execution Modes:
    - SEQUENTIAL: Execute steps one at a time
    - PARALLEL: Execute independent steps concurrently
    - BATCH: Group steps into execution batches
    - CONDITIONAL: Execute based on branch conditions

    Architecture Note: No Contract-Based Entry Point

    Unlike ProtocolCompute (which has execute_compute()), orchestrators
    intentionally do NOT have an execute_orchestration() method. This
    asymmetry reflects a fundamental architectural difference:

    - COMPUTE nodes are **invoked**: They execute a single unit of work
      and return typed results. The execute_compute(contract) entry point
      is natural for this pattern - you call it with a contract and get
      back a result.

    - ORCHESTRATOR nodes are **reactive**: They coordinate workflows by
      responding to events, commands, and state transitions. Their behavior
      emerges from message flow and workflow state, not from executing a
      single contract. The process() method handles orchestration input
      but orchestrators fundamentally react to external stimuli rather
      than being invoked as callable operations.

    Adding execute_orchestration() would incorrectly imply orchestrators
    can be called like compute nodes to "execute an orchestration" as a
    discrete operation. This would:
    - Blur the architectural boundary between coordination and transformation
    - Suggest orchestrators produce typed results (they emit events/intents)
    - Encourage misuse as synchronous callable operations
    - Obscure the reactive, event-driven nature of workflow coordination

    The correct pattern for driving orchestration is to send events/commands
    to the orchestrator via process(), not to "execute" it via contract.

    Example:
        class MyOrchestrator:
            async def process(
                self,
                input_data: ModelOrchestratorInput,
            ) -> ModelOrchestratorOutput:
                # Coordinate workflow execution
                return ModelOrchestratorOutput(
                    execution_status="completed",
                    completed_steps=["step1", "step2"],
                    execution_time_ms=150,
                    actions_emitted=[...],
                )

        node: ProtocolOrchestrator = MyOrchestrator()  # Type-safe!
    """

    async def process(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Execute workflow orchestration.

        This is the core orchestration interface. Implementations must:
        - Accept ModelOrchestratorInput with workflow steps
        - Return ModelOrchestratorOutput with execution results
        - Emit ModelAction objects for deferred side effects
        - NOT return typed results (only events/intents)

        Args:
            input_data: Orchestrator input with workflow_id, steps,
                       execution_mode, and configuration.

        Returns:
            Orchestrator output with step results and emitted actions.

        Raises:
            ModelOnexError: If workflow validation fails, dependency cycles
                are detected, or step execution encounters an unrecoverable
                error.
        """
        ...

    async def validate_contract(self) -> list[str]:
        """
        Validate the workflow contract before execution.

        Checks contract configuration, step definitions, and
        dependency graphs for validity.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...

    async def validate_workflow_steps(
        self,
        steps: list[ModelWorkflowStep],
    ) -> list[str]:
        """
        Validate workflow steps for consistency and executability.

        Checks step references, dependency cycles, and configuration
        validity without requiring a full contract.

        Args:
            steps: List of workflow steps to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...

    def get_execution_order_for_steps(
        self,
        steps: list[ModelWorkflowStep],
    ) -> list[UUID]:
        """
        Get topological execution order for workflow steps.

        Computes execution order based on step dependencies.
        Respects depends_on relationships between steps.

        Args:
            steps: List of workflow steps with dependencies.

        Returns:
            List of step UUIDs in correct execution order.

        Raises:
            ModelOnexError: If workflow contains dependency cycles.
        """
        ...

    def snapshot_workflow_state(
        self,
        *,
        deep_copy: bool = False,
    ) -> ModelWorkflowStateSnapshot | None:
        """
        Export current workflow state for persistence.

        Creates a snapshot of workflow execution state suitable
        for serialization and later restoration.

        Args:
            deep_copy: If True, creates fully isolated copy (O(n)).
                      If False, returns reference (O(1), read-only).

        Returns:
            Workflow state snapshot, or None if no workflow active.
        """
        ...

    def restore_workflow_state(
        self,
        snapshot: ModelWorkflowStateSnapshot,
    ) -> None:
        """
        Restore workflow from persisted state.

        Validates snapshot compatibility and restores workflow
        execution state for replay or recovery.

        Args:
            snapshot: Previously captured workflow state.

        Raises:
            ModelOnexError: If snapshot validation fails.
        """
        ...

    def get_workflow_snapshot(
        self,
        *,
        deep_copy: bool = False,
    ) -> dict[str, object] | None:
        """
        Get workflow state as JSON-serializable dictionary.

        Returns workflow state in a format suitable for external
        APIs and storage backends.

        Args:
            deep_copy: If True, creates fully isolated copy.
                      If False, returns reference.

        Returns:
            Dictionary representation of workflow state, or None.
        """
        ...


__all__ = ["ProtocolOrchestrator"]
