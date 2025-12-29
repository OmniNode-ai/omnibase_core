from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.enums.enum_status import EnumStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

"""
Node core information summary model.

Clean, strongly-typed replacement for node core info dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""


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
    health: EnumNodeHealthStatus = Field(description="Node health status")
    is_active: bool = Field(description="Whether node is active")
    is_healthy: bool = Field(description="Whether node is healthy")
    has_description: bool = Field(description="Whether node has description")
    has_author: bool = Field(description="Whether node has author")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

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
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata: dict[str, object] = {}
        # Map model fields to standard metadata keys
        # TypedDictMetadataDict expects: name, description, version, tags, metadata
        field_mapping = {
            "name": "node_name",
            "version": "node_version",
        }
        for metadata_key, model_field in field_mapping.items():
            if hasattr(self, model_field):
                value = getattr(self, model_field)
                if value is not None:
                    metadata[metadata_key] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return cast(TypedDictMetadataDict, metadata)

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
        return cast(
            TypedDictSerializedModel,
            self.model_dump(exclude_none=False, by_alias=True),
        )

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
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


__all__ = ["ModelNodeCoreInfoSummary"]
