"""
Node Core Model.

Core node identification and basic information.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_complexity_level import EnumComplexityLevel
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.utils.uuid_utilities import uuid_from_string


class ModelNodeCore(BaseModel):
    """
    Core node identification and basic information.

    Focused on fundamental node identity and basic properties.
    """

    # Core node info - UUID-based entity references
    node_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "node"),
        description="Unique identifier for the node",
    )
    node_display_name: str | None = Field(None, description="Human-readable node name")
    description: str | None = Field(None, description="Node description")
    node_type: EnumNodeType = Field(
        default=EnumNodeType.UNKNOWN,
        description="Type of node",
    )
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: EnumComplexityLevel = Field(
        default=EnumComplexityLevel.MEDIUM,
        description="Node complexity level",
    )
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Node version",
    )

    @property
    def node_name(self) -> str | None:
        """Get node name with fallback."""
        return self.node_display_name

    @property
    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == EnumMetadataNodeStatus.ACTIVE

    @property
    def is_deprecated(self) -> bool:
        """Check if node is deprecated."""
        return self.status == EnumMetadataNodeStatus.DEPRECATED

    @property
    def is_disabled(self) -> bool:
        """Check if node is disabled."""
        return self.status == EnumMetadataNodeStatus.DISABLED

    @property
    def is_simple(self) -> bool:
        """Check if node has simple complexity."""
        return self.complexity == EnumComplexityLevel.SIMPLE

    @property
    def is_complex(self) -> bool:
        """Check if node has high or critical complexity."""
        return self.complexity in [
            EnumComplexityLevel.HIGH,
            EnumComplexityLevel.CRITICAL,
        ]

    @property
    def version_string(self) -> str:
        """Get version as string."""
        return str(self.version)

    def update_status(self, status: EnumMetadataNodeStatus) -> None:
        """Update node status."""
        self.status = status

    def update_complexity(self, complexity: EnumComplexityLevel) -> None:
        """Update node complexity."""
        self.complexity = complexity

    def update_version(
        self,
        major: int | None = None,
        minor: int | None = None,
        patch: int | None = None,
    ) -> None:
        """Update version components."""
        if major is not None:
            self.version.major = major
        if minor is not None:
            self.version.minor = minor
        if patch is not None:
            self.version.patch = patch

    def increment_version(self, level: str = "patch") -> None:
        """Increment version level."""
        if level == "major":
            self.version.major += 1
            self.version.minor = 0
            self.version.patch = 0
        elif level == "minor":
            self.version.minor += 1
            self.version.patch = 0
        else:  # patch
            self.version.patch += 1

    def has_description(self) -> bool:
        """Check if node has a description."""
        return self.description is not None and self.description.strip() != ""

    def get_complexity_level(self) -> str:
        """Get descriptive complexity level."""
        return self.complexity.value

    @classmethod
    def create_for_node(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumNodeType,
        description: str | None = None,
    ) -> ModelNodeCore:
        """Create node core for specific node."""
        return cls(
            node_id=node_id,
            node_display_name=node_name,
            description=description,
            node_type=node_type,
        )

    @classmethod
    def create_minimal_node(
        cls,
        node_name: str,
        node_type: EnumNodeType = EnumNodeType.UNKNOWN,
    ) -> ModelNodeCore:
        """Create minimal node core."""
        return cls(
            node_id=uuid_from_string(node_name, "node"),
            node_display_name=node_name,
            description=None,
            node_type=node_type,
            complexity=EnumComplexityLevel.LOW,
        )

    @classmethod
    def create_complex_node(
        cls,
        node_name: str,
        node_type: EnumNodeType,
        description: str,
    ) -> ModelNodeCore:
        """Create complex node core."""
        return cls(
            node_id=uuid_from_string(node_name, "node"),
            node_display_name=node_name,
            description=description,
            node_type=node_type,
            complexity=EnumComplexityLevel.HIGH,
        )


# Export for use
__all__ = ["ModelNodeCore"]
