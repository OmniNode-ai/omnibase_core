"""
Artifact type configuration model.
"""

from typing import Optional

from pydantic import BaseModel

from omnibase_core.enums import ArtifactTypeEnum


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: ArtifactTypeEnum
    metadata_file: Optional[str] = None
    version_pattern: Optional[str] = None
