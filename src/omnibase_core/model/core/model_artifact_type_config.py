"""
Artifact type configuration model.
"""

from pydantic import BaseModel

from omnibase_core.enums import ArtifactTypeEnum


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: ArtifactTypeEnum
    metadata_file: str | None = None
    version_pattern: str | None = None
