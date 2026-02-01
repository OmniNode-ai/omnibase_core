"""Input State Model.

Type-safe input state container for version parsing.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
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

    Error Codes:
        VALIDATION_ERROR: Raised by set_metadata() for invalid version formats
            or metadata field assignment failures.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

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

        Returns minimal metadata for ProtocolMetadataProvider compliance.
        Empty name/description/tags are intentional: ModelInputState is a
        version parsing container, not a named entity. The protocol requires
        these fields but they have no semantic meaning for input state objects.

        Returns:
            TypedDictMetadataDict with empty name/description/tags placeholders,
            additional_fields in metadata, and version if present.
        """
        # additional_fields uses default_factory=dict, always a dict (never None)
        result: TypedDictMetadataDict = {
            "name": "",
            "description": "",
            "tags": [],
            "metadata": self.additional_fields,
        }
        if self.version is not None:
            result["version"] = self.version
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Error Codes:
            VALIDATION_ERROR: Raised when version format is invalid (string,
                dict, or other value cannot be converted to ModelSemVer) or
                when metadata field assignment fails.
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    # Convert version to ModelSemVer if provided as string or dict
                    if key == "version" and value is not None:
                        try:
                            if isinstance(value, ModelSemVer):
                                # Already ModelSemVer, use as-is (preserves type)
                                pass
                            elif isinstance(value, str):
                                value = ModelSemVer.parse(value)
                            elif isinstance(value, dict):
                                # Use model_validate for robust dict handling
                                value = ModelSemVer.model_validate(value)
                            else:
                                raise ModelOnexError(
                                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                    message=(
                                        f"Version must be ModelSemVer, str, or dict, "
                                        f"got {type(value).__name__}"
                                    ),
                                    context={
                                        "key": key,
                                        "value_type": type(value).__name__,
                                    },
                                )
                        except VALIDATION_ERRORS as version_error:
                            raise ModelOnexError(
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                message=f"Invalid version format: {version_error}",
                                context={"key": key, "value": str(value)[:100]},
                            ) from version_error
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            # Re-raise ModelOnexError (e.g., from version parsing) without wrapping
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to set metadata field: {e}",
                context={"error_type": type(e).__name__},
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Returns:
            True if the instance is valid.

        Note:
            Base implementation always returns True. Override in subclasses
            for custom validation logic.
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
