"""Model for node configuration schema."""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.models.configuration.model_config_types import (
    VALID_VALUE_TYPES,
    ConfigValue,
)


class ModelNodeConfigSchema(BaseModel):
    """
    Strongly-typed model for node configuration schema.

    Represents a complete configuration schema entry including
    key, type, and default value information.

    Attributes:
        key: Configuration key
        config_type: Type name of the value ('int', 'float', 'bool', 'str')
        default: Default value
    """

    key: str = Field(..., description="Configuration key")
    config_type: VALID_VALUE_TYPES = Field(
        ..., alias="type", description="Type name of the value"
    )
    default: ConfigValue = Field(..., description="Default value")

    model_config = {"frozen": True, "populate_by_name": True}

    @model_validator(mode="after")
    def validate_default_type(self) -> "ModelNodeConfigSchema":
        """Ensure default value type matches declared config_type."""
        type_map: dict[str, type | tuple[type, ...]] = {
            "int": int,
            "float": (int, float),  # int is valid for float
            "bool": bool,
            "str": str,
        }
        expected = type_map[self.config_type]
        # Strict bool check - don't allow int/float to match bool
        if self.config_type == "bool" and not isinstance(self.default, bool):
            raise ValueError(f"default must be bool, got {type(self.default).__name__}")
        if not isinstance(self.default, expected):
            raise ValueError(
                f"default must be {self.config_type}, got {type(self.default).__name__}"
            )
        return self
