"""Strongly typed discriminated union for different tool events."""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.model.hook_events.model_read_tool_event import (
    ModelBashToolEvent,
    ModelEditToolEvent,
    ModelGrepToolEvent,
    ModelReadToolEvent,
    ModelWriteToolEvent,
)


def get_tool_discriminator(v) -> str:
    """Discriminator function for tool events."""
    if isinstance(v, dict):
        return v.get("tool_name", "unknown").lower()
    return getattr(v, "tool_name", "unknown").lower()


# Strongly typed discriminated union using proper Pydantic pattern
class ModelToolEventContainer(BaseModel):
    """Container for different tool event types with proper discrimination."""

    read_event: ModelReadToolEvent | None = Field(
        None,
        description="Read tool event",
    )
    write_event: ModelWriteToolEvent | None = Field(
        None,
        description="Write tool event",
    )
    edit_event: ModelEditToolEvent | None = Field(
        None,
        description="Edit tool event",
    )
    bash_event: ModelBashToolEvent | None = Field(
        None,
        description="Bash tool event",
    )
    grep_event: ModelGrepToolEvent | None = Field(
        None,
        description="Grep tool event",
    )

    @model_validator(mode="after")
    def validate_exactly_one_event(self) -> "ModelToolEventContainer":
        """Ensure exactly one event type is set."""
        events = [
            self.read_event is not None,
            self.write_event is not None,
            self.edit_event is not None,
            self.bash_event is not None,
            self.grep_event is not None,
        ]

        if sum(events) != 1:
            raise ValueError("ModelToolEventContainer must have exactly one event set")

        return self

    def get_read_event(self) -> ModelReadToolEvent | None:
        """Get read tool event if set."""
        return self.read_event

    def get_write_event(self) -> ModelWriteToolEvent | None:
        """Get write tool event if set."""
        return self.write_event

    def get_edit_event(self) -> ModelEditToolEvent | None:
        """Get edit tool event if set."""
        return self.edit_event

    def get_bash_event(self) -> ModelBashToolEvent | None:
        """Get bash tool event if set."""
        return self.bash_event

    def get_grep_event(self) -> ModelGrepToolEvent | None:
        """Get grep tool event if set."""
        return self.grep_event


# Legacy alias for transition - use ModelToolEventContainer instead
ToolEventUnion = ModelToolEventContainer


class ModelToolPreExecutionEvent(BaseModel):
    """Event fired before tool execution with discriminated tool-specific data."""

    event_type: str = Field("pre-execution", description="Event type")
    tool_event: ModelToolEventContainer = Field(
        ...,
        description="Tool-specific event data",
    )


class ModelToolPostExecutionEvent(BaseModel):
    """Event fired after tool execution."""

    event_type: str = Field("post-execution", description="Event type")
    tool_name: str = Field(..., description="Name of the tool that executed")
    result: str = Field(..., description="Tool execution result")
    success: bool = Field(..., description="Whether execution succeeded")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    error_message: str | None = Field(None, description="Error message if failed")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: str = Field(..., description="Execution completion timestamp")
    hook_version: str = Field("1.0.0", description="Hook system version")
