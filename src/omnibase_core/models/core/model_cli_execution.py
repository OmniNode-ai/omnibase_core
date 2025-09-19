"""
CLI Execution Model.

Represents CLI command execution context with timing, configuration,
and state tracking for comprehensive command execution management.
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_execution_status import EnumExecutionStatus
from ...enums.enum_output_format import EnumOutputFormat


class ModelCliExecution(BaseModel):
    """
    CLI execution context and state tracking.

    Captures all context for CLI command execution including timing,
    configuration, and execution state for comprehensive monitoring.
    """

    # Execution identification
    execution_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique execution identifier",
    )

    # Command information
    command_name: str = Field(..., description="Name of the CLI command")
    command_args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    command_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Command options and flags",
    )

    # Target information
    target_node_name: str | None = Field(
        default=None,
        description="Target node name if applicable",
    )
    target_path: str | None = Field(
        default=None,
        description="Target file or directory path",
    )

    # Execution context
    working_directory: str | None = Field(
        default=None,
        description="Working directory for execution",
    )
    environment_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )

    # Execution settings
    is_dry_run: bool = Field(default=False, description="Whether this is a dry run")
    is_test_execution: bool = Field(
        default=False,
        description="Whether this is a test execution",
    )
    is_debug_enabled: bool = Field(
        default=False,
        description="Whether debug mode is enabled",
    )
    is_trace_enabled: bool = Field(
        default=False,
        description="Whether tracing is enabled",
    )
    is_verbose: bool = Field(
        default=False,
        description="Whether verbose mode is enabled",
    )

    # Timing information
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution start time",
    )
    end_time: datetime | None = Field(default=None, description="Execution end time")

    # Execution state
    status: EnumExecutionStatus = Field(
        default=EnumExecutionStatus.PENDING, description="Execution status"
    )
    current_phase: str | None = Field(
        default=None,
        description="Current execution phase",
    )
    progress_percentage: float = Field(
        default=0.0,
        description="Progress percentage",
        ge=0.0,
        le=100.0,
    )

    # Resource limits and configuration
    timeout_seconds: int | None = Field(
        default=None,
        description="Execution timeout",
        ge=1,
    )
    max_memory_mb: int | None = Field(
        default=None,
        description="Memory limit in MB",
        ge=1,
    )
    max_retries: int = Field(default=0, description="Maximum retry attempts", ge=0)
    retry_count: int = Field(default=0, description="Current retry count", ge=0)

    # User and session information
    user_id: UUID | None = Field(default=None, description="User identifier")
    session_id: UUID | None = Field(default=None, description="Session identifier")

    # Input/output configuration
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for execution",
    )
    output_format: EnumOutputFormat = Field(
        default=EnumOutputFormat.TEXT, description="Expected output format"
    )
    capture_output: bool = Field(default=True, description="Whether to capture output")

    # Custom metadata for extensibility
    custom_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom execution context",
    )
    execution_tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing execution",
    )

    def get_command_name(self) -> str:
        """Get the command name."""
        return self.command_name

    def get_target_node_name(self) -> str | None:
        """Get the target node name."""
        return self.target_node_name

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

    def is_timed_out(self) -> bool:
        """Check if execution timed out."""
        if self.timeout_seconds is None:
            return False
        return self.get_elapsed_seconds() > self.timeout_seconds

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = EnumExecutionStatus.RUNNING
        self.start_time = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        self.end_time = datetime.now(UTC)
        if self.status == EnumExecutionStatus.RUNNING:
            self.status = EnumExecutionStatus.SUCCESS

    def mark_failed(self, reason: str | None = None) -> None:
        """Mark execution as failed."""
        self.status = EnumExecutionStatus.FAILED
        self.end_time = datetime.now(UTC)
        if reason:
            self.custom_context["failure_reason"] = reason

    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        self.status = EnumExecutionStatus.CANCELLED
        self.end_time = datetime.now(UTC)

    def set_phase(self, phase: str) -> None:
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

    def add_context(self, key: str, value: Any) -> None:
        """Add custom context data."""
        self.custom_context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get custom context data."""
        return self.custom_context.get(key, default)

    def add_input_data(self, key: str, value: Any) -> None:
        """Add input data."""
        self.input_data[key] = value

    def get_input_data(self, key: str, default: Any = None) -> Any:
        """Get input data."""
        return self.input_data.get(key, default)

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        return {
            "execution_id": self.execution_id,
            "command_name": self.command_name,
            "target_node_name": self.target_node_name,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_ms": self.get_elapsed_ms(),
            "retry_count": self.retry_count,
            "is_dry_run": self.is_dry_run,
            "is_test_execution": self.is_test_execution,
            "progress_percentage": self.progress_percentage,
            "current_phase": self.current_phase,
        }

    @classmethod
    def create_simple(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> "ModelCliExecution":
        """Create a simple execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
        )

    @classmethod
    def create_dry_run(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> "ModelCliExecution":
        """Create a dry run execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
            is_dry_run=True,
        )

    @classmethod
    def create_test_execution(
        cls,
        command_name: str,
        target_node_name: str | None = None,
    ) -> "ModelCliExecution":
        """Create a test execution context."""
        return cls(
            command_name=command_name,
            target_node_name=target_node_name,
            is_test_execution=True,
        )


# Export for use
__all__ = ["ModelCliExecution"]
