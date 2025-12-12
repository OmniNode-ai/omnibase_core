from __future__ import annotations

from pydantic import Field, model_validator

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Node Union Model.

Discriminated union for function node types following ONEX one-model-per-file architecture.
"""


from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_union_type import EnumNodeUnionType
from omnibase_core.models.node_metadata.model_function_node import ModelFunctionNode
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_function_node_data import ModelFunctionNodeData


class ModelNodeUnion(BaseModel):
    """
    Discriminated union for function node types.

    Replaces ModelFunctionNode | ModelFunctionNodeData union with structured typing.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    node_type: EnumNodeUnionType = Field(
        description="Type discriminator for node value",
    )

    # Node storage (only one should be populated)
    function_node: ModelFunctionNode | None = None
    function_node_data: ModelFunctionNodeData | None = None

    @model_validator(mode="after")
    def validate_single_node(self) -> ModelNodeUnion:
        """Ensure only one node value is set based on type discriminator."""
        if self.node_type == EnumNodeUnionType.FUNCTION_NODE:
            if self.function_node is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node must be set when node_type is 'function_node'",
                )
            if self.function_node_data is not None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node_data must be None when node_type is 'function_node'",
                )
        elif self.node_type == EnumNodeUnionType.FUNCTION_NODE_DATA:
            if self.function_node_data is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node_data must be set when node_type is 'function_node_data'",
                )
            if self.function_node is not None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="function_node must be None when node_type is 'function_node_data'",
                )

        return self

    @classmethod
    def from_function_node(cls, node: ModelFunctionNode) -> ModelNodeUnion:
        """Create union from function node."""
        return cls(node_type=EnumNodeUnionType.FUNCTION_NODE, function_node=node)

    @classmethod
    def from_function_node_data(
        cls,
        node_data: ModelFunctionNodeData,
    ) -> ModelNodeUnion:
        """Create union from function node data."""
        return cls(
            node_type=EnumNodeUnionType.FUNCTION_NODE_DATA,
            function_node_data=node_data,
        )

    def get_node(self) -> ModelFunctionNode | ModelFunctionNodeData:
        """
        Get the actual node value with runtime type safety.

        Returns:
            ModelFunctionNode | ModelFunctionNodeData: Either ModelFunctionNode or
                          ModelFunctionNodeData based on node_type discriminator.
                          Use isinstance() to check specific type.

        Raises:
            ModelOnexError: If discriminator state is invalid

        Examples:
            node = union.get_node()
            if isinstance(node, ModelFunctionNode):
                # Handle function node
                pass
            elif isinstance(node, ModelFunctionNodeData):
                # Handle function node data
                pass
        """
        if self.node_type == EnumNodeUnionType.FUNCTION_NODE:
            if self.function_node is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Invalid state: function_node is None but node_type is FUNCTION_NODE",
                )
            return self.function_node
        if self.node_type == EnumNodeUnionType.FUNCTION_NODE_DATA:
            if self.function_node_data is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Invalid state: function_node_data is None but node_type is FUNCTION_NODE_DATA",
                )
            return self.function_node_data
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown node_type: {self.node_type}",
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


__all__ = ["ModelNodeUnion"]
