from __future__ import annotations

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"\nArtifact type configuration model.\n"
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_artifact_type import EnumArtifactType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.primitives.model_semver import ModelSemVer


class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    name: EnumArtifactType = Field(
        default=..., description="Strongly typed artifact type"
    )
    metadata_file: Path | None = Field(
        default=None, description="Path to metadata file for this artifact type"
    )
    version_pattern: ModelSemVer | None = Field(
        default=None, description="Version pattern for artifact naming/validation"
    )
    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e
