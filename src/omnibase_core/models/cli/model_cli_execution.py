"""
CLI Execution Model.

Represents CLI command execution context with timing, configuration,
and state tracking for comprehensive command execution management.

Restructured to use composition of focused sub-models instead of
excessive string fields in a single large model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_execution_phase import EnumExecutionPhase
from ...enums.enum_execution_status import EnumExecutionStatus
from .model_cli_execution_config import ModelCliExecutionConfig
from .model_cli_execution_context import ModelCliExecutionContext
from .model_cli_execution_core import ModelCliExecutionCore
from .model_cli_execution_input_data import ModelCliExecutionInputData
from .model_cli_execution_metadata import ModelCliExecutionMetadata
from .model_cli_execution_resources import ModelCliExecutionResources
from .model_cli_execution_summary import ModelCliExecutionSummary


class ModelCliExecution(BaseModel):
    """
    CLI execution context and state tracking.

    Restructured to use composition of focused sub-models:
    - core: Essential execution information and timing
    - config: Configuration settings and parameters
    - resources: Resource limits and user context
    - metadata: Tags and custom context data
    """

    # Composed sub-models for focused concerns
    core: ModelCliExecutionCore = Field(
        default_factory=ModelCliExecutionCore,
        description="Core execution information",
    )
    config: ModelCliExecutionConfig = Field(
        default_factory=ModelCliExecutionConfig,
        description="Execution configuration",
    )
    resources: ModelCliExecutionResources = Field(
        default_factory=ModelCliExecutionResources,
        description="Resource limits and constraints",
    )
    metadata: ModelCliExecutionMetadata = Field(
        default_factory=ModelCliExecutionMetadata,
        description="Metadata and custom context",
    )

    # Backward compatibility properties
    @property
    def execution_id(self) -> UUID:
        """Get execution ID from core."""
        return self.core.execution_id

    @property
    def command_name(self) -> str:
        """Get command name from core."""
        return self.core.command_name

    @property
    def status(self) -> EnumExecutionStatus:
        """Get status from core."""
        return self.core.status

    @property
    def start_time(self) -> datetime:
        """Get start time from core."""
        return self.core.start_time

    @property
    def end_time(self) -> datetime | None:
        """Get end time from core."""
        return self.core.end_time

    @property
    def is_dry_run(self) -> bool:
        """Get dry run flag from config."""
        return self.config.is_dry_run

    # Delegate methods to appropriate sub-models
    def get_command_name(self) -> str:
        """Get the command name."""
        return self.core.get_command_name()

    def get_target_node_id(self) -> UUID | None:
        """Get the target node UUID."""
        return self.core.get_target_node_id()

    def get_target_node_name(self) -> str | None:
        """Get the target node display name."""
        return self.core.get_target_node_name()

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        return self.core.get_elapsed_ms()

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.core.get_elapsed_seconds()

    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.core.is_completed()

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.core.is_running()

    def is_pending(self) -> bool:
        """Check if execution is pending."""
        return self.core.is_pending()

    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.core.is_failed()

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.core.is_successful()

    def is_timed_out(self) -> bool:
        """Check if execution timed out."""
        return self.resources.is_timed_out(self.get_elapsed_seconds())

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.core.mark_started()

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        self.core.mark_completed()

    def mark_failed(self, reason: str | None = None) -> None:
        """Mark execution as failed."""
        self.core.mark_failed()
        if reason:
            self.metadata.add_failure_reason(reason)

    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        self.core.mark_cancelled()

    def set_phase(self, phase: EnumExecutionPhase) -> None:
        """Set current execution phase."""
        self.core.set_phase(phase)

    def set_progress(self, percentage: float) -> None:
        """Set progress percentage."""
        self.core.set_progress(percentage)

    def increment_retry(self) -> bool:
        """Increment retry count and check if more retries available."""
        return self.resources.increment_retry()

    def add_tag(self, tag: str) -> None:
        """Add an execution tag."""
        self.metadata.add_tag(tag)

    def add_context(self, key: str, context: ModelCliExecutionContext) -> None:
        """Add custom context data."""
        self.metadata.add_context(key, context)

    def get_context(
        self, key: str, default: ModelCliExecutionContext | None = None
    ) -> ModelCliExecutionContext | None:
        """Get custom context data."""
        return self.metadata.get_context(key, default)

    def add_input_data(self, key: str, input_data: ModelCliExecutionInputData) -> None:
        """Add input data."""
        self.config.add_input_data(key, input_data)

    def get_input_data(
        self, key: str, default: ModelCliExecutionInputData | None = None
    ) -> ModelCliExecutionInputData | None:
        """Get input data."""
        return self.config.get_input_data(key, default)

    def get_summary(self) -> ModelCliExecutionSummary:
        """Get execution summary."""
        return ModelCliExecutionSummary(
            execution_id=self.execution_id,
            command_name=self.command_name,
            target_node_id=self.get_target_node_id(),
            target_node_name=self.get_target_node_name(),
            status=self.status,
            start_time=self.start_time,
            end_time=self.end_time,
            elapsed_ms=self.get_elapsed_ms(),
            retry_count=self.resources.retry_count,
            is_dry_run=self.is_dry_run,
            is_test_execution=self.config.is_test_execution,
            progress_percentage=self.core.progress_percentage,
            current_phase=self.core.current_phase,
        )

    @classmethod
    def create_simple(
        cls,
        command_name: str,
        target_node_id: UUID | None = None,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a simple execution context."""
        core = ModelCliExecutionCore.create_simple(command_name, target_node_id, target_node_name)
        return cls(core=core)

    @classmethod
    def create_dry_run(
        cls,
        command_name: str,
        target_node_id: UUID | None = None,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a dry run execution context."""
        core = ModelCliExecutionCore.create_simple(command_name, target_node_id, target_node_name)
        config = ModelCliExecutionConfig(is_dry_run=True)
        return cls(core=core, config=config)

    @classmethod
    def create_test_execution(
        cls,
        command_name: str,
        target_node_id: UUID | None = None,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create a test execution context."""
        core = ModelCliExecutionCore.create_simple(command_name, target_node_id, target_node_name)
        config = ModelCliExecutionConfig.create_test()
        return cls(core=core, config=config)

    @classmethod
    def create_with_config(
        cls,
        command_name: str,
        config: ModelCliExecutionConfig | None = None,
        resources: ModelCliExecutionResources | None = None,
        metadata: ModelCliExecutionMetadata | None = None,
        target_node_id: UUID | None = None,
        target_node_name: str | None = None,
    ) -> ModelCliExecution:
        """Create execution with custom configuration."""
        core = ModelCliExecutionCore.create_simple(command_name, target_node_id, target_node_name)
        return cls(
            core=core,
            config=config or ModelCliExecutionConfig(),
            resources=resources or ModelCliExecutionResources(),
            metadata=metadata or ModelCliExecutionMetadata(),
        )


# Export for use
__all__ = ["ModelCliExecution"]
