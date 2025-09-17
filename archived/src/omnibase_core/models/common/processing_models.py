"""
Common processing models for use across all ONEX services.

These models provide strongly typed data structures that can be reused
across different services and components.
"""

from pydantic import BaseModel


class ModelProcessingResult(BaseModel):
    """Common strongly typed processing result model."""

    success: bool
    data: str = ""
    status_code: str = ""
    message: str = ""


class ModelProcessingError(BaseModel):
    """Common strongly typed processing error model."""

    error_code: str
    error_message: str
    error_context: str = ""


class ModelWorkflowPayload(BaseModel):
    """Common strongly typed workflow payload model."""

    content: str = ""
    content_type: str = ""
    parameters: str = ""


class ModelWorkflowMetadata(BaseModel):
    """Common strongly typed workflow metadata model."""

    correlation_context: str = ""
    processing_hints: str = ""
    quality_requirements: str = ""
