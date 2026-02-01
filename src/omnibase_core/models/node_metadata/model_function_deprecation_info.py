"""
Function deprecation and lifecycle information.

Contains deprecation details, version information, and replacement suggestions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_deprecation_status import EnumDeprecationStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_deprecation_summary import (
    TypedDictDeprecationSummary,
)


class ModelFunctionDeprecationInfo(BaseModel):
    """
    Function deprecation and lifecycle information.

    Contains deprecation details:
    - Deprecation version and replacement info
    - Lifecycle status
    """

    # Deprecation information (2 fields, but minimal)
    deprecated_since: ModelSemVer | None = Field(
        default=None,
        description="Version when deprecated",
    )
    replacement: str | None = Field(
        default=None,
        description="Replacement function if deprecated",
    )

    def is_deprecated(self) -> bool:
        """Check if function is deprecated."""
        return self.deprecated_since is not None

    def has_replacement(self) -> bool:
        """Check if function has a replacement."""
        return self.replacement is not None

    def get_deprecation_status(self) -> EnumDeprecationStatus:
        """Get deprecation status as enum."""
        if not self.is_deprecated():
            return EnumDeprecationStatus.ACTIVE

        if self.has_replacement():
            return EnumDeprecationStatus.DEPRECATED_WITH_REPLACEMENT

        return EnumDeprecationStatus.DEPRECATED

    def get_deprecation_status_description(self) -> str:
        """Get deprecation status description as human-readable string."""
        if not self.is_deprecated():
            return "active"

        if self.has_replacement():
            return f"deprecated since {self.deprecated_since}, use {self.replacement}"

        return f"deprecated since {self.deprecated_since}"

    def get_deprecation_summary(self) -> TypedDictDeprecationSummary:
        """Get deprecation information summary."""
        return {
            "is_deprecated": self.is_deprecated(),
            "has_replacement": self.has_replacement(),
            "deprecated_since": (
                str(self.deprecated_since) if self.deprecated_since else None
            ),
            "replacement": self.replacement,
            "status": self.get_deprecation_status().value,
        }

    @classmethod
    def create_active(cls) -> ModelFunctionDeprecationInfo:
        """Create active (non-deprecated) function info."""
        return cls()

    @classmethod
    def create_deprecated(
        cls,
        deprecated_since: ModelSemVer,
        replacement: str | None = None,
    ) -> ModelFunctionDeprecationInfo:
        """Create deprecated function info."""
        return cls(
            deprecated_since=deprecated_since,
            replacement=replacement,
        )

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
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack deprecation info into metadata dict
        result["metadata"] = {
            "deprecated_since": (
                str(self.deprecated_since) if self.deprecated_since else None
            ),
            "replacement": self.replacement,
            "is_deprecated": self.is_deprecated(),
            "has_replacement": self.has_replacement(),
            "deprecation_status": self.get_deprecation_status().value,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


__all__ = ["ModelFunctionDeprecationInfo"]
