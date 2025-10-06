from enum import Enum
from typing import Any, Dict, TypedDict, Union

from pydantic import BaseModel, Field, model_validator

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.core.model_sem_ver import ModelSemVer


class ModelVersionUnion(BaseModel):
    """
    Discriminated union for version types.

    Replaces Union[ModelSemVer, ModelTypedDictVersionDict, None] patterns with structured typing.
    Implements omnibase_spi protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    version_type: EnumVersionUnionType = Field(
        description="Type discriminator for version value",
        discriminator="version_type",
    )

    # Version storage (only one should be populated based on type)
    semantic_version: ModelSemVer | None = None
    version_dict: ModelTypedDictVersionDict | None = None

    @model_validator(mode="after")
    def validate_single_version(self) -> ModelVersionUnion:
        """Ensure only one version value is set based on type discriminator."""
        if self.version_type == EnumVersionUnionType.SEMANTIC_VERSION:
            if self.semantic_version is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="semantic_version must be set when version_type is 'semantic_version'",
                )
            if self.version_dict is not None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="version_dict must be None when version_type is 'semantic_version'",
                )
        elif self.version_type == EnumVersionUnionType.VERSION_DICT:
            if self.version_dict is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="version_dict must be set when version_type is 'version_dict'",
                )
            if self.semantic_version is not None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="semantic_version must be None when version_type is 'version_dict'",
                )
        elif self.version_type == EnumVersionUnionType.NONE_VERSION:
            if self.semantic_version is not None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="semantic_version must be None when version_type is 'none_version'",
                )
            if self.version_dict is not None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="version_dict must be None when version_type is 'none_version'",
                )

        return self

    @classmethod
    def from_semantic_version(cls, version: ModelSemVer) -> ModelVersionUnion:
        """Create union from semantic version."""
        return cls(
            version_type=EnumVersionUnionType.SEMANTIC_VERSION,
            semantic_version=version,
        )

    @classmethod
    def from_version_dict(
        cls, version_dict: ModelTypedDictVersionDict
    ) -> ModelVersionUnion:
        """Create union from version dict[str, Any]ionary."""
        return cls(
            version_type=EnumVersionUnionType.VERSION_DICT,
            version_dict=version_dict,
        )

    @classmethod
    def from_none(cls) -> ModelVersionUnion:
        """Create union representing no version."""
        return cls(version_type=EnumVersionUnionType.NONE_VERSION)

    def get_version(self) -> ModelSemVer | ModelTypedDictVersionDict | None:
        """
        Get the actual version value with runtime type safety.

        Returns:
            ModelSemVer | ModelTypedDictVersionDict | None: The actual version value based on
                   version_type discriminator. Use isinstance() to check specific type.

        Raises:
            ModelOnexError: If discriminator state is invalid

        Examples:
            version = union.get_version()
            if isinstance(version, ModelSemVer):
                # Handle semantic version
                pass
            elif isinstance(version, dict):
                # Handle version dict[str, Any]ionary
                pass
            elif version is None:
                # Handle no version
                pass
        """
        if self.version_type == EnumVersionUnionType.SEMANTIC_VERSION:
            if self.semantic_version is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="Invalid state: semantic_version is None but version_type is SEMANTIC_VERSION",
                )
            return self.semantic_version
        if self.version_type == EnumVersionUnionType.VERSION_DICT:
            if self.version_dict is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="Invalid state: version_dict is None but version_type is VERSION_DICT",
                )
            return self.version_dict
        if self.version_type == EnumVersionUnionType.NONE_VERSION:
            return None
        raise ModelOnexError(
            code=ModelCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown version_type: {self.version_type}",
        )

    def has_version(self) -> bool:
        """Check if version union has a non-None version."""
        return self.version_type != EnumVersionUnionType.NONE_VERSION

    def to_semantic_version(self) -> ModelSemVer:
        """
        Convert to ModelSemVer regardless of current type.

        Returns:
            ModelSemVer: Converted semantic version

        Raises:
            ModelOnexError: If version is None or conversion fails
        """
        if self.version_type == EnumVersionUnionType.SEMANTIC_VERSION:
            if self.semantic_version is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="semantic_version is None",
                )
            return self.semantic_version
        if self.version_type == EnumVersionUnionType.VERSION_DICT:
            if self.version_dict is None:
                raise ModelOnexError(
                    code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message="version_dict is None",
                )
            return ModelSemVer(**self.version_dict)
        raise ModelOnexError(
            code=ModelCoreErrorCode.VALIDATION_ERROR,
            message="Cannot convert None version to ModelSemVer",
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

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
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol).

        Raises:
            ModelOnexError: If setting metadata fails with details about the failure
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Setting metadata failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e
