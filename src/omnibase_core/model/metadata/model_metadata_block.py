"""
Model for metadata blocks used in file stamping.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from .model_function_discovery import ModelFunctionDiscovery
from .model_metadata_properties import ModelMetadataProperties


class ModelMetadataBlock(BaseModel):
    """Model representing a metadata block for file stamping."""

    block_type: str = Field("ONEX_METADATA", description="Type of metadata block")

    version: str = Field("1.0.0", description="Metadata block format version")

    node_name: str = Field(
        ..., description="Name of the node that created this metadata"
    )

    node_version: str = Field(
        ..., description="Version of the node that created this metadata"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this metadata was created"
    )

    updated_at: Optional[datetime] = Field(
        None, description="When this metadata was last updated"
    )

    file_hash: Optional[str] = Field(
        None, description="Hash of the file content when metadata was added"
    )

    hash_algorithm: Optional[str] = Field(
        None, description="Algorithm used for file hash"
    )

    tags: List[str] = Field(
        default_factory=list, description="Tags associated with this file"
    )

    properties: Optional[ModelMetadataProperties] = Field(
        None, description="Custom properties for this metadata block"
    )

    function_discovery: Optional[ModelFunctionDiscovery] = Field(
        None, description="Function discovery information if applicable"
    )

    dependencies: List[str] = Field(
        default_factory=list, description="Dependencies discovered in this file"
    )

    @validator("version")
    def validate_version(cls, v):
        """Ensure version follows semantic versioning."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must be in semantic versioning format (x.y.z)")
        return v

    @validator("updated_at")
    def validate_updated_at(cls, v, values):
        """Ensure updated_at is after created_at."""
        if v and "created_at" in values:
            if v < values["created_at"]:
                raise ValueError("updated_at must be after created_at")
        return v
