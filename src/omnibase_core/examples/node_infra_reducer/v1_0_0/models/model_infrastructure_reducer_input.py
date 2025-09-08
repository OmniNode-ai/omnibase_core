"""Input model for Infrastructure Reducer operations with enhanced validation."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModelInfrastructureReducerInput(BaseModel):
    """Input model for Infrastructure Reducer operations with enhanced validation."""

    operation_type: str = Field(
        ...,
        description="Type of reduction operation to perform",
    )
    adapter_results: list[dict[str, Any]] = Field(
        ...,
        description="Results from infrastructure adapters to aggregate",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracking the operation",
    )
    timeout_ms: int | None = Field(
        None,
        description="Operation timeout in milliseconds",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Operation priority (1-10)",
    )

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v: str) -> str:
        """Validate operation type against allowed values."""
        allowed_types = {
            "aggregate_health",
            "aggregate_metrics",
            "aggregate_bootstrap",
            "aggregate_failover",
            "aggregate_status",
        }
        if v not in allowed_types:
            raise ValueError(f"Invalid operation_type. Must be one of: {allowed_types}")
        return v

    # UUID correlation_id doesn't need validation - Pydantic handles UUID format automatically

    @field_validator("adapter_results")
    @classmethod
    def validate_adapter_results(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate adapter results structure."""
        if not v:
            raise ValueError("adapter_results cannot be empty")

        for result in v:
            if "status" not in result:
                raise ValueError("Each adapter result must include 'status' field")
        return v
