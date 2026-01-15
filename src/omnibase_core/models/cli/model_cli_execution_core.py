"""
CLI Execution Core Model.

Core execution information for CLI commands.
Part of the ModelCliExecution restructuring to reduce excessive string fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.types.typed_dict_cli_execution_core_serialized import (
    TypedDictCliExecutionCoreSerialized,
)

from .model_cli_command_option import ModelCliCommandOption


class ModelCliExecutionCore(BaseModel):
    """
    Core CLI execution information.

    Contains essential execution identification, command info, and timing.
    Focused model without configuration or metadata clutter.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Execution identification
    execution_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique execution identifier",
    )

    # Command information
    command_name_id: UUID = Field(default=..., description="UUID for command name")
    command_display_name: str | None = Field(
        default=None,
        description="Human-readable command name",
    )
    command_args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    command_options: dict[str, ModelCliCommandOption] = Field(
        default_factory=dict,
        description="Command options and flags",
    )

    # Target information
    target_node_id: UUID | None = Field(
        default=None,
        description="Target node UUID for precise identification",
    )
    target_node_display_name: str | None = Field(
        default=None,
        description="Target node display name if applicable",
    )
    target_path: Path | None = Field(
        default=None,
        description="Target file or directory path",
    )

    # Execution state
    status: EnumExecutionStatus = Field(
        default=EnumExecutionStatus.PENDING,
        description="Execution status",
    )
    current_phase: EnumExecutionPhase | None = Field(
        default=None,
        description="Current execution phase",
    )

    # Timing information
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution start time",
    )
    end_time: datetime | None = Field(default=None, description="Execution end time")

    # Progress tracking
    progress_percentage: float = Field(
        default=0.0,
        description="Progress percentage",
        ge=0.0,
        le=100.0,
    )

    def get_command_name(self) -> str:
        """Get the command name."""
        return self.command_display_name or f"command_{str(self.command_name_id)[:8]}"

    def get_target_node_id(self) -> UUID | None:
        """Get the target node UUID."""
        return self.target_node_id

    def get_target_node_name(self) -> str | None:
        """Get the target node display name."""
        return self.target_node_display_name

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        delta = datetime.now(UTC) - self.start_time
        return int(delta.total_seconds() * 1000)

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.get_elapsed_ms() / 1000.0

    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.end_time is not None

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == EnumExecutionStatus.RUNNING and self.end_time is None

    def is_pending(self) -> bool:
        """Check if execution is pending."""
        return self.status == EnumExecutionStatus.PENDING

    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == EnumExecutionStatus.FAILED

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status in {
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.COMPLETED,
        }

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = EnumExecutionStatus.RUNNING
        self.start_time = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        self.end_time = datetime.now(UTC)
        if self.status == EnumExecutionStatus.RUNNING:
            self.status = EnumExecutionStatus.SUCCESS

    def mark_failed(self) -> None:
        """Mark execution as failed."""
        self.status = EnumExecutionStatus.FAILED
        self.end_time = datetime.now(UTC)

    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        self.status = EnumExecutionStatus.CANCELLED
        self.end_time = datetime.now(UTC)

    def set_phase(self, phase: EnumExecutionPhase) -> None:
        """Set current execution phase."""
        self.current_phase = phase

    def set_progress(self, percentage: float) -> None:
        """Set progress percentage."""
        self.progress_percentage = max(0.0, min(100.0, percentage))

    @classmethod
    def create_simple(
        cls,
        command_name: str,
        target_node_id: UUID | None = None,
        target_node_name: str | None = None,
    ) -> ModelCliExecutionCore:
        """Create a simple execution core."""
        import hashlib

        # Generate UUID from command name
        command_hash = hashlib.sha256(command_name.encode()).hexdigest()
        command_name_id = UUID(
            f"{command_hash[:8]}-{command_hash[8:12]}-{command_hash[12:16]}-{command_hash[16:20]}-{command_hash[20:32]}",
        )

        return cls(
            command_name_id=command_name_id,
            command_display_name=command_name,
            target_node_id=target_node_id,
            target_node_display_name=target_node_name,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    @allow_dict_any
    def serialize(self) -> TypedDictCliExecutionCoreSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)  # type: ignore[return-value]

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
__all__ = ["ModelCliExecutionCore"]
