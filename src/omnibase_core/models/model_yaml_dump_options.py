from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Type-safe YAML dump options model.

Author: ONEX Framework Team
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class ModelYamlDumpOptions(BaseModel):
    """Type-safe YAML dump options.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    sort_keys: bool = False
    default_flow_style: bool = False
    allow_unicode: bool = True
    explicit_start: bool = False
    explicit_end: bool = False
    indent: int = 2
    width: int = 120

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
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


__all__ = ["ModelYamlDumpOptions"]
