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
        """Get metadata as dictionary (ProtocolMetadataProvider protocol).

        Maps model fields to TypedDictMetadataDict structure:
        - version -> version (ModelSemVer if present)
        - additional_fields stored in metadata dict
        """
        result = TypedDictMetadataDict(
            name="",  # Model doesn't have name field
            description="",  # Model doesn't have description field
            tags=[],  # Model doesn't have tags field
            metadata=dict(self.additional_fields),  # Copy additional fields
        )
        # Only include version if present
        if self.version is not None:
            result["version"] = self.version
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    # Convert version field to ModelSemVer if needed
                    if key == "version" and value is not None:
                        if isinstance(value, ModelSemVer):
                            # Already a ModelSemVer, use as-is
                            setattr(self, key, value)
                        elif isinstance(value, str):
                            # Parse string to ModelSemVer
                            setattr(self, key, ModelSemVer.parse(value))
                        elif isinstance(value, dict):
                            # Create ModelSemVer from dict
                            setattr(self, key, ModelSemVer(**value))
                        else:
                            raise ModelOnexError(
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                message=f"Version must be ModelSemVer, str, or dict, got {type(value).__name__}",
                            )
                    else:
                        setattr(self, key, value)
            return True
        except ModelOnexError:
            raise
        except Exception as e:
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
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
