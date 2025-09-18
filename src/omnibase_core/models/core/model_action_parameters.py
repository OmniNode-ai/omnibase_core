"""
Action Parameters Model

Typed parameters container for action execution to replace Dict usage.
Provides strong typing for action parameter values.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .model_generic_metadata import ModelGenericMetadata


class ModelActionParameters(BaseModel):
    """
    Typed parameters for action execution.

    Replaces Dict[str, Any] with structured parameter storage
    for better type safety and validation.
    """

    # Basic parameter types
    string_params: dict[str, str] = Field(
        default_factory=dict,
        description="String parameters",
    )
    numeric_params: dict[str, int | float] = Field(
        default_factory=dict,
        description="Numeric parameters",
    )
    boolean_params: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean parameters",
    )
    list_params: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List parameters",
    )

    # Nested parameters for complex data
    nested_params: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Nested object parameters",
    )

    # For complex types requiring dynamic parameters
    raw_params: ModelGenericMetadata | None = Field(
        None,
        description="Raw parameters for complex types (use sparingly)",
    )

    model_config = ConfigDict(extra="forbid")

    def get_parameter(self, name: str) -> Any:
        """Get parameter by name, searching all parameter types."""
        # Search in order of preference
        if name in self.string_params:
            return self.string_params[name]
        if name in self.numeric_params:
            return self.numeric_params[name]
        if name in self.boolean_params:
            return self.boolean_params[name]
        if name in self.list_params:
            return self.list_params[name]
        if name in self.nested_params:
            return self.nested_params[name]
        if (
            self.raw_params
            and self.raw_params.custom_fields
            and name in self.raw_params.custom_fields
        ):
            return self.raw_params.custom_fields[name]
        return None

    def set_parameter(self, name: str, value: Any) -> None:
        """Set parameter with automatic type detection."""
        if isinstance(value, str):
            self.string_params[name] = value
        elif isinstance(value, (int, float)):
            self.numeric_params[name] = value
        elif isinstance(value, bool):
            self.boolean_params[name] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            self.list_params[name] = value
        elif isinstance(value, dict) and all(
            isinstance(v, str) for v in value.values()
        ):
            self.nested_params[name] = value
        else:
            # Fall back to raw parameters for complex types
            if not self.raw_params:
                self.raw_params = ModelGenericMetadata()
            # Use custom_fields for complex parameter storage
            if not self.raw_params.custom_fields:
                self.raw_params.custom_fields = {}
            # Store complex values as string representation for now
            self.raw_params.custom_fields[name] = str(value)

    def has_parameter(self, name: str) -> bool:
        """Check if parameter exists."""
        return self.get_parameter(name) is not None

    def to_flat_dict(
        self,
    ) -> dict[str, str | int | float | bool | list[str] | dict[str, str]]:
        """Convert to flat dictionary for legacy compatibility."""
        result: dict[str, str | int | float | bool | list[str] | dict[str, str]] = {}
        result.update(self.string_params)
        result.update(self.numeric_params)
        result.update(self.boolean_params)
        result.update(self.list_params)
        result.update(self.nested_params)
        # Only include raw params that match our typing
        if self.raw_params and self.raw_params.custom_fields:
            for key, value in self.raw_params.custom_fields.items():
                if isinstance(value, (str, int, float, bool, list, dict)):
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelActionParameters":
        """Create from dictionary for data conversion."""
        instance = cls()
        for key, value in data.items():
            instance.set_parameter(key, value)
        return instance
