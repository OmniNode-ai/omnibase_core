"""
Event Output State Model.

Type-safe model for output state in event metadata,
replacing Dict[str, Any] usage with proper model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelEventOutputState(BaseModel):
    """
    Type-safe output state for event metadata.

    Replaces Dict[str, Any] with structured model for better validation
    and type safety.
    """

    status: str = Field(
        ...,
        description="Execution status",
        pattern="^(success|failure|timeout|cancelled|pending)$",
    )
    message: str | None = Field(None, description="Status message")
    data: dict[str, str | int | bool | float | list[str]] = Field(
        default_factory=dict,
        description="Output data",
    )
    execution_time_ms: float | None = Field(
        None,
        description="Execution time in milliseconds",
        ge=0,
    )
    exit_code: int | None = Field(
        None,
        description="Process exit code",
        ge=0,
        le=255,
    )

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data value with default."""
        return self.data.get(key, default)
