"""
Artifact type configuration model.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from ...enums.enum_artifact_type import EnumArtifactType


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: EnumArtifactType = Field(
        ...,
        description="Strongly typed artifact type",
    )

    metadata_file: Path | None = Field(
        None,
        description="Path to metadata file for this artifact type",
    )

    version_pattern: str | None = Field(
        None,
        description="Version pattern for artifact naming/validation",
    )
