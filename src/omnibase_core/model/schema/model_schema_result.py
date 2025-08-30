"""
Schema Result Model.

Structured model for schema operation results that replaces Dict[str, Any] usage.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.schema.enum_schema_types import (
    EnumSchemaOperationType, EnumSchemaStatus)
from omnibase_core.model.schema.model_schema_issue import ModelSchemaIssue


class ModelSchemaResult(BaseModel):
    """
    Structured schema result model.

    Replaces Dict[str, Any] usage with proper typing for
    schema operation results.
    """

    # Core result information
    operation_type: EnumSchemaOperationType = Field(
        ..., description="Type of schema operation performed"
    )
    status: EnumSchemaStatus = Field(..., description="Overall operation status")
    success: bool = Field(..., description="Whether operation was successful")

    # Result details
    schemas_processed: int = Field(default=0, description="Number of schemas processed")
    models_generated: int = Field(default=0, description="Number of models generated")
    files_created: List[Path] = Field(
        default_factory=list, description="Files created during operation"
    )

    # Issues and validation
    issues: List[ModelSchemaIssue] = Field(
        default_factory=list, description="Issues found during operation"
    )
    warnings_count: int = Field(default=0, description="Number of warnings")
    errors_count: int = Field(default=0, description="Number of errors")

    # Metadata
    duration_ms: Optional[int] = Field(
        None, description="Operation duration in milliseconds"
    )
    summary: str = Field(..., description="Human-readable operation summary")

    # Schema evolution specific
    version_from: Optional[str] = Field(None, description="Source schema version")
    version_to: Optional[str] = Field(None, description="Target schema version")
    breaking_changes: List[str] = Field(
        default_factory=list, description="Breaking changes detected"
    )
