"""
Artifact type configuration model.
"""

from typing import Literal

from pydantic import BaseModel


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: Literal["TOOL", "VALIDATOR", "AGENT", "MODEL", "PLUGIN", "SCHEMA", "CONFIG"]
    metadata_file: str | None = None
    version_pattern: str | None = None
