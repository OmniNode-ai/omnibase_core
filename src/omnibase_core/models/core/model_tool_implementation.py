"""
Model for tool implementation references.

Represents a resolved tool implementation without requiring direct imports,
enabling protocol-based tool execution while maintaining type safety.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelToolImplementation(BaseModel):
    """
    Model representing a resolved tool implementation.

    This model provides type safety for tool implementations without
    requiring direct imports, enabling protocol-based execution.
    """

    # Implementation identification
    tool_name: str = Field(default=..., description="Name of the resolved tool")
    implementation_class: str = Field(
        default=...,
        description="Class name of the tool implementation",
    )
    module_path: str = Field(
        default=...,
        description="Python module path to the implementation",
    )

    # Implementation metadata
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the tool implementation",
    )
    registry_source: str = Field(
        default=...,
        description="Registry that provided this implementation",
    )

    # Duck typing support
    has_process_method: bool = Field(
        default=True,
        description="Whether the implementation has a process() method",
    )
    accepts_input_state: bool = Field(
        default=True,
        description="Whether the implementation accepts input state models",
    )
    returns_output_state: bool = Field(
        default=True,
        description="Whether the implementation returns output state models",
    )

    # Health and validation
    is_healthy: bool = Field(
        default=True, description="Whether the implementation is healthy"
    )
    health_message: str | None = Field(
        default=None,
        description="Health status message if unhealthy",
    )

    # Instance reference (opaque for serialization safety)
    instance_available: bool = Field(
        default=False,
        description="Whether a live instance is available",
    )
