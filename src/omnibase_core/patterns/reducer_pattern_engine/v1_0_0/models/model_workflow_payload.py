"""Workflow payload model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field


class ModelWorkflowPayload(BaseModel):
    """Common strongly typed workflow payload model."""

    content: str = Field("", description="Workflow content payload")
    content_type: str = Field("", description="Type of the content")
    parameters: str = Field("", description="Processing parameters")
