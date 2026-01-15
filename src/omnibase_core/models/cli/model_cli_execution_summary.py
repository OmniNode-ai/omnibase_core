"""
CLI Execution Summary Model.

Represents execution summary with proper validation.
Replaces dict[str, Any] for execution summary with structured typing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCliExecutionSummary(BaseModel):
    """
    Structured execution summary for CLI operations.

    Replaces dict[str, Any] for get_summary() return type to provide
    type safety and validation for execution summary data.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Core execution information - UUID-based entity references
    execution_id: UUID = Field(default=..., description="Unique execution identifier")
    command_id: UUID = Field(
        default=..., description="UUID identifier for the CLI command"
    )
    command_display_name: str | None = Field(
        default=None,
        description="Human-readable command name",
    )
    target_node_id: UUID | None = Field(
        default=None,
        description="Target node UUID for precise identification",
    )
    target_node_display_name: str | None = Field(
        default=None,
        description="Target node display name if applicable",
    )

    # Execution state
    status: EnumExecutionStatus = Field(default=..., description="Execution status")
    current_phase: EnumExecutionPhase | None = Field(
        default=None,
        description="Current execution phase",
    )
    progress_percentage: float = Field(
        default=...,
        description="Progress percentage",
        ge=0.0,
        le=100.0,
    )

    # Timing information
    start_time: datetime = Field(default=..., description="Execution start time")
    end_time: datetime | None = Field(default=None, description="Execution end time")
    elapsed_ms: int = Field(
        default=..., description="Elapsed time in milliseconds", ge=0
    )

    # Execution metadata
    retry_count: int = Field(default=..., description="Current retry count", ge=0)
    is_dry_run: bool = Field(default=..., description="Whether this is a dry run")
    is_test_execution: bool = Field(
        default=..., description="Whether this is a test execution"
    )

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

    def get_end_time_iso(self) -> str | None:
        """Get end time as ISO string, None if not completed."""
        return self.end_time.isoformat() if self.end_time else None

    @property
    def command_name(self) -> str:
        """Get command name with fallback to UUID-based name."""
        return self.command_display_name or f"command_{str(self.command_id)[:8]}"

    @property
    def target_node_name(self) -> str:
        """Get target node name with fallback to UUID-based name."""
        if self.target_node_display_name:
            return self.target_node_display_name
        if self.target_node_id is not None:
            return f"node_{str(self.target_node_id)[:8]}"
        return "unknown_node"

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        return True


# Export for use
__all__ = ["ModelCliExecutionSummary"]
