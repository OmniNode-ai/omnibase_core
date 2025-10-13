from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Node capabilities summary model.

Clean, strongly-typed replacement for node capabilities dict[str, Any]return types.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.errors.error_codes import EnumCoreErrorCode


class ModelNodeCapabilitiesSummary(BaseModel):
    """Node capabilities summary with specific types.
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    capabilities_count: int = Field(description="Number of capabilities")
    operations_count: int = Field(description="Number of operations")
    dependencies_count: int = Field(description="Number of dependencies")
    has_capabilities: bool = Field(description="Whether node has capabilities")
    has_operations: bool = Field(description="Whether node has operations")
    has_dependencies: bool = Field(description="Whether node has dependencies")
    has_performance_metrics: bool = Field(
        description="Whether node has performance metrics",
    )
    primary_capability: str | None = Field(description="Primary capability if any")
    metrics_count: int = Field(description="Number of metrics")

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

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


__all__ = ["ModelNodeCapabilitiesSummary"]
