"""
Event Input State Model.

Type-safe model for input state in event metadata,
replacing Dict[str, Any] usage with proper model.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_workflow_constants import (
    MAX_TIMEOUT_MS,
    MIN_TIMEOUT_MS,
)


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
    # v1.0.3 Fix 38: timeout_ms MUST be >= MIN_TIMEOUT_MS (100ms) per normative rules.
    # This prevents unrealistically short timeouts that would cause immediate failures.
    # MIN_TIMEOUT_MS (100ms) prevents busy-waiting scenarios where extremely short
    # timeouts would cause rapid retry loops consuming excessive CPU.
    #
    # TIMEOUT HIERARCHY (cross-reference):
    # - Event timeout: Capped at MAX_TIMEOUT_MS (24 hours) - this field
    #   Allows long-running event processing (batch jobs, ETL, ML training).
    #   Prevents DoS via extremely long timeouts that could exhaust resources.
    # - Step timeout: Capped at TIMEOUT_LONG_MS (5 min) - for individual workflow steps
    #   See: omnibase_core/models/contracts/model_workflow_step.py
    # - I/O operation timeout: Uses constants_timeouts.py (TIMEOUT_DEFAULT_MS, etc.)
    #   See: omnibase_core/constants/constants_timeouts.py
    timeout_ms: int | None = Field(
        default=None,
        description="Execution timeout in milliseconds (min: 100ms, max: 24 hours)",
        ge=MIN_TIMEOUT_MS,  # Min 100ms per v1.0.3 Fix 38 - prevents busy-waiting
        le=MAX_TIMEOUT_MS,  # Max 24 hours - prevents DoS via excessively long timeouts
    )

    def get_parameter(
        self, key: str, default: str | int | bool | float | list[str] | None = None
    ) -> str | int | bool | float | list[str] | None:
        """Get parameter value with default."""
        return self.parameters.get(key, default)
