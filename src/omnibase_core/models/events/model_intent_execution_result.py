"""
Intent execution result model.

This module defines the result event published by intent executors
after attempting to execute an intent.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelIntentExecutionResult(BaseModel):
    """
    Result of executing an intent.

    Published by intent executor after successful/failed execution.

    Attributes:
        intent_id: Reference to original intent
        correlation_id: Correlation ID from intent
        executed_at: When intent was executed (UTC)
        success: Whether execution succeeded
        error_message: Error message if failed
        execution_duration_ms: How long execution took
    """

    model_config = ConfigDict(extra="forbid")

    intent_id: UUID = Field(
        ...,
        description="Reference to original intent ID",
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID from original intent",
    )
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When intent was executed (UTC)",
    )
    success: bool = Field(
        ...,
        description="Whether execution succeeded",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )
    execution_duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="How long execution took in milliseconds",
    )
