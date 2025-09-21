"""
CLI Execution Summary Model.

Represents execution summary with proper validation.
Replaces dict[str, Any] for execution summary with structured typing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_execution_phase import EnumExecutionPhase
from ...enums.enum_execution_status import EnumExecutionStatus
from ...utils.uuid_helpers import uuid_from_string


class ModelCliExecutionSummary(BaseModel):
    """
    Structured execution summary for CLI operations.

    Replaces dict[str, Any] for get_summary() return type to provide
    type safety and validation for execution summary data.
    """

    # Core execution information - UUID-based entity references
    execution_id: UUID = Field(..., description="Unique execution identifier")
    command_id: UUID = Field(..., description="UUID identifier for the CLI command")
    command_display_name: str | None = Field(None, description="Human-readable command name")
    target_node_id: Optional[UUID] = Field(
        default=None, description="Target node UUID for precise identification"
    )
    target_node_display_name: Optional[str] = Field(
        default=None, description="Target node display name if applicable"
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

    @property
    def command_name(self) -> str:
        """Get command name with fallback to UUID-based name."""
        return self.command_display_name or f"command_{str(self.command_id)[:8]}"

    @command_name.setter
    def command_name(self, value: str) -> None:
        """Set command name (for backward compatibility)."""
        self.command_display_name = value
        # Update command_id to be deterministic based on name
        self.command_id = uuid_from_string(value, "command")

    @property
    def target_node_name(self) -> str | None:
        """Get target node name with fallback to UUID-based name."""
        if self.target_node_id is None:
            return None
        return self.target_node_display_name or f"node_{str(self.target_node_id)[:8]}"

    @target_node_name.setter
    def target_node_name(self, value: str | None) -> None:
        """Set target node name (for backward compatibility)."""
        self.target_node_display_name = value
        if value:
            # Update target_node_id to be deterministic based on name
            self.target_node_id = uuid_from_string(value, "node")


# Export for use
__all__ = ["ModelCliExecutionSummary"]
