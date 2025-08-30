"""
Pydantic model for file stamp results.

Defines the structured result model for file stamping operations
within the ONEX architecture.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_base_result import ModelBaseResult


class ModelStampingDetails(BaseModel):
    """Details about file stamping operation."""

    files_processed: int = Field(..., description="Number of files processed")
    files_stamped: int = Field(..., description="Number of files successfully stamped")
    files_skipped: int = Field(..., description="Number of files skipped")
    files_found: List[str] = Field(
        default_factory=list, description="List of files found"
    )
    stamp_timestamp: str = Field(..., description="Timestamp when stamping occurred")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    errors: List[str] = Field(
        default_factory=list, description="List of errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of warnings encountered"
    )


class ModelFileStampResult(ModelBaseResult):
    """
    Structured result model for file stamping operations.

    Contains the results of stamping files with metadata
    within the ONEX architecture.
    """

    stamping_result: ModelStampingDetails = Field(
        ..., description="Detailed stamping results"
    )
    path: str = Field(..., description="Path that was processed")
    pattern: Optional[str] = Field(None, description="File pattern used")
    recursive: bool = Field(..., description="Whether processing was recursive")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    force: bool = Field(..., description="Whether force mode was used")
    execution_time_ms: Optional[float] = Field(
        None, description="Execution time in milliseconds"
    )
