import json
from typing import Any

from pydantic import Field

"""
Tool Parameters Model

Strongly typed model for tool parameters to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with zero tolerance for Any types.
"""

from pydantic import BaseModel


class ModelToolParameter(BaseModel):
    """Single tool parameter with strong typing."""

    name: str = Field(default=..., description="Parameter name")
    value: str | int | float | bool | list[str] | dict[str, str] = Field(
        default=...,
        description="Parameter value with specific allowed types",
    )
    parameter_type: str = Field(
        default=...,
        description="Parameter type",
        json_schema_extra={
            "enum": [
                "string",
                "integer",
                "float",
                "boolean",
                "list[Any]",
                "dict[str, Any]",
            ],
        },
    )
    required: bool = Field(default=False, description="Whether parameter is required")
    description: str | None = Field(default=None, description="Parameter description")
