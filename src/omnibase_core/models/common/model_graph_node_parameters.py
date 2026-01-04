"""
Graph Node Parameters Container Model.

Container for strongly-typed graph node parameters.
Follows ONEX canonical patterns with strict typing - no Any types allowed.

This module provides the ``ModelGraphNodeParameters`` class for managing
collections of typed parameters in the ONEX graph node execution system.
It replaces untyped ``dict[str, str]`` patterns with strongly-typed containers.

Example:
    >>> from omnibase_core.models.common.model_graph_node_parameters import (
    ...     ModelGraphNodeParameters,
    ... )
    >>> params = ModelGraphNodeParameters.from_dict({
    ...     "threshold": 0.85,
    ...     "enabled": True,
    ...     "tags": ["production", "ml"],
    ... })
    >>> params.get_parameter("threshold")
    0.85

See Also:
    - :class:`ModelGraphNodeParameter`: Individual parameter model.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_graph_node_parameter import (
    ModelGraphNodeParameter,
)
from omnibase_core.types.type_json import ToolParameterValue


class ModelGraphNodeParameters(BaseModel):
    """
    Container for graph node parameters with strong typing.

    Provides type-safe parameter management for graph nodes,
    replacing dict[str, str] patterns with properly typed parameters.

    This model supports:
    - Multiple value types (str, int, float, bool, list[str], dict[str, str])
    - Type inference from Python values
    - Conversion to/from dictionary format for interoperability

    Example:
        >>> params = ModelGraphNodeParameters.from_dict({
        ...     "threshold": 0.85,
        ...     "enabled": True,
        ...     "tags": ["production", "ml"],
        ... })
        >>> params.get_parameter_dict()
        {'threshold': 0.85, 'enabled': True, 'tags': ['production', 'ml']}
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    parameters: list[ModelGraphNodeParameter] = Field(
        default_factory=list,
        description="List of typed graph node parameters",
    )

    def get_parameter_dict(self) -> dict[str, ToolParameterValue]:
        """
        Convert to dictionary format for current standards.

        Returns:
            dict[str, ToolParameterValue]: Dictionary mapping parameter names to values
        """
        return {param.name: param.value for param in self.parameters}

    def get_parameter(self, name: str) -> ToolParameterValue | None:
        """
        Get a parameter value by name.

        Args:
            name: Parameter name to look up

        Returns:
            The parameter value if found, None otherwise
        """
        for param in self.parameters:
            if param.name == name:
                return param.value
        return None

    def has_parameter(self, name: str) -> bool:
        """
        Check if a parameter exists.

        Args:
            name: Parameter name to check

        Returns:
            True if parameter exists, False otherwise
        """
        return any(param.name == name for param in self.parameters)

    @classmethod
    def from_dict(
        cls,
        param_dict: dict[str, ToolParameterValue],
    ) -> "ModelGraphNodeParameters":
        """
        Create from dictionary with type inference.

        Automatically infers parameter types from Python values.

        Args:
            param_dict: Dictionary of parameter names to values

        Returns:
            ModelGraphNodeParameters instance with typed parameters
        """
        parameters: list[ModelGraphNodeParameter] = []
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
                ModelGraphNodeParameter(
                    name=name,
                    value=value,
                    parameter_type=param_type,
                ),
            )

        return cls(parameters=parameters)


__all__ = ["ModelGraphNodeParameters"]
