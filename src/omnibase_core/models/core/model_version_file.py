"""
Version File Model - Tier 3 Metadata.

Pydantic model for file references within a version implementation.
"""

from pydantic import BaseModel, Field


class ModelVersionFile(BaseModel):
    """File reference within a version implementation."""

    file_path: str = Field(description="Relative path to file within version directory")
    file_type: str = Field(
        description="File type (contract, model, protocol, test, etc.)",
    )
    required: bool = Field(default=True, description="Whether file is required")
    description: str = Field(description="File purpose and contents")
    checksum: str | None = Field(
        default=None,
        description="File checksum for integrity verification",
    )
