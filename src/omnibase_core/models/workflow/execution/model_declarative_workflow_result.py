"""
Declarative workflow execution result model.

Result of declarative workflow execution from workflow_executor utilities.
Follows ONEX one-model-per-file architecture.

Strict typing is enforced - no Any types in implementation.
"""

from datetime import UTC, datetime
from uuid import UUID

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.workflow.execution.model_workflow_result_metadata import (
    ModelWorkflowResultMetadata,
)


class ModelDeclarativeWorkflowResult:
    """
    Result of declarative workflow execution.

    Pure data structure containing workflow outcome and emitted actions
    for declarative orchestration workflows.

    Distinct from ModelWorkflowExecutionResult which is used for
    coordination-based workflow tracking.

    Note:
        This is intentionally a plain Python class rather than a Pydantic model
        because:

        1. **Mutability required**: ``execution_time_ms`` and ``timestamp`` are set
           after the object is created (during workflow execution completion).
        2. **Type safety via composition**: All type-sensitive data is encapsulated
           in ``ModelWorkflowResultMetadata``, which IS a frozen Pydantic model
           with full validation.
        3. **Internal use only**: This is a simple data container for internal
           workflow executor use, not exposed in public APIs.
        4. **Performance**: Avoids Pydantic validation overhead for high-frequency
           workflow result creation.

        For type safety, class-level type annotations are provided below for
        IDE support and static type checking.

    Frozen Metadata Pattern:
        The ``metadata`` attribute holds a ``ModelWorkflowResultMetadata`` instance
        which is frozen (immutable). To update metadata fields after creation, use
        ``model_copy(update={...})`` to create a new frozen instance::

            # Correct: Replace metadata with a new frozen instance
            if result.metadata is not None:
                result.metadata = result.metadata.model_copy(
                    update={"workflow_hash": computed_hash}
                )

        This pattern provides thread-safety for the metadata while allowing the
        result container to be updated as needed during workflow execution.
    """

    # Class-level type annotations for IDE support and static type checking
    workflow_id: UUID
    execution_status: EnumWorkflowStatus
    completed_steps: list[str]
    failed_steps: list[str]
    skipped_steps: list[str]
    actions_emitted: list[ModelAction]
    execution_time_ms: int
    metadata: ModelWorkflowResultMetadata | None
    timestamp: str

    def __init__(
        self,
        workflow_id: UUID,
        execution_status: EnumWorkflowStatus,
        completed_steps: list[str],
        failed_steps: list[str],
        actions_emitted: list[ModelAction],
        execution_time_ms: int,
        metadata: ModelWorkflowResultMetadata | None = None,
        skipped_steps: list[str] | None = None,
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
            metadata: Optional typed execution metadata
            skipped_steps: List of skipped step IDs (disabled steps).
                Per v1.0.1 Fix 17, steps with enabled=False are tracked
                in skipped_steps, not completed_steps or failed_steps.
        """
        self.workflow_id = workflow_id
        self.execution_status = execution_status
        self.completed_steps = completed_steps
        self.failed_steps = failed_steps
        self.skipped_steps = skipped_steps if skipped_steps is not None else []
        self.actions_emitted = actions_emitted
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata
        self.timestamp = datetime.now(UTC).isoformat()


__all__ = ["ModelDeclarativeWorkflowResult"]
