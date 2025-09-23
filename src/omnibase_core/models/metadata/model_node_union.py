"""
Node Union Model.

Discriminated union for function node types following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...exceptions.onex_error import OnexError
from ..nodes.model_function_node import ModelFunctionNode
from .model_function_node_data import ModelFunctionNodeData


class ModelNodeUnion(BaseModel):
    """
    Discriminated union for function node types.

    Replaces ModelFunctionNode | ModelFunctionNodeData union with structured typing.
    """

    node_type: Literal["function_node", "function_node_data"] = Field(
        description="Type discriminator for node value"
    )

    # Node storage (only one should be populated)
    function_node: ModelFunctionNode | None = None
    function_node_data: ModelFunctionNodeData | None = None

    @model_validator(mode="after")
    def validate_single_node(self) -> "ModelNodeUnion":
        """Ensure only one node value is set based on type discriminator."""
        if self.node_type == "function_node":
            if self.function_node is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node must be set when node_type is 'function_node'",
                )
            if self.function_node_data is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node_data must be None when node_type is 'function_node'",
                )
        elif self.node_type == "function_node_data":
            if self.function_node_data is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node_data must be set when node_type is 'function_node_data'",
                )
            if self.function_node is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node must be None when node_type is 'function_node_data'",
                )

        return self

    @classmethod
    def from_function_node(cls, node: ModelFunctionNode) -> "ModelNodeUnion":
        """Create union from function node."""
        return cls(node_type="function_node", function_node=node)

    @classmethod
    def from_function_node_data(
        cls, node_data: ModelFunctionNodeData
    ) -> "ModelNodeUnion":
        """Create union from function node data."""
        return cls(node_type="function_node_data", function_node_data=node_data)

    def get_node(self) -> Any:
        """Get the actual node value.

        Returns:
            ModelFunctionNode or ModelFunctionNodeData based on node_type discriminator.
        """
        if self.node_type == "function_node":
            assert self.function_node is not None  # Guaranteed by validator
            return self.function_node
        else:
            assert self.function_node_data is not None  # Guaranteed by validator
            return self.function_node_data


# Export the model
__all__ = ["ModelNodeUnion"]
