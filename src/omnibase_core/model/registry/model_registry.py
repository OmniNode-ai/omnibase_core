"""Registry models for artifact management and discovery."""

from pydantic import BaseModel

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.protocol.protocol_registry import (
    ModelRegistryArtifactMetadata,
    RegistryArtifactType,
)


class ModelRegistryArtifactInfo(BaseModel):
    """Information about a registry artifact."""

    name: str
    version: str
    artifact_type: RegistryArtifactType
    path: str
    metadata: ModelRegistryArtifactMetadata
    is_wip: bool = False


class ModelRegistryStatus(BaseModel):
    """Status information for registry operations."""

    status: EnumOnexStatus
    message: str
    artifact_count: int
    valid_artifact_count: int
    invalid_artifact_count: int
    wip_artifact_count: int
    artifact_types_found: list[RegistryArtifactType]


# Rebuild models to handle forward references
ModelRegistryArtifactInfo.model_rebuild()
ModelRegistryStatus.model_rebuild()
