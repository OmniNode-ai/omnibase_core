from typing import Any, List

from pydantic import BaseModel, Field


class ModelToolParameters(BaseModel):
    """Tool parameters container with strong typing."""

    parameters: list[ModelToolParameter] = Field(
        default_factory=list,
        description="List of typed tool parameters",
    )

    def get_parameter_dict(
        self,
    ) -> dict[str, str | int | float | bool | list[str] | dict[str, str]]:
        """Convert to dict[str, Any]ionary format for current standards."""
        return {param.name: param.value for param in self.parameters}

    @classmethod
    def from_dict(
        cls,
        param_dict: dict[str, str | int | float | bool | list[str] | dict[str, str]],
    ) -> "ModelToolParameters":
        """Create from dict[str, Any]ionary with type inference."""
        parameters = []
        for name, value in param_dict.items():
            if isinstance(value, str):
                param_type = "string"
            elif isinstance(value, int):
                param_type = "integer"
            elif isinstance(value, float):
                param_type = "float"
            elif isinstance(value, bool):
                param_type = "boolean"
            elif isinstance(value, list):
                param_type = "list[Any]"
            elif isinstance(value, dict):
                param_type = "dict[str, Any]"
            else:
                # Fallback to string representation
                param_type = "string"
                value = str(value)

            parameters.append(
                ModelToolParameter(name=name, value=value, parameter_type=param_type),
            )

        return cls(parameters=parameters)
