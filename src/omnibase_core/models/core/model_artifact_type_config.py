"""
Artifact type configuration model.
"""

from pydantic import BaseModel

from omnibase_core.enums.enum_artifact_type import EnumArtifactType


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: EnumArtifactType
    metadata_file: str | None = None
    version_pattern: str | None = None
