"""
Declarative workflow step execution context model.

Context for a single step execution in declarative orchestration.
Follows ONEX one-model-per-file architecture.
"""

from datetime import datetime
from uuid import UUID

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep


class ModelDeclarativeWorkflowStepContext:
    """
    Context for a single step execution in declarative workflows.

    Distinct from ModelWorkflowStepExecution which is a Pydantic model
    for configuration-based step tracking.
    """

    def __init__(
        self,
        step: ModelWorkflowStep,
        workflow_id: UUID,
        completed_steps: set[UUID],
    ):
        """
        Initialize step execution context.

        Args:
            step: Step to execute
            workflow_id: Parent workflow ID
            completed_steps: Set of completed step IDs
        """
        self.step = step
        self.workflow_id = workflow_id
        self.completed_steps = completed_steps
        self.started_at = datetime.now()
        self.completed_at: datetime | None = None
        self.error: str | None = None


__all__ = ["ModelDeclarativeWorkflowStepContext"]
