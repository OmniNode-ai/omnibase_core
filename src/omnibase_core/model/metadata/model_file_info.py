"""
Model for file information used by metadata tools.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, validator

from .model_file_type import ModelFileType
from .model_metadata_properties import ModelMetadataProperties


class ModelFileInfo(BaseModel):
    """Model representing file information and metadata."""

    file_path: str = Field(..., description="Absolute path to the file")

    file_name: str = Field(..., description="Name of the file including extension")

    file_extension: str = Field(..., description="File extension (including the dot)")

    file_size: int = Field(..., description="File size in bytes")

    file_type: ModelFileType = Field(..., description="Detected file type information")

    created_at: datetime | None = Field(None, description="File creation timestamp")

    modified_at: datetime | None = Field(
        None,
        description="File last modification timestamp",
    )

    content_hash: str | None = Field(None, description="Hash of file content")

    has_metadata_block: bool = Field(
        False,
        description="Whether file contains existing metadata block",
    )

    metadata_location: str | None = Field(
        None,
        description="Location of metadata block if present (line numbers, etc.)",
    )

    is_readable: bool = Field(True, description="Whether the file is readable")

    is_writable: bool = Field(True, description="Whether the file is writable")

    encoding: str | None = Field(
        None,
        description="Detected or assumed text encoding",
    )

    line_count: int | None = Field(None, description="Number of lines in the file")

    properties: ModelMetadataProperties | None = Field(
        None,
        description="Additional file properties",
    )

    @validator("file_path")
    def validate_file_path(self, v):
        """Ensure file path is absolute."""
        path = Path(v)
        if not path.is_absolute():
            msg = "file_path must be absolute"
            raise ValueError(msg)
        return str(path)

    @validator("file_name")
    def validate_file_name(self, v, values):
        """Ensure file_name matches the path."""
        if "file_path" in values:
            expected_name = Path(values["file_path"]).name
            if v != expected_name:
                msg = f"file_name '{v}' does not match path '{expected_name}'"
                raise ValueError(
                    msg,
                )
        return v

    @validator("file_extension")
    def validate_file_extension(self, v, values):
        """Ensure file_extension matches the path."""
        if "file_path" in values:
            expected_ext = Path(values["file_path"]).suffix
            if v != expected_ext:
                msg = f"file_extension '{v}' does not match path '{expected_ext}'"
                raise ValueError(
                    msg,
                )
        return v
