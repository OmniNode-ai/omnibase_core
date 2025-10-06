from __future__ import annotations

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Artifact type configuration model.
"""


from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_artifact_type import EnumArtifactType
from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    name: EnumArtifactType = Field(
        default=...,
        description="Strongly typed artifact type",
    )

    metadata_file: Path | None = Field(
        default=None,
        description="Path to metadata file for this artifact type",
    )

    version_pattern: str | None = Field(
        default=None,
        description="Version pattern for artifact naming/validation",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
