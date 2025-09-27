"""
Result Summary Model.

Restrictive model for CLI execution result summary
with proper typing and validation.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ModelResultSummary(BaseModel):
    """Restrictive model for result summary."""

    execution_id: UUID = Field(description="Execution identifier")
    command: str = Field(description="Command name")
    target_node: str | None = Field(description="Target node name")
    success: bool = Field(description="Whether execution succeeded")
    exit_code: int = Field(description="Exit code")
    duration_ms: float = Field(description="Duration in milliseconds")
    retry_count: int = Field(description="Number of retries")
    has_errors: bool = Field(description="Whether there are errors")
    has_warnings: bool = Field(description="Whether there are warnings")
    error_count: int = Field(description="Number of errors")
    warning_count: int = Field(description="Number of warnings")
    critical_error_count: int = Field(description="Number of critical errors")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
