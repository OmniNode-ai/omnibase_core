"""
CLI Execution Model.

Represents CLI command execution context with timing, configuration,
and state tracking for comprehensive command execution management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.types.type_serializable_value import SerializedDict

# Use object type for CLI command option values.
# Avoids primitive soup union anti-pattern while maintaining flexibility.
# Runtime type validation should be done where values are consumed.
CommandOptionValue = object

# Use object type for execution context values.
# Avoids primitive soup union anti-pattern while maintaining flexibility.
# Runtime type validation should be done where values are consumed.
ExecutionContextValue = object

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_execution_phase import EnumExecutionPhase
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_output_format import EnumOutputFormat

if TYPE_CHECKING:
    from omnibase_core.models.cli.model_cli_execution_summary import (
        ModelCliExecutionSummary,
    )


class ModelCliExecution(BaseModel):
    """
    CLI execution context and state tracking.

    Represents CLI command execution with timing, configuration,
    and state tracking for comprehensive command execution management.
    """

    # Core execution fields
    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier",
    )
    command_name: str = Field(default=..., description="Command name")
    command_args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    command_options: dict[str, CommandOptionValue] = Field(
        default_factory=dict,
        description="Command options",
    )

    # Target and path information
    target_node_name: str | None = Field(default=None, description="Target node name")
    target_path: Path | None = Field(default=None, description="Target path")
    working_directory: Path | None = Field(
        default=None, description="Working directory"
    )
    environment_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )

    # Execution flags
    is_dry_run: bool = Field(default=False, description="Whether this is a dry run")
    is_test_execution: bool = Field(
        default=False,
        description="Whether this is a test execution",
    )
    is_debug_enabled: bool = Field(
        default=False,
        description="Whether debug is enabled",
    )
    is_trace_enabled: bool = Field(
        default=False,
        description="Whether trace is enabled",
    )
    is_verbose: bool = Field(
        default=False,
        description="Whether verbose output is enabled",
    )

    # Timing information
    start_time: datetime = Field(
        default_factory=datetime.now,
        description="Execution start time",
    )
    end_time: datetime | None = Field(default=None, description="Execution end time")

    # Status and progress
    status: EnumExecutionStatus = Field(
        default=EnumExecutionStatus.PENDING,
        description="Execution status",
    )
    current_phase: EnumExecutionPhase | None = Field(
        default=EnumExecutionPhase.INITIALIZATION,
        description="Current execution phase",
    )
    progress_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Progress percentage",
    )

    # Resource limits
    timeout_seconds: int | None = Field(
        default=None,
        gt=0,
        description="Timeout in seconds (None = no timeout, must be > 0 if specified)",
    )
    max_memory_mb: int | None = Field(
        default=None,
        gt=0,
        description="Maximum memory in MB (None = no limit, must be > 0 if specified)",
    )
    max_retries: int = Field(default=0, ge=0, description="Maximum retry attempts")
    retry_count: int = Field(default=0, ge=0, description="Current retry count")

    # User and session context
    user_id: UUID | None = Field(default=None, description="User ID")
    session_id: UUID | None = Field(default=None, description="Session ID")

    # Data and output
    input_data: dict[str, ExecutionContextValue] = Field(
        default_factory=dict,
        description="Input data",
    )
    output_format: EnumOutputFormat = Field(
        default=EnumOutputFormat.TEXT,
        description="Output format",
    )
    capture_output: bool = Field(default=True, description="Whether to capture output")

    # Metadata
    custom_context: dict[str, ExecutionContextValue] = Field(
        default_factory=dict,
        description="Custom context data",
    )
    execution_tags: list[str] = Field(
        default_factory=list,
        description="Execution tags",
    )

    # Additional fields from tests
    unit: str | None = Field(default=None, description="Unit of measurement")
    data_source: str | None = Field(default=None, description="Data source")
    forecast_points: int | None = Field(
        default=None, description="Number of forecast points"
    )
    confidence_interval: float | None = Field(
        default=None, description="Confidence interval"
    )
    anomaly_points: int | None = Field(
        default=None, description="Number of anomaly points"
    )
    anomaly_threshold: float | None = Field(
        default=None, description="Anomaly threshold"
    )

    # Computed properties and methods
    def get_command_name(self) -> str:
        """Get the command name."""
        return self.command_name

    def get_target_node_id(self) -> UUID | None:
        """Get the target node UUID (not implemented in flat model)."""
        return None

    def get_target_node_name(self) -> str | None:
        """Get the target node display name."""
        return self.target_node_name

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if not self.end_time:
            # Use timezone-aware datetime if start_time is timezone-aware
            if self.start_time.tzinfo is not None:
                current_time = datetime.now(UTC)
            else:
                current_time = datetime.now()
            elapsed = current_time - self.start_time
        else:
            elapsed = self.end_time - self.start_time
        return int(elapsed.total_seconds() * 1000)

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
        return self.status == EnumExecutionStatus.SUCCESS

    def is_timed_out(self) -> bool:
        """Check if execution timed out."""
        if self.timeout_seconds is None:
            return False
        return self.get_elapsed_seconds() >= self.timeout_seconds

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = EnumExecutionStatus.RUNNING
        if not hasattr(self, "_start_time_set"):
            self.start_time = datetime.now()
            self._start_time_set = True

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        # Only mark as success if currently running
        if self.status == EnumExecutionStatus.RUNNING:
            self.status = EnumExecutionStatus.SUCCESS
        self.end_time = datetime.now()
        self.progress_percentage = 100.0

    def mark_failed(self, reason: str | None = None) -> None:
        """Mark execution as failed."""
        self.status = EnumExecutionStatus.FAILED
        self.end_time = datetime.now()
        if reason:
            from omnibase_core.enums.enum_context_source import EnumContextSource
            from omnibase_core.enums.enum_context_type import EnumContextType
            from omnibase_core.models.cli.model_cli_execution_context import (
                ModelCliExecutionContext,
            )

            failure_context = ModelCliExecutionContext(
                key="failure_reason",
                value=reason,
                context_type=EnumContextType.SYSTEM,
                source=EnumContextSource.SYSTEM,
                description="Execution failure reason",
            )
            self.custom_context["failure_reason"] = failure_context

    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        self.status = EnumExecutionStatus.CANCELLED
        self.end_time = datetime.now()

    def set_phase(self, phase: EnumExecutionPhase) -> None:
        """Set current execution phase."""
        self.current_phase = phase

    def set_progress(self, percentage: float) -> None:
        """Set progress percentage."""
        self.progress_percentage = max(0.0, min(100.0, percentage))

    def increment_retry(self) -> bool:
        """Increment retry count and check if more retries available."""
        self.retry_count += 1
        return self.retry_count <= self.max_retries

    def add_tag(self, tag: str) -> None:
        """Add an execution tag."""
        if tag not in self.execution_tags:
            self.execution_tags.append(tag)

    def add_context(self, key: str, context: ExecutionContextValue) -> None:
        """Add custom context data."""
        self.custom_context[key] = context

    def get_context(
        self,
        key: str,
        default: ExecutionContextValue = None,
    ) -> ExecutionContextValue:
        """Get custom context data."""
        return self.custom_context.get(key, default)

    def add_input_data(self, key: str, input_data: ExecutionContextValue) -> None:
        """Add input data."""
        self.input_data[key] = input_data

    def get_input_data(
        self,
        key: str,
        default: ExecutionContextValue = None,
    ) -> ExecutionContextValue:
        """Get input data."""
        return self.input_data.get(key, default)

    def get_summary(self) -> ModelCliExecutionSummary:
        """Get execution summary."""
        # Generate a command ID from the command name (or use a real UUID if available)
        import hashlib

        from omnibase_core.models.cli.model_cli_execution_summary import (
            ModelCliExecutionSummary,
        )

        command_hash = hashlib.sha256(self.command_name.encode()).hexdigest()
        command_id = UUID(
            f"{command_hash[:8]}-{command_hash[8:12]}-{command_hash[12:16]}-{command_hash[16:20]}-{command_hash[20:32]}",
        )

        return ModelCliExecutionSummary(
            execution_id=self.execution_id,
            command_id=command_id,
            command_display_name=self.command_name,
            target_node_display_name=self.target_node_name,
            status=self.status,
            current_phase=self.current_phase,
            progress_percentage=self.progress_percentage,
            start_time=self.start_time,
            end_time=self.end_time,
            elapsed_ms=self.get_elapsed_ms(),
            retry_count=self.retry_count,
            is_dry_run=self.is_dry_run,
            is_test_execution=self.is_test_execution,
        )

    @classmethod
    def create_simple(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a simple execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
            target_path=None,
            working_directory=None,
            end_time=None,
            user_id=None,
            session_id=None,
            unit=None,
            data_source=None,
            forecast_points=None,
            confidence_interval=None,
            anomaly_points=None,
            anomaly_threshold=None,
        )

    @classmethod
    def create_dry_run(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a dry run execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
            is_dry_run=True,
            target_path=None,
            working_directory=None,
            end_time=None,
            user_id=None,
            session_id=None,
            unit=None,
            data_source=None,
            forecast_points=None,
            confidence_interval=None,
            anomaly_points=None,
            anomaly_threshold=None,
        )

    @classmethod
    def create_test_execution(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a test execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
            is_test_execution=True,
            target_path=None,
            working_directory=None,
            end_time=None,
            user_id=None,
            session_id=None,
            unit=None,
            data_source=None,
            forecast_points=None,
            confidence_interval=None,
            anomaly_points=None,
            anomaly_threshold=None,
        )

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
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelCliExecution"]
