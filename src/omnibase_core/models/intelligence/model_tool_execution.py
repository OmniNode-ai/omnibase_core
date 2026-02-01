"""Tool execution model for intelligence pattern extraction.

Represents structured tool execution data for pattern extraction,
enabling analysis of tool usage, failures, and recovery patterns.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelToolExecution(BaseModel):
    """Structured tool execution data for pattern extraction.

    Represents a single tool invocation with its parameters, result,
    and timing information.

    Note: `timestamp` should come from recorded session data, not `now()`.
    For deterministic pattern extraction, timestamps must be stable across runs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identification
    tool_name: str = Field(..., description="Name of the tool executed")
    index: int = Field(..., ge=0, description="Order in execution sequence")

    # Parameters (flexible, JSON-serializable)
    tool_parameters: JsonType | None = Field(
        default=None,
        description="Tool parameters (JSON-serializable)",
    )

    # Result
    success: bool = Field(..., description="Whether tool execution succeeded")
    error_type: str | None = Field(
        default=None,
        description="Error type if failed (e.g., 'FileNotFoundError')",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )

    # Context
    file_path: str | None = Field(
        default=None,
        description="File path involved in execution (if applicable)",
    )

    # Timing
    timestamp: datetime | None = Field(
        default=None,
        description="When execution occurred (from recorded session data)",
    )
    duration_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Execution duration in milliseconds",
    )

    @property
    def directory(self) -> str | None:
        """Directory context derived from file_path.

        Returns parent directory of file_path if present, None otherwise.
        Computed property ensures consistency with file_path.
        """
        if self.file_path is None:
            return None
        return str(Path(self.file_path).parent)


__all__ = ["ModelToolExecution"]
