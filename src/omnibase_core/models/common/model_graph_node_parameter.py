"""
Graph Node Parameter Model

Strongly-typed model for individual graph node parameters.
Follows ONEX canonical patterns with strict typing - no Any types allowed.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.json_types import ToolParameterValue


class ModelGraphNodeParameter(BaseModel):
    """
    Single graph node parameter with strong typing.

    Represents an individual parameter for graph node execution,
    with support for multiple value types and optional metadata.

    This model follows the same pattern as ModelToolParameter but is
    specifically designed for graph node parameter passing.

    Example:
        >>> param = ModelGraphNodeParameter(
        ...     name="threshold",
        ...     value=0.85,
        ...     parameter_type="float",
        ...     description="Confidence threshold for filtering",
        ... )
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(
        default=...,
        description="Parameter name (must be a valid identifier)",
        min_length=1,
        max_length=255,
    )
    value: ToolParameterValue = Field(
        default=...,
        description="Parameter value with constrained allowed types",
    )
    parameter_type: str = Field(
        default=...,
        description="Parameter type for validation and documentation",
        json_schema_extra={
            "enum": [
                "string",
                "integer",
                "float",
                "boolean",
                "list[str]",
                "dict[str, str]",
            ],
        },
    )
    required: bool = Field(
        default=False,
        description="Whether this parameter is required",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the parameter",
    )


__all__ = ["ModelGraphNodeParameter"]
