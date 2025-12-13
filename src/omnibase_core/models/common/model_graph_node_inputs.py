"""
Typed inputs model for graph nodes.

This module provides strongly-typed inputs for graph node patterns.
"""

from pydantic import BaseModel, Field


class ModelGraphNodeInputs(BaseModel):
    """
    Typed inputs for graph nodes.

    Replaces dict[str, Any] inputs field in ModelGraphNode
    with explicit typed fields for graph node inputs.
    """

    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Input parameters as key-value pairs",
    )
    from_outputs: dict[str, str] = Field(
        default_factory=dict,
        description="Mappings from other node outputs",
    )
    constants: dict[str, str] = Field(
        default_factory=dict,
        description="Constant input values",
    )
    environment_vars: list[str] = Field(
        default_factory=list,
        description="Environment variables to inject",
    )


__all__ = ["ModelGraphNodeInputs"]
