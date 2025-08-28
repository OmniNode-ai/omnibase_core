"""
Tool Parameters Model

Strongly typed model for tool parameters to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with zero tolerance for Any types.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelToolParameter(BaseModel):
    """Single tool parameter with strong typing."""

    name: str = Field(..., description="Parameter name")
    value: Union[str, int, float, bool, List[str], Dict[str, str]] = Field(
        ..., description="Parameter value with specific allowed types"
    )
    parameter_type: str = Field(
        ...,
        description="Parameter type",
        json_schema_extra={
            "enum": ["string", "integer", "float", "boolean", "list", "dict"]
        },
    )
    required: bool = Field(default=False, description="Whether parameter is required")
    description: Optional[str] = Field(None, description="Parameter description")


class ModelToolParameters(BaseModel):
    """Tool parameters container with strong typing."""

    parameters: List[ModelToolParameter] = Field(
        default_factory=list, description="List of typed tool parameters"
    )

    def get_parameter_dict(
        self,
    ) -> Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]:
        """Convert to dictionary format for backward compatibility."""
        return {param.name: param.value for param in self.parameters}

    @classmethod
    def from_dict(
        cls,
        param_dict: Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]],
    ) -> "ModelToolParameters":
        """Create from dictionary with type inference."""
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
                param_type = "list"
            elif isinstance(value, dict):
                param_type = "dict"
            else:
                # Fallback to string representation
                param_type = "string"
                value = str(value)

            parameters.append(
                ModelToolParameter(name=name, value=value, parameter_type=param_type)
            )

        return cls(parameters=parameters)
