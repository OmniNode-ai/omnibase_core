"""Discriminated union for different tool events."""

from typing import Union

from pydantic import BaseModel, Discriminator, Field

from omnibase_core.model.hook_events.model_read_tool_event import (
    ModelBashToolEvent, ModelEditToolEvent, ModelGrepToolEvent,
    ModelReadToolEvent, ModelWriteToolEvent)


def get_tool_discriminator(v) -> str:
    """Discriminator function for tool events."""
    if isinstance(v, dict):
        return v.get("tool_name", "unknown").lower()
    return getattr(v, "tool_name", "unknown").lower()


# Discriminated union of all tool events
ToolEventUnion = Union[
    ModelReadToolEvent,
    ModelWriteToolEvent,
    ModelEditToolEvent,
    ModelBashToolEvent,
    ModelGrepToolEvent,
]


class ModelToolPreExecutionEvent(BaseModel):
    """Event fired before tool execution with discriminated tool-specific data."""

    event_type: str = Field("pre-execution", description="Event type")
    tool_event: ToolEventUnion = Field(
        ..., discriminator=Discriminator(get_tool_discriminator)
    )


class ModelToolPostExecutionEvent(BaseModel):
    """Event fired after tool execution."""

    event_type: str = Field("post-execution", description="Event type")
    tool_name: str = Field(..., description="Name of the tool that executed")
    result: str = Field(..., description="Tool execution result")
    success: bool = Field(..., description="Whether execution succeeded")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    error_message: str = Field(None, description="Error message if failed")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str = Field(None, description="Correlated conversation ID")
    timestamp: str = Field(..., description="Execution completion timestamp")
    hook_version: str = Field("1.0.0", description="Hook system version")
