from __future__ import annotations

from pydantic import Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)

"""
Node Core Model.

Core node identification and basic information.
Follows ONEX one-model-per-file architecture.
"""


from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class ModelNodeCore(BaseModel):
    """
    Core node identification and basic information.

    Focused on fundamental node identity and basic properties.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core node info - UUID-based entity references
    node_id: UUID = Field(
        default_factory=lambda: uuid_from_string("default", "node"),
        description="Unique identifier for the node",
    )
    node_display_name: str | None = Field(
        default=None, description="Human-readable node name"
    )
    description: str | None = Field(default=None, description="Node description")
    node_type: EnumNodeType = Field(
        default=EnumNodeType.UNKNOWN,
        description="Type of node",
    )
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: EnumConceptualComplexity = Field(
        default=EnumConceptualComplexity.INTERMEDIATE,
        description="Node conceptual complexity level",
    )
    version: ModelSemVer = Field(
        default_factory=default_model_version,
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
        return self.complexity == EnumConceptualComplexity.TRIVIAL

    @property
    def is_complex(self) -> bool:
        """Check if node has high or critical complexity."""
        return self.complexity in [
            EnumConceptualComplexity.ADVANCED,
            EnumConceptualComplexity.EXPERT,
        ]

    @property
    def version_string(self) -> str:
        """Get version as string."""
        return str(self.version)

    def update_status(self, status: EnumMetadataNodeStatus) -> None:
        """Update node status."""
        self.status = status

    def update_complexity(self, complexity: EnumConceptualComplexity) -> None:
        """Update node complexity."""
        self.complexity = complexity

    def update_version(
        self,
        major: int | None = None,
        minor: int | None = None,
        patch: int | None = None,
    ) -> None:
        """Update version components."""
        current_major = self.version.major if major is None else major
        current_minor = self.version.minor if minor is None else minor
        current_patch = self.version.patch if patch is None else patch

        # Create a new ModelSemVer since it's frozen
        object.__setattr__(
            self,
            "version",
            ModelSemVer(major=current_major, minor=current_minor, patch=current_patch),
        )

    def increment_version(self, level: str = "patch") -> None:
        """Increment version level."""
        if level == "major":
            new_version = ModelSemVer(major=self.version.major + 1, minor=0, patch=0)
        elif level == "minor":
            new_version = ModelSemVer(
                major=self.version.major,
                minor=self.version.minor + 1,
                patch=0,
            )
        else:  # patch
            new_version = ModelSemVer(
                major=self.version.major,
                minor=self.version.minor,
                patch=self.version.patch + 1,
            )

        # Create a new ModelSemVer since it's frozen
        object.__setattr__(self, "version", new_version)

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
            complexity=EnumConceptualComplexity.BASIC,
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
            complexity=EnumConceptualComplexity.ADVANCED,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map node_display_name to name
        if self.node_display_name:
            result["name"] = self.node_display_name
        # Map description directly
        if self.description:
            result["description"] = self.description
        # Map version directly
        result["version"] = self.version
        # Pack other core fields into metadata dict
        result["metadata"] = {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "complexity": self.complexity.value,
            "is_active": self.is_active,
            "is_deprecated": self.is_deprecated,
            "version_string": self.version_string,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelNodeCore"]
