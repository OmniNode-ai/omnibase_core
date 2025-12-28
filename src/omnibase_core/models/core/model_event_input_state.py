"""
Event Input State Model.

Type-safe model for input state in event metadata,
replacing Dict[str, Any] usage with proper model.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.workflow_constants import MAX_TIMEOUT_MS


class ModelEventInputState(BaseModel):
    """
    Type-safe input state for event metadata.

    Replaces Dict[str, Any] with structured model for better validation
    and type safety.
    """

    action: str | None = Field(default=None, description="Action being performed")
    parameters: dict[str, str | int | bool | float | list[str]] = Field(
        default_factory=dict,
        description="Action parameters",
    )
    node_version: ModelSemVer | None = Field(
        default=None,
        description="Node version for this input",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing",
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Execution timeout in milliseconds",
        ge=0,
        le=MAX_TIMEOUT_MS,  # Max 24 hours - prevents DoS via excessively long timeouts
    )

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default."""
        return self.parameters.get(key, default)
