"""
Model for file statistics information.
"""

from typing import Dict

from pydantic import BaseModel, Field


class ModelFileStatistics(BaseModel):
    """Model representing detailed file statistics."""

    total_files: int = Field(..., description="Total number of files")

    total_size_bytes: int = Field(..., description="Total size of all files in bytes")

    average_size_bytes: float = Field(..., description="Average file size in bytes")

    largest_file_bytes: int = Field(..., description="Size of largest file in bytes")

    smallest_file_bytes: int = Field(..., description="Size of smallest file in bytes")

    extensions: Dict[str, int] = Field(
        default_factory=dict, description="Count of files by extension"
    )

    file_types: Dict[str, int] = Field(
        default_factory=dict, description="Count of files by type"
    )

    readable_files: int = Field(..., description="Number of readable files")

    writable_files: int = Field(..., description="Number of writable files")

    readable_percentage: float = Field(
        ..., description="Percentage of files that are readable"
    )

    writable_percentage: float = Field(
        ..., description="Percentage of files that are writable"
    )
