"""Execution result data model."""

from pydantic import BaseModel, Field


class ModelExecutionResultData(BaseModel):
    """Strongly typed execution result data."""

    result: str | None = Field(default=None, description="Primary result value")
    status: str | None = Field(default=None, description="Execution status")
    message: str | None = Field(default=None, description="Result message")
    data: str | None = Field(default=None, description="Additional data")
    retryable: bool = Field(
        default=False,
        description="Whether operation can be retried",
    )
