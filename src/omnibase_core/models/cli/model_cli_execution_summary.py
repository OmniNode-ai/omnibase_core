"""
CLI Execution Summary Model.

Represents execution summary with proper validation.
Replaces dict[str, Any] for execution summary with structured typing.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_execution_phase import EnumExecutionPhase
from ...enums.enum_execution_status import EnumExecutionStatus


class ModelCliExecutionSummary(BaseModel):
    """
    Structured execution summary for CLI operations.

    Replaces dict[str, Any] for get_summary() return type to provide
    type safety and validation for execution summary data.
    """

    # Core execution information
    execution_id: UUID = Field(..., description="Unique execution identifier")
    command_name: str = Field(..., description="Name of the CLI command")
    target_node_name: Optional[str] = Field(
        default=None, description="Target node name if applicable"
    )

    # Execution state
    status: EnumExecutionStatus = Field(..., description="Execution status")
    current_phase: Optional[EnumExecutionPhase] = Field(
        default=None, description="Current execution phase"
    )
    progress_percentage: float = Field(
        ..., description="Progress percentage", ge=0.0, le=100.0
    )

    # Timing information
    start_time: datetime = Field(..., description="Execution start time")
    end_time: Optional[datetime] = Field(default=None, description="Execution end time")
    elapsed_ms: int = Field(..., description="Elapsed time in milliseconds", ge=0)

    # Execution metadata
    retry_count: int = Field(..., description="Current retry count", ge=0)
    is_dry_run: bool = Field(..., description="Whether this is a dry run")
    is_test_execution: bool = Field(..., description="Whether this is a test execution")

    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.end_time is not None

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == EnumExecutionStatus.RUNNING and self.end_time is None

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status in {
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.COMPLETED,
        }

    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == EnumExecutionStatus.FAILED

    def get_duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return self.elapsed_ms / 1000.0

    def get_start_time_iso(self) -> str:
        """Get start time as ISO string."""
        return self.start_time.isoformat()

    def get_end_time_iso(self) -> Optional[str]:
        """Get end time as ISO string, None if not completed."""
        return self.end_time.isoformat() if self.end_time else None


# Export for use
__all__ = ["ModelCliExecutionSummary"]
