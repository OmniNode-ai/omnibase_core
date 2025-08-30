"""
Workflow Parameters Model

Type-safe workflow parameters that replace Dict[str, Any] usage
for workflow execution configuration.
"""

from typing import Union

from pydantic import BaseModel, Field

ParameterValue = Union[
    str,
    int,
    bool,
    float,
    list[str],
    list[int],
    list[float],
    dict[str, str],
]


class ModelWorkflowParameters(BaseModel):
    """
    Type-safe workflow parameters.

    This model provides structured parameter storage for workflow execution
    with type safety and validation.
    """

    parameters: dict[str, ParameterValue] = Field(
        default_factory=dict,
        description="Workflow parameter values",
    )

    required_parameters: list[str] = Field(
        default_factory=list,
        description="List of required parameter names",
    )

    parameter_metadata: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Metadata for each parameter",
    )

    def get_parameter(
        self,
        key: str,
        default: ParameterValue | None = None,
    ) -> ParameterValue | None:
        """
        Get parameter value with type safety.

        Args:
            key: Parameter key
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        return self.parameters.get(key, default)

    def set_parameter(self, key: str, value: ParameterValue) -> None:
        """
        Set parameter value.

        Args:
            key: Parameter key
            value: Parameter value
        """
        self.parameters[key] = value

    def get_string(self, key: str, default: str = "") -> str:
        """Get parameter as string."""
        value = self.get_parameter(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get parameter as integer."""
        value = self.get_parameter(key, default)
        if isinstance(value, int | float):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get parameter as boolean."""
        value = self.get_parameter(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value) if value is not None else default

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get parameter as list."""
        value = self.get_parameter(key, default or [])
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [value]
        return default or []

    def is_required(self, key: str) -> bool:
        """Check if parameter is required."""
        return key in self.required_parameters

    def validate_required(self) -> list[str]:
        """
        Validate that all required parameters are present.

        Returns:
            List of missing required parameter names
        """
        missing = []
        for param in self.required_parameters:
            if param not in self.parameters:
                missing.append(param)
        return missing

    def add_metadata(self, key: str, metadata_key: str, metadata_value: str) -> None:
        """Add metadata for a parameter."""
        if key not in self.parameter_metadata:
            self.parameter_metadata[key] = {}
        self.parameter_metadata[key][metadata_key] = metadata_value

    def get_metadata(self, key: str, metadata_key: str) -> str | None:
        """Get metadata for a parameter."""
        if key in self.parameter_metadata:
            return self.parameter_metadata[key].get(metadata_key)
        return None
