"""
Typed inputs model for graph nodes.

This module provides strongly-typed inputs for graph node patterns.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_graph_node_parameters import (
    ModelGraphNodeParameters,
)
from omnibase_core.models.common.model_output_mapping import ModelOutputMapping
from omnibase_core.types.type_json import ToolParameterValue


class ModelGraphNodeInputs(BaseModel):
    """
    Typed inputs for graph nodes.

    Replaces dict[str, Any] inputs field in ModelGraphNode
    with explicit typed fields for graph node inputs.

    Uses strongly-typed container models:
    - parameters: ModelGraphNodeParameters for typed key-value parameters
    - from_outputs: ModelOutputMapping for node output references
    - constants: dict[str, str] for constant string values

    Example:
        >>> inputs = ModelGraphNodeInputs(
        ...     parameters=ModelGraphNodeParameters.from_dict({
        ...         "threshold": 0.85,
        ...         "enabled": True,
        ...     }),
        ...     from_outputs=ModelOutputMapping.from_dict({
        ...         "data": "preprocessing.output",
        ...     }),
        ... )
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    parameters: ModelGraphNodeParameters = Field(
        default_factory=ModelGraphNodeParameters,
        description="Typed input parameters with value type support",
    )
    from_outputs: ModelOutputMapping = Field(
        default_factory=ModelOutputMapping,
        description="Typed mappings from other node outputs",
    )
    constants: dict[str, str] = Field(
        default_factory=dict,
        description="Constant input values as strings",
    )
    environment_vars: list[str] = Field(
        default_factory=list,
        description="Environment variables to inject",
    )

    def get_parameter_dict(self) -> dict[str, ToolParameterValue]:
        """
        Get parameters as a dictionary.

        Returns:
            dict[str, ToolParameterValue]: Parameter name to value mapping
        """
        return self.parameters.get_parameter_dict()

    def get_output_mapping_dict(self) -> dict[str, str]:
        """
        Get output mappings as a dictionary.

        Returns:
            dict[str, str]: Local name to source reference mapping
        """
        return self.from_outputs.get_mapping_dict()


__all__ = ["ModelGraphNodeInputs"]
