"""Clean model for tool execution events."""

import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ModelToolExecutionEvent(BaseModel):
    """Clean, simple model for tool execution events.

    Uses JSON serialization for parameters to maintain type safety
    while avoiding complex Union types or generic dictionaries.
    """

    # Event metadata
    event_type: str = Field(..., description="pre-execution or post-execution")
    tool_name: str = Field(..., description="Name of the tool being executed")
    session_id: str = Field(..., description="Claude session identifier")
    conversation_id: str | None = Field(
        None,
        description="Correlated conversation ID",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    hook_version: str = Field("1.0.0", description="Hook system version")

    # Pre-execution data
    parameters_json: str | None = Field(
        None,
        description="JSON-serialized tool parameters for pre-execution events",
    )

    # Post-execution data
    result: str | None = Field(None, description="Tool execution result")
    success: bool | None = Field(None, description="Whether execution succeeded")
    duration_ms: int | None = Field(
        None,
        description="Execution duration in milliseconds",
    )
    error_message: str | None = Field(None, description="Error message if failed")
    error_type: str | None = Field(None, description="Type of error if failed")
    result_size_bytes: int | None = Field(None, description="Size of result data")

    # Claude Code additional fields
    claude_message: str | None = Field(None, description="Claude message content")
    error: str | None = Field(None, description="Error details from Claude Code")
    topic: str | None = Field(
        None,
        description="Event bus topic or similar routing info",
    )
    working_directory: str | None = Field(None, description="Working directory path")
    hook_type: str | None = Field(None, description="Hook type from Claude Code")

    @field_validator("parameters_json")
    @classmethod
    def validate_parameters_json(cls, v):
        """Validate that parameters_json is valid JSON if provided."""
        if v is not None:
            try:
                json.loads(v)
            except json.JSONDecodeError:
                msg = "parameters_json must be valid JSON"
                raise ValueError(msg)
        return v

    def get_parameters(self) -> dict:
        """Parse and return parameters as a dictionary."""
        if self.parameters_json:
            return json.loads(self.parameters_json)
        return {}

    def set_parameters(self, params: dict) -> None:
        """Set parameters from a dictionary."""
        self.parameters_json = json.dumps(params) if params else None
