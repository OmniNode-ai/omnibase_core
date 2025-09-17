"""
Orchestrator Execution State Model

Simple execution state tracking for workflow orchestrator operations.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus


class ModelOrchestratorExecutionState(BaseModel):
    """
    Simple execution state for workflow orchestrator operations.

    This model provides basic execution state tracking for workflow
    orchestration operations by the WorkflowOrchestratorAgent.
    """

    scenario_id: str = Field(..., description="Unique scenario identifier")
    status: EnumWorkflowStatus = Field(..., description="Current workflow status")
    start_time: datetime = Field(..., description="Workflow start time")
    end_time: Optional[datetime] = Field(None, description="Workflow end time")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    operation_type: str = Field(..., description="Type of operation being orchestrated")
    current_step: int = Field(default=0, description="Current step number", ge=0)
    total_steps: int = Field(default=1, description="Total number of steps", ge=1)
    execution_time_ms: int = Field(
        default=0, description="Execution time in milliseconds", ge=0
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def get_progress_percentage(self) -> float:
        """Calculate progress as a percentage."""
        if self.total_steps == 0:
            return 0.0
        return min((self.current_step / self.total_steps) * 100.0, 100.0)

    def is_completed(self) -> bool:
        """Check if execution is completed (success or failure)."""
        return self.status in [
            EnumWorkflowStatus.COMPLETED,
            EnumWorkflowStatus.FAILED,
            EnumWorkflowStatus.CANCELLED,
        ]

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == EnumWorkflowStatus.RUNNING

    def mark_completed(self, end_time: Optional[datetime] = None) -> None:
        """Mark execution as completed."""
        self.status = EnumWorkflowStatus.COMPLETED
        self.end_time = end_time or datetime.now()
        if self.end_time and self.start_time:
            self.execution_time_ms = int(
                (self.end_time - self.start_time).total_seconds() * 1000
            )

    def mark_failed(
        self, error_message: str, end_time: Optional[datetime] = None
    ) -> None:
        """Mark execution as failed with error message."""
        self.status = EnumWorkflowStatus.FAILED
        self.error_message = error_message
        self.end_time = end_time or datetime.now()
        if self.end_time and self.start_time:
            self.execution_time_ms = int(
                (self.end_time - self.start_time).total_seconds() * 1000
            )
