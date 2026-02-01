"""
Node core information summary model.

Clean, strongly-typed replacement for node core info dict[str, Any] return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_status import EnumStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodeCoreInfoSummary(BaseModel):
    """
    Core node information summary with strongly-typed fields.

    This model provides a clean, type-safe alternative to dict[str, Any] return
    types for node core information. It captures essential node metadata including
    identification, versioning, status, and health information.

    Implements Core protocols:
        - Identifiable: UUID-based identification via get_id()
        - ProtocolMetadataProvider: Metadata management via get_metadata()/set_metadata()
        - Serializable: Data serialization via serialize()
        - Validatable: Instance validation via validate_instance()

    Thread Safety:
        This model is a Pydantic BaseModel with validate_assignment=True, making
        it safe for concurrent reads. Modifications should be synchronized externally.
    """

    node_id: UUID = Field(description="Node identifier")
    node_name: str = Field(description="Node name")
    node_type: EnumMetadataNodeType = Field(description="Node type value")
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version",
    )
    status: EnumStatus = Field(description="Node status value")
    health: EnumHealthStatus = Field(description="Node health status")
    is_active: bool = Field(description="Whether node is active")
    is_healthy: bool = Field(description="Whether node is healthy")
    has_description: bool = Field(description="Whether node has description")
    has_author: bool = Field(description="Whether node has author")

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """
        Get metadata as dictionary for ProtocolMetadataProvider protocol.

        Returns a TypedDictMetadataDict containing comprehensive node core
        information. Maps node identification and versioning to standard
        top-level keys, with status and health details in nested metadata.

        Returns:
            TypedDictMetadataDict with the following structure:
            - "name": node_name (required field, always present)
            - "version": ModelSemVer instance representing node version
            - "metadata": Dict containing:
                - "node_id": String representation of the node UUID
                - "node_type": EnumMetadataNodeType value string
                  (e.g., "class", "function", "module", "method")
                - "status": EnumStatus value string (e.g., "active", "inactive")
                - "health": EnumHealthStatus value string
                  (e.g., "healthy", "degraded", "unhealthy")
                - "is_active": Boolean indicating if node is currently active
                - "is_healthy": Boolean indicating if node is in healthy state
                - "has_description": Boolean indicating if description is set
                - "has_author": Boolean indicating if author info is available

        Example:
            >>> from uuid import uuid4
            >>> from omnibase_core.enums.enum_health_status import EnumHealthStatus
            >>> from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
            >>> from omnibase_core.enums.enum_status import EnumStatus
            >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
            >>> summary = ModelNodeCoreInfoSummary(
            ...     node_id=uuid4(),
            ...     node_name="DataProcessor",
            ...     node_type=EnumMetadataNodeType.CLASS,
            ...     node_version=ModelSemVer(major=1, minor=0, patch=0),
            ...     status=EnumStatus.ACTIVE,
            ...     health=EnumHealthStatus.HEALTHY,
            ...     is_active=True,
            ...     is_healthy=True,
            ...     has_description=True,
            ...     has_author=False,
            ... )
            >>> metadata = summary.get_metadata()
            >>> metadata["name"]
            'DataProcessor'
            >>> metadata["metadata"]["is_active"]
            True
        """
        result: TypedDictMetadataDict = {}
        # Map actual fields to TypedDictMetadataDict structure
        # node_name is required field, always present
        result["name"] = self.node_name
        # node_version is required (has default_factory), include directly
        result["version"] = self.node_version
        # Pack additional fields into metadata
        result["metadata"] = {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health.value,
            "is_active": self.is_active,
            "is_healthy": self.is_healthy,
            "has_description": self.has_description,
            "has_author": self.has_author,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """
        Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Updates model fields from the provided metadata dictionary. Only fields
        that exist on the model are updated; unknown keys are silently ignored.

        Args:
            metadata: Dictionary containing metadata key-value pairs

        Returns:
            True if metadata was set successfully, False on any error

        Note:
            The broad exception handler is intentional for protocol compliance.
            This method should never raise exceptions per ProtocolMetadataProvider
            contract - failures are indicated by returning False.
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Performs basic validation to ensure the instance is in a valid state.
        For ModelNodeCoreInfoSummary, Pydantic's model validation handles field
        constraints, so this method returns True for well-constructed instances.

        Returns:
            True if the instance is valid, False otherwise

        Note:
            The broad exception handler is intentional for protocol compliance.
            This method should never raise exceptions per ProtocolValidatable
            contract - validation failures are indicated by returning False.
            Override in subclasses for custom validation logic.
        """
        return True


__all__ = ["ModelNodeCoreInfoSummary"]
