from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_tool_parameters import ModelToolParameter
from omnibase_core.types.type_json import ToolParameterValue


class ModelToolParameters(BaseModel):
    """Tool parameters container with strong typing."""

    parameters: list[ModelToolParameter] = Field(
        default_factory=list,
        description="List of typed tool parameters",
    )

    def get_parameter_dict(
        self,
    ) -> dict[str, ToolParameterValue]:
        """Convert to dictionary format for current standards."""
        return {param.name: param.value for param in self.parameters}

    @classmethod
    def from_dict(
        cls,
        param_dict: dict[str, ToolParameterValue],
    ) -> "ModelToolParameters":
        """Create from dictionary with type inference."""
        parameters = []
        for name, value in param_dict.items():
            # Check bool before int since bool is a subclass of int in Python
            if isinstance(value, bool):
                param_type = "boolean"
            elif isinstance(value, str):
                param_type = "string"
            elif isinstance(value, int):
                param_type = "integer"
            elif isinstance(value, float):
                param_type = "float"
            elif isinstance(value, list):
                param_type = "list[str]"
            elif isinstance(value, dict):
                param_type = "dict[str, str]"
            else:  # pragma: no cover
                # Fallback for unexpected types - defensive code for runtime safety
                # Type system guarantees this is unreachable, but runtime values may differ
                param_type = "string"  # type: ignore[unreachable]
                value = str(value)

            parameters.append(
                ModelToolParameter(name=name, value=value, parameter_type=param_type),
            )

        return cls(parameters=parameters)
