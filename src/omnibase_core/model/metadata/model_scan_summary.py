"""
Model for directory scan summary information.
"""

from pydantic import BaseModel, Field


class ModelScanSummary(BaseModel):
    """Model representing directory scan summary statistics."""

    total_files: int = Field(..., description="Total number of files discovered")

    total_directories: int = Field(
        ...,
        description="Total number of directories scanned",
    )

    files_by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Count of files by type name",
    )

    scan_duration_ms: float = Field(
        ...,
        description="Time taken for scan in milliseconds",
    )

    errors_encountered: int = Field(
        default=0,
        description="Number of errors during scanning",
    )
