"""Model for node configuration entry."""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.models.configuration.model_config_types import (
    VALID_VALUE_TYPES,
    ConfigValue,
)


class ModelNodeConfigEntry(BaseModel):
    """
    Strongly-typed model for a node configuration entry.

    This model represents a single configuration entry with its key,
    type information, and default value.

    Attributes:
        key: Configuration key (e.g., "compute.max_parallel_workers")
        value_type: Type name of the value ('int', 'float', 'bool', 'str')
        default: Default value for this configuration
    """

    key: str = Field(
        ...,
        description="Configuration key (e.g., 'compute.max_parallel_workers')",
    )
    value_type: VALID_VALUE_TYPES = Field(
        ...,
        description="Type name of the value ('int', 'float', 'bool', 'str')",
    )
    default: ConfigValue = Field(
        ...,
        description="Default value for this configuration",
    )

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_default_type(self) -> "ModelNodeConfigEntry":
        """Ensure default value type matches declared value_type."""
        type_map: dict[str, type | tuple[type, ...]] = {
            "int": int,
            "float": (int, float),  # int is valid for float
            "bool": bool,
            "str": str,
        }
        expected = type_map[self.value_type]
        # Strict bool check - don't allow int/float to match bool
        if self.value_type == "bool" and not isinstance(self.default, bool):
            raise ValueError(f"default must be bool, got {type(self.default).__name__}")
        if not isinstance(self.default, expected):
            raise ValueError(
                f"default must be {self.value_type}, got {type(self.default).__name__}"
            )
        return self
