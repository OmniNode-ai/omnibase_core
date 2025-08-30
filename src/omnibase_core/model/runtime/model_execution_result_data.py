"""Execution result data model."""

from typing import Optional

from pydantic import BaseModel, Field


class ModelExecutionResultData(BaseModel):
    """Strongly typed execution result data."""

    result: Optional[str] = Field(default=None, description="Primary result value")
    status: Optional[str] = Field(default=None, description="Execution status")
    message: Optional[str] = Field(default=None, description="Result message")
    data: Optional[str] = Field(default=None, description="Additional data")
    retryable: bool = Field(
        default=False, description="Whether operation can be retried"
    )
