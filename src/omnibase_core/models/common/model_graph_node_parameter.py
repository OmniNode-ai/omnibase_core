"""
Graph Node Parameter Model.

Strongly-typed model for individual graph node parameters.
Follows ONEX canonical patterns with strict typing - no Any types allowed.

This module provides the ``ModelGraphNodeParameter`` class for representing
individual parameters in the ONEX graph node execution system. It replaces
untyped ``dict[str, str]`` patterns with explicit type validation.

Example:
    >>> from omnibase_core.models.common.model_graph_node_parameter import (
    ...     ModelGraphNodeParameter,
    ... )
    >>> param = ModelGraphNodeParameter(
    ...     name="batch_size",
    ...     value=32,
    ...     parameter_type="integer",
    ...     description="Number of items per batch",
    ... )
    >>> param.value
    32

See Also:
    - :class:`ModelGraphNodeParameters`: Container for multiple parameters.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.types.type_json import ToolParameterValue


class ModelGraphNodeParameter(BaseModel):
    """
    Single graph node parameter with strong typing.

    Represents an individual parameter for graph node execution,
    with support for multiple value types and optional metadata.
    This model replaces untyped ``dict[str, str]`` patterns with
    explicit type validation via the ``ToolParameterValue`` union type.

    This model follows the same pattern as ModelToolParameter but is
    specifically designed for graph node parameter passing in the
    ONEX workflow execution engine.

    Supported Value Types:
        - ``str``: String values
        - ``int``: Integer values
        - ``float``: Floating-point values
        - ``bool``: Boolean values
        - ``list[str]``: List of strings
        - ``dict[str, str]``: Dictionary with string keys and values

    Attributes:
        name: Parameter name (must be a valid identifier, 1-255 chars).
        value: Parameter value with constrained allowed types.
        parameter_type: Type string for validation and documentation.
            One of: "string", "integer", "float", "boolean",
            "list[str]", "dict[str, str]".
        required: Whether this parameter is required (default: False).
        description: Optional human-readable description.

    Example:
        >>> param = ModelGraphNodeParameter(
        ...     name="threshold",
        ...     value=0.85,
        ...     parameter_type="float",
        ...     description="Confidence threshold for filtering",
        ... )
        >>> param.name
        'threshold'
        >>> param.value
        0.85

    Note:
        The model uses ``ConfigDict(extra="forbid")`` to ensure strict
        validation and prevent unknown fields from being silently accepted.

    See Also:
        - :class:`ModelGraphNodeParameters`: Container for multiple parameters.
        - :class:`ModelToolParameter`: Similar pattern for tool parameters.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    name: str = Field(
        default=...,
        description="Parameter name (must be a valid identifier)",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
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
