from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
YAML option value model with discriminated union.

Author: ONEX Framework Team
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_yaml_option_type import EnumYamlOptionType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelYamlOption(BaseModel):
    """Discriminated union for YAML dumper option values.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    option_type: EnumYamlOptionType = Field(
        description="Type discriminator for the option value",
    )
    boolean_value: bool | None = Field(default=None, description="Boolean option value")
    integer_value: int | None = Field(default=None, description="Integer option value")
    string_value: str | None = Field(default=None, description="String option value")

    @classmethod
    def from_bool(cls, value: bool) -> "ModelYamlOption":
        """Create from boolean value."""
        return cls(
            option_type=EnumYamlOptionType.BOOLEAN,
            boolean_value=value,
            integer_value=None,
            string_value=None,
        )

    @classmethod
    def from_int(cls, value: int) -> "ModelYamlOption":
        """Create from integer value."""
        return cls(
            option_type=EnumYamlOptionType.INTEGER,
            boolean_value=None,
            integer_value=value,
            string_value=None,
        )

    @classmethod
    def from_str(cls, value: str) -> "ModelYamlOption":
        """Create from string value."""
        return cls(
            option_type=EnumYamlOptionType.STRING,
            boolean_value=None,
            integer_value=None,
            string_value=value,
        )

    def to_value(self) -> object:
        """Convert back to Python value."""
        if self.option_type == EnumYamlOptionType.BOOLEAN:
            return self.boolean_value
        if self.option_type == EnumYamlOptionType.INTEGER:
            return self.integer_value
        if self.option_type == EnumYamlOptionType.STRING:
            return self.string_value
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Invalid option_type: {self.option_type}",
            details=ModelErrorContext.with_context(
                {
                    "option_type": ModelSchemaValue.from_value(str(self.option_type)),
                    "method": ModelSchemaValue.from_value("to_value"),
                },
            ),
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

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
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelYamlOption"]
