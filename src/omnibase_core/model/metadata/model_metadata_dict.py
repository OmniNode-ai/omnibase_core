"""
Model for metadata dictionary representation.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_function_discovery import ModelFunctionDiscovery
from .model_metadata_properties import ModelMetadataProperties


class ModelMetadataDict(BaseModel):
    """Model representing metadata as a dictionary structure for serialization."""

    node_name: str = Field(
        ...,
        description="Name of the node that created this metadata",
    )

    node_version: str = Field(
        ...,
        description="Version of the node that created this metadata",
    )

    block_type: str = Field(
        default="ONEX_METADATA",
        description="Type of metadata block",
    )

    version: str = Field(default="1.0.0", description="Metadata block format version")

    created_at: datetime | None = Field(
        None,
        description="When this metadata was created",
    )

    updated_at: datetime | None = Field(
        None,
        description="When this metadata was last updated",
    )

    file_hash: str | None = Field(
        None,
        description="Hash of the file content when metadata was added",
    )

    hash_algorithm: str | None = Field(
        None,
        description="Algorithm used for file hash",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with this file",
    )

    function_discovery: ModelFunctionDiscovery | None = Field(
        None,
        description="Function discovery information if applicable",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Dependencies discovered in this file",
    )

    additional_properties: ModelMetadataProperties | None = Field(
        None,
        description="Additional custom properties",
    )

    class Config:
        extra = "allow"  # Allow extra fields for compatibility
