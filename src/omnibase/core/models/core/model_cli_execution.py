"""
CLI Execution Model

Complete CLI command execution model that tracks all aspects
of command execution from start to finish.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase.model.core.model_cli_command_definition import ModelCliCommandDefinition
from omnibase.model.core.model_execution_context import ModelExecutionContext
from omnibase.model.core.model_node_reference import ModelNodeReference
from omnibase.model.core.model_parsed_arguments import ModelParsedArguments
from omnibase.model.core.model_schema_value import ModelSchemaValue


class ModelExecutionMetadata(BaseModel):
    """Execution metadata for CLI commands."""

    # Command metadata
    command_source: Optional[str] = Field(
        None, description="Source of command (user, script, api)"
    )
    command_version: Optional[str] = Field(
        None, description="Version of CLI interface used"
    )
    command_group: Optional[str] = Field(None, description="Command group/category")

    # Execution environment
    host_name: Optional[str] = Field(None, description="Host executing the command")
    process_id: Optional[int] = Field(None, description="Process ID of execution")
    thread_id: Optional[str] = Field(None, description="Thread ID of execution")

    # Performance tracking
    queue_time_ms: Optional[int] = Field(
        None, description="Time spent in queue before execution"
    )
    init_time_ms: Optional[int] = Field(None, description="Initialization time")
    validation_time_ms: Optional[int] = Field(
        None, description="Argument validation time"
    )

    # Resource usage
    memory_usage_mb: Optional[float] = Field(
        None, description="Peak memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        None, description="Average CPU usage percentage"
    )

    # Error tracking
    error_count: int = Field(0, description="Number of errors encountered")
    warning_count: int = Field(0, description="Number of warnings encountered")
    retry_count: int = Field(0, description="Number of retries performed")

    # Feature flags
    features_enabled: List[str] = Field(
        default_factory=list, description="Enabled feature flags"
    )
    features_disabled: List[str] = Field(
        default_factory=list, description="Disabled feature flags"
    )

    # Custom tags for filtering/grouping
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")

    # Extensibility for command-specific data
    custom_metrics: Optional[Dict[str, float]] = Field(
        None, description="Command-specific metrics"
    )
    custom_properties: Optional[Dict[str, str]] = Field(
        None, description="Command-specific properties"
    )


class ModelCliExecution(BaseModel):
    """
    Complete CLI command execution model.

    This model tracks all aspects of CLI command execution including
    command definition, arguments, context, and execution metadata.
    """

    execution_id: UUID = Field(
        default_factory=uuid4, description="Unique execution identifier"
    )

    command_definition: ModelCliCommandDefinition = Field(
        ..., description="Command being executed"
    )

    parsed_arguments: ModelParsedArguments = Field(
        ..., description="Parsed and validated arguments"
    )

    execution_context: ModelExecutionContext = Field(
        ..., description="Execution environment and settings"
    )

    target_node: ModelNodeReference = Field(
        ..., description="Node that will execute the command"
    )

    start_time: datetime = Field(
        default_factory=datetime.utcnow, description="Execution start timestamp"
    )

    end_time: Optional[datetime] = Field(None, description="Execution end timestamp")

    correlation_id: UUID = Field(
        default_factory=uuid4, description="Correlation ID for distributed tracing"
    )

    parent_execution_id: Optional[UUID] = Field(
        None, description="Parent execution ID for nested commands"
    )

    user_id: Optional[str] = Field(
        None, description="User ID for audit and permissions"
    )

    session_id: Optional[str] = Field(
        None, description="Session ID for tracking related commands"
    )

    source_location: Optional[str] = Field(
        None, description="Source location (CLI, API, script, etc.)"
    )

    execution_metadata: ModelExecutionMetadata = Field(
        default_factory=ModelExecutionMetadata, description="Execution metadata"
    )

    is_dry_run: bool = Field(
        default=False, description="Whether this is a dry run execution"
    )

    is_test_execution: bool = Field(
        default=False, description="Whether this is a test execution"
    )

    priority: int = Field(
        default=50,
        description="Execution priority (0-100, higher = more important)",
        ge=0,
        le=100,
    )

    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.end_time is None

    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.end_time is not None

    def get_duration_ms(self) -> Optional[int]:
        """Get execution duration in milliseconds."""
        if self.end_time is None:
            return None
        return int((self.end_time - self.start_time).total_seconds() * 1000)

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds (ongoing or completed)."""
        end_time = self.end_time or datetime.utcnow()
        return int((end_time - self.start_time).total_seconds() * 1000)

    def mark_completed(self) -> None:
        """Mark execution as completed."""
        if self.end_time is None:
            self.end_time = datetime.utcnow()

    def add_metadata(self, key: str, value: ModelSchemaValue) -> None:
        """Add execution metadata."""
        # Use setattr for known fields or add to custom properties
        if hasattr(self.execution_metadata, key):
            setattr(self.execution_metadata, key, value.to_value())
        else:
            if self.execution_metadata.custom_properties is None:
                self.execution_metadata.custom_properties = {}
            self.execution_metadata.custom_properties[key] = str(value.to_value())

    def get_metadata(
        self, key: str, default: Optional[ModelSchemaValue] = None
    ) -> Optional[ModelSchemaValue]:
        """Get execution metadata."""
        # Check known fields first
        if hasattr(self.execution_metadata, key):
            value = getattr(self.execution_metadata, key, None)
            if value is not None:
                return ModelSchemaValue.from_value(value)
        # Check custom properties
        if self.execution_metadata.custom_properties:
            value = self.execution_metadata.custom_properties.get(key)
            if value is not None:
                return ModelSchemaValue.from_value(value)
        return default

    def get_command_name(self) -> str:
        """Get the command name."""
        return self.command_definition.command_name

    def get_target_node_name(self) -> str:
        """Get the target node name."""
        return self.target_node.node_name

    def get_action_name(self) -> str:
        """Get the action name."""
        return self.command_definition.action

    def is_high_priority(self) -> bool:
        """Check if this is a high priority execution."""
        return self.priority >= 80

    def is_low_priority(self) -> bool:
        """Check if this is a low priority execution."""
        return self.priority <= 20

    def has_parent(self) -> bool:
        """Check if this execution has a parent."""
        return self.parent_execution_id is not None

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.execution_context.debug_enabled

    def is_trace_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self.execution_context.trace_enabled

    def get_timeout_ms(self) -> int:
        """Get execution timeout in milliseconds."""
        return self.execution_context.get_timeout_ms()

    def should_retry_on_failure(self) -> bool:
        """Check if retries are enabled on failure."""
        return self.execution_context.should_retry()

    def to_execution_dict(self) -> dict:
        """Convert to dictionary for node execution."""
        # Get the base execution dictionary from parsed arguments
        execution_dict = self.parsed_arguments.to_execution_dict()

        # Add execution context information
        execution_dict.update(
            {
                "execution_id": str(self.execution_id),
                "correlation_id": str(self.correlation_id),
                "start_time": self.start_time.isoformat(),
                "user_id": self.user_id,
                "session_id": self.session_id,
                "is_dry_run": self.is_dry_run,
                "is_test_execution": self.is_test_execution,
                "priority": self.priority,
                "debug_enabled": self.is_debug_enabled(),
                "trace_enabled": self.is_trace_enabled(),
                "timeout_ms": self.get_timeout_ms(),
                "retry_attempts": self.execution_context.retry_attempts,
            }
        )

        # Add environment variables from execution context
        execution_dict.update(self.execution_context.to_environment_dict())

        # Add execution metadata (excluding None values)
        metadata_dict = self.execution_metadata.dict(exclude_none=True)
        execution_dict.update(metadata_dict)

        return execution_dict

    def get_summary(self) -> dict:
        """Get execution summary for logging/monitoring."""
        return {
            "execution_id": str(self.execution_id),
            "command": self.get_command_name(),
            "target_node": self.get_target_node_name(),
            "action": self.get_action_name(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.get_duration_ms(),
            "elapsed_ms": self.get_elapsed_ms(),
            "status": "completed" if self.is_completed() else "running",
            "is_dry_run": self.is_dry_run,
            "is_test": self.is_test_execution,
            "priority": self.priority,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "correlation_id": str(self.correlation_id),
            "parent_execution_id": (
                str(self.parent_execution_id) if self.parent_execution_id else None
            ),
            "execution_mode": self.execution_context.execution_mode.value,
            "environment": self.execution_context.environment.name,
            "debug_enabled": self.is_debug_enabled(),
            "trace_enabled": self.is_trace_enabled(),
        }

    @classmethod
    def create_for_command(
        cls,
        command_definition: ModelCliCommandDefinition,
        parsed_arguments: ModelParsedArguments,
        execution_context: ModelExecutionContext,
        target_node: ModelNodeReference,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_execution_id: Optional[UUID] = None,
        **kwargs,
    ) -> "ModelCliExecution":
        """Create execution for a specific command."""
        return cls(
            command_definition=command_definition,
            parsed_arguments=parsed_arguments,
            execution_context=execution_context,
            target_node=target_node,
            user_id=user_id,
            session_id=session_id,
            parent_execution_id=parent_execution_id,
            **kwargs,
        )

    @classmethod
    def create_test_execution(
        cls,
        command_definition: ModelCliCommandDefinition,
        parsed_arguments: ModelParsedArguments,
        execution_context: ModelExecutionContext,
        target_node: ModelNodeReference,
    ) -> "ModelCliExecution":
        """Create a test execution."""
        return cls(
            command_definition=command_definition,
            parsed_arguments=parsed_arguments,
            execution_context=execution_context,
            target_node=target_node,
            is_test_execution=True,
            source_location="test",
            priority=10,  # Low priority for test executions
        )

    @classmethod
    def create_dry_run(
        cls,
        command_definition: ModelCliCommandDefinition,
        parsed_arguments: ModelParsedArguments,
        execution_context: ModelExecutionContext,
        target_node: ModelNodeReference,
    ) -> "ModelCliExecution":
        """Create a dry run execution."""
        # Create a modified execution context for dry run
        dry_run_context = execution_context.create_child_context(dry_run=True)

        return cls(
            command_definition=command_definition,
            parsed_arguments=parsed_arguments,
            execution_context=dry_run_context,
            target_node=target_node,
            is_dry_run=True,
            source_location="cli_dry_run",
        )
