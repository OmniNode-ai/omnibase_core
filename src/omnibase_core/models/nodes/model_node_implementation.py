"""
Model for node implementation references.

Represents a resolved node implementation without requiring direct imports,
enabling protocol-based node execution while maintaining type safety.
"""

from pydantic import BaseModel, Field


class ModelNodeImplementation(BaseModel):
    """
    Model representing a resolved node implementation.

    This model provides type safety for node implementations without
    requiring direct imports, enabling protocol-based execution.
    """

    # Implementation identification
    node_name: str = Field(..., description="Name of the resolved node")
    implementation_class: str = Field(
        ...,
        description="Class name of the node implementation",
    )
    module_path: str = Field(
        ...,
        description="Python module path to the implementation",
    )

    # Implementation metadata
    version: str = Field(..., description="Version of the node implementation")
    registry_source: str = Field(
        ...,
        description="Registry that provided this implementation",
    )

    # Duck typing support
    has_process_method: bool = Field(
        True,
        description="Whether the implementation has a process() method",
    )
    accepts_input_state: bool = Field(
        True,
        description="Whether the implementation accepts input state models",
    )
    returns_output_state: bool = Field(
        True,
        description="Whether the implementation returns output state models",
    )

    # Health and validation
    is_healthy: bool = Field(True, description="Whether the implementation is healthy")
    health_message: str | None = Field(
        None,
        description="Health status message if unhealthy",
    )

    # Instance reference (opaque for serialization safety)
    instance_available: bool = Field(
        False,
        description="Whether a live instance is available",
    )

    class Config:
        """Pydantic configuration."""

        # Allow serialization even with complex types
        arbitrary_types_allowed = True

        # Example for documentation
        json_schema_extra = {
            "example": {
                "node_name": "node_file_generator",
                "implementation_class": "NodeFileGenerator",
                "module_path": "protocol.nodes.example.node_example",
                "version": "1.0.0",
                "registry_source": "RegistryFileGenerator",
                "has_process_method": True,
                "accepts_input_state": True,
                "returns_output_state": True,
                "is_healthy": True,
                "health_message": None,
                "instance_available": True,
            },
        }
