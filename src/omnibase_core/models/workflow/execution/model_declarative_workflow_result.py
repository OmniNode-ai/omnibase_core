"""
Declarative workflow execution result model.

Result of declarative workflow execution from workflow_executor utilities.
Follows ONEX one-model-per-file architecture.

Strict typing is enforced - no Any types in implementation.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_workflow_execution import EnumWorkflowState
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Declarative workflow result metadata field requires dict[str, Any] "
    "for flexible workflow-specific execution context and tracking data."
)
class ModelDeclarativeWorkflowResult:
    """
    Result of declarative workflow execution.

    Pure data structure containing workflow outcome and emitted actions
    for declarative orchestration workflows.

    Distinct from ModelWorkflowExecutionResult which is used for
    coordination-based workflow tracking.
    """

    def __init__(
        self,
        workflow_id: UUID,
        execution_status: EnumWorkflowState,
        completed_steps: list[str],
        failed_steps: list[str],
        actions_emitted: list[ModelAction],
        execution_time_ms: int,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize declarative workflow execution result.

        Args:
            workflow_id: Unique workflow execution ID
            execution_status: Final workflow status
            completed_steps: List of completed step IDs
            failed_steps: List of failed step IDs
            actions_emitted: List of actions emitted during execution
            execution_time_ms: Execution time in milliseconds
            metadata: Optional execution metadata
        """
        self.workflow_id = workflow_id
        self.execution_status = execution_status
        self.completed_steps = completed_steps
        self.failed_steps = failed_steps
        self.actions_emitted = actions_emitted
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now(UTC).isoformat()


__all__ = ["ModelDeclarativeWorkflowResult"]
