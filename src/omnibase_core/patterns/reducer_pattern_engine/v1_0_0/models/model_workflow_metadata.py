"""Workflow metadata model for Reducer Pattern Engine."""

from typing import Optional

from pydantic import BaseModel, Field


class ModelWorkflowMetadata(BaseModel):
    """Strongly typed workflow metadata model."""

    correlation_context: str = Field(
        "", description="Correlation context for the workflow"
    )
    processing_hints: str = Field("", description="Processing hints for the workflow")
    quality_requirements: str = Field(
        "", description="Quality requirements for processing"
    )

    # Execution metadata
    retry_count: int = Field(0, description="Number of retries attempted", ge=0, le=5)
    max_retries: int = Field(3, description="Maximum retries allowed", ge=0, le=10)

    # Source tracking
    source_system: Optional[str] = Field(
        None, description="Source system that initiated the workflow"
    )
    user_context: Optional[str] = Field(
        None, description="User context for the workflow"
    )

    # Processing preferences
    async_processing: bool = Field(
        True, description="Whether to process asynchronously"
    )
    notify_on_completion: bool = Field(
        False, description="Whether to send completion notifications"
    )
