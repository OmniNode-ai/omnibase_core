"""
Typed inputs model for graph nodes.

This module provides strongly-typed inputs for graph node patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphNodeInputs(BaseModel):
    """
    Typed inputs for graph nodes.

    Replaces dict[str, Any] inputs field in ModelGraphNode
    with explicit typed fields for graph node inputs.

    Note: Fields use dict[str, str] per ONEX strict typing standards.
    For complex values, serialize to JSON strings.
    """

    model_config = ConfigDict(extra="forbid")

    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Input parameters as key-value string pairs",
    )
    from_outputs: dict[str, str] = Field(
        default_factory=dict,
        description="Mappings from other node outputs (node_id.output_name -> local_name)",
    )
    constants: dict[str, str] = Field(
        default_factory=dict,
        description="Constant input values as strings",
    )
    environment_vars: list[str] = Field(
        default_factory=list,
        description="Environment variables to inject",
    )


__all__ = ["ModelGraphNodeInputs"]
