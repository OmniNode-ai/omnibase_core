"""Output model for Infrastructure Reducer operations with enhanced tracking."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelInfrastructureReducerOutput(BaseModel):
    """Output model for Infrastructure Reducer operations with enhanced tracking."""

    success: bool = Field(..., description="Whether reduction operation succeeded")
    aggregated_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated result from all adapter inputs",
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
    execution_time_ms: int = Field(
        ...,
        description="Execution time in milliseconds",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID",
    )
    processed_adapters: int = Field(
        default=0,
        description="Number of adapters successfully processed",
    )
    failed_adapters: list[str] = Field(
        default_factory=list,
        description="List of adapter names that failed processing",
    )
