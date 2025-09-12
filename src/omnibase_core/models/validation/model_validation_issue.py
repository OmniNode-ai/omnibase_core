"""
ValidationIssue model.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_severity import ModelSeverity

from .model_validation_metadata import ModelValidationMetadata


class ModelValidationIssue(BaseModel):
    """Individual validation issue"""

    issue_id: UUID = Field(default_factory=uuid4, description="Unique issue identifier")
    severity: ModelSeverity = Field(..., description="Issue severity level")
    message: str = Field(..., description="Human-readable issue description")
    source_location: str | None = Field(
        None,
        description="Location where issue was found",
    )
    suggestion: str | None = Field(None, description="Suggested fix for the issue")
    metadata: ModelValidationMetadata | None = Field(
        None,
        description="Additional issue metadata",
    )
