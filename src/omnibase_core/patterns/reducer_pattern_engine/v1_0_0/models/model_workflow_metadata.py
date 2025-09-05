"""Workflow metadata model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field


class ModelWorkflowMetadata(BaseModel):
    """Common strongly typed workflow metadata model."""

    correlation_context: str = Field(
        "", description="Correlation context for the workflow"
    )
    processing_hints: str = Field("", description="Processing hints for the workflow")
    quality_requirements: str = Field(
        "", description="Quality requirements for processing"
    )
