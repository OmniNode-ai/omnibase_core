#!/usr/bin/env python3
"""
Canary Effect Output Model - Contract-Driven Implementation.

Strongly typed Pydantic model generated from ONEX contract output_state schema.
Eliminates JSON/YAML parsing architecture violations by using proper contract-driven models.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelCanaryEffectOutput(BaseModel):
    """
    Output model for canary effect operations - generated from contract output_state schema.

    This model represents the strongly-typed output structure for canary effect operations,
    replacing the previous architecture violation of using dict[str, Any] for operation results.
    All fields are properly typed according to the ONEX contract specification.

    Contract Reference:
        - Source: canary_effect_contract.yaml output_state
        - Node Type: EFFECT
        - Strong Typing: Enforced via Pydantic validation
        - Zero Any Types: All fields use specific types with proper validation
    """

    operation_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Result data from the effect operation - object type from contract",
    )

    success: bool = Field(
        True,
        description="Whether operation succeeded - boolean type from contract",
    )

    error_message: str | None = Field(
        None,
        description="Error message if operation failed - string type from contract",
    )

    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds - integer type from contract",
        ge=0,  # Must be non-negative
    )

    correlation_id: str | None = Field(
        None,
        description="Request correlation ID - string type from contract",
    )

    # Pydantic v2 configuration using ConfigDict
    model_config = ConfigDict(
        # Enable validation on assignment for runtime safety
        validate_assignment=True,
        # Forbid extra fields to maintain contract compliance
        extra="forbid",
        # Enable JSON schema generation
        json_schema_serialization_defaults_required=True,
    )

    @field_validator("execution_time_ms")
    @classmethod
    def validate_execution_time(cls, v: int | None) -> int | None:
        """Validate execution time is non-negative when provided."""
        if v is not None and v < 0:
            raise ValueError("execution_time_ms must be non-negative")
        return v

    def is_successful(self) -> bool:
        """
        Check if the operation was successful.

        Returns:
            bool: True if operation succeeded with no error, False otherwise
        """
        return self.success and self.error_message is None

    def has_execution_metrics(self) -> bool:
        """
        Check if execution timing metrics are available.

        Returns:
            bool: True if execution_time_ms is populated
        """
        return self.execution_time_ms is not None

    def get_result_summary(self) -> dict[str, Any]:
        """
        Get a summary of the operation result for logging/monitoring.

        Returns:
            Dict[str, Any]: Summary containing key metrics and status
        """
        return {
            "success": self.success,
            "has_error": self.error_message is not None,
            "execution_time_ms": self.execution_time_ms,
            "result_present": bool(self.operation_result),
            "result_size": (
                len(str(self.operation_result)) if self.operation_result else 0
            ),
            "correlation_id": self.correlation_id,
        }
