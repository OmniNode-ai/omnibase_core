"""Workflow payload model for Reducer Pattern Engine."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelWorkflowPayload(BaseModel):
    """Strongly typed workflow payload model."""

    content: str = Field("", description="Workflow content payload")
    content_type: str = Field("text", description="Type of the content")
    parameters: str = Field("", description="Processing parameters")

    # Document-specific fields
    document_id: Optional[UUID] = Field(
        None, description="Document UUID for document workflows"
    )
    title: Optional[str] = Field(None, description="Document or data title")

    # Analysis-specific fields
    data_source: Optional[str] = Field(
        None, description="Source of data for analysis workflows"
    )
    analysis_type: Optional[str] = Field(
        None, description="Type of analysis to perform"
    )

    # Report-specific fields
    report_format: Optional[str] = Field(
        None, description="Output format for report workflows"
    )
    template_id: Optional[UUID] = Field(
        None, description="Template UUID for report generation"
    )

    # Common fields
    priority: int = Field(
        1, description="Processing priority (1=highest, 5=lowest)", ge=1, le=5
    )
    timeout_seconds: int = Field(
        300, description="Processing timeout in seconds", ge=1, le=3600
    )
