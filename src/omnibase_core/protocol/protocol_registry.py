# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.276226'
# description: Stamped by ToolPython
# entrypoint: python://protocol_registry
# hash: a08694d4a43c239f7653f23bcaf0645dcc77cc1b8afeeaec3f1bceecfafc579b
# last_modified_at: '2025-05-29T14:14:00.324643+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_registry.py
# namespace: python://omnibase.protocol.protocol_registry
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 8664087b-f756-490a-914c-4bb9c21cac98
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Shared Registry Protocol.

Provides a cross-cutting interface for registry functionality without exposing
node-specific implementation details. This protocol abstracts registry operations
to enable testing and cross-node registry access while maintaining proper
architectural boundaries.
"""

from enum import Enum
from typing import List, Optional, Protocol

from pydantic import BaseModel, field_validator

from omnibase_core.enums.enum_onex_status import EnumOnexStatus


class RegistryArtifactType(str, Enum):
    """Shared enumeration of registry artifact types."""

    NODES = "nodes"
    CLI_TOOLS = "cli_tools"
    RUNTIMES = "runtimes"
    ADAPTERS = "adapters"
    CONTRACTS = "contracts"
    PACKAGES = "packages"


class RegistryArtifactModelMetadata(BaseModel):
    # Canonical fields for artifact metadata; extend as needed
    description: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    last_modified_at: Optional[str] = None
    # Add more fields as needed for protocol

    @field_validator("author", mode="before")
    @classmethod
    def set_author_default(cls, v):
        if v is None or not isinstance(v, str) or not v.strip():
            return "Unknown"
        return v

    @field_validator("description", mode="before")
    @classmethod
    def set_description_default(cls, v):
        if v is None or not isinstance(v, str) or not v.strip():
            return "No description"
        return v

    def model_post_init(self, __context):
        if (
            self.author is None
            or not isinstance(self.author, str)
            or not self.author.strip()
        ):
            object.__setattr__(self, "author", "Unknown")
        if (
            self.description is None
            or not isinstance(self.description, str)
            or not self.description.strip()
        ):
            object.__setattr__(self, "description", "No description")


class RegistryArtifactInfo(BaseModel):
    name: str
    version: str
    artifact_type: RegistryArtifactType
    path: str
    metadata: RegistryArtifactModelMetadata
    is_wip: bool = False


class RegistryStatus(BaseModel):
    status: EnumOnexStatus
    message: str
    artifact_count: int
    valid_artifact_count: int
    invalid_artifact_count: int
    wip_artifact_count: int
    artifact_types_found: List[RegistryArtifactType]


class ProtocolRegistry(Protocol):
    """
    Cross-cutting registry protocol.

    Provides an interface for registry operations that can be implemented
    by different registry backends (registry loader node, mock registries, etc.)
    without exposing implementation-specific details.
    """

    def get_status(self) -> RegistryStatus:
        """Get registry loading status and statistics."""
        ...

    def get_artifacts(self) -> List[RegistryArtifactInfo]:
        """Get all artifacts in the registry."""
        ...

    def get_artifacts_by_type(
        self, artifact_type: RegistryArtifactType
    ) -> List[RegistryArtifactInfo]:
        """Get artifacts filtered by type."""
        ...

    def get_artifact_by_name(
        self, name: str, artifact_type: Optional[RegistryArtifactType] = None
    ) -> RegistryArtifactInfo:
        """
        Get a specific artifact by name.

        Args:
            name: Artifact name to search for
            artifact_type: Optional type filter

        Returns:
            RegistryArtifactInfo: The found artifact

        Raises:
            OnexError: If artifact is not found
        """
        ...

    def has_artifact(
        self, name: str, artifact_type: Optional[RegistryArtifactType] = None
    ) -> bool:
        """Check if an artifact exists in the registry."""
        ...


RegistryArtifactModelMetadata.model_rebuild()
RegistryArtifactInfo.model_rebuild()
RegistryStatus.model_rebuild()
