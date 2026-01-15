"""Input State Model.

Type-safe input state container for version parsing.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import (
    TypedDictAdditionalFields,
    TypedDictMetadataDict,
    TypedDictSerializedModel,
)


class ModelInputState(BaseModel):
    """
    Type-safe input state container for version parsing.

    Replaces dict[str, str | int | ModelSemVer | dict[str, int]] with
    structured input state that handles version parsing requirements.

    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Version field (required for parsing) - canonical ModelSemVer
    version: ModelSemVer | None = Field(
        default=None,
        description="Version information as ModelSemVer or None",
    )

    # Additional fields that might be present in input state
    additional_fields: TypedDictAdditionalFields = Field(
        default_factory=dict,
        description="Additional fields in the input state",
    )

    def get_version_data(self) -> ModelSemVer | None:
        """Get the version data for parsing."""
        return self.version

    def has_version(self) -> bool:
        """Check if input state has version information."""
        return self.version is not None

    def get_field(self, key: str) -> object | None:
        """Get a field from the input state."""
        if key == "version":
            return self.get_version_data()
        return self.additional_fields.get(key)

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {
            "name": "",
            "description": "",
            "tags": [],
            "metadata": dict(self.additional_fields) if self.additional_fields else {},
        }
        # version is Optional (ModelSemVer | None), so None check is correct
        if self.version is not None:
            result["version"] = self.version
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    # Convert version to ModelSemVer if provided as string or dict
                    if key == "version" and value is not None:
                        if isinstance(value, str):
                            value = ModelSemVer.parse(value)
                        elif isinstance(value, dict):
                            value = ModelSemVer(**value)
                        # If already ModelSemVer, use as-is
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
