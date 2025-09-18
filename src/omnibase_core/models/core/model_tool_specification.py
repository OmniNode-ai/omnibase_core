"""
Tool specification model for ONEX NodeBase contracts.

Provides strongly typed tool specification structure for contract content.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelToolSpecification(BaseModel):
    """Tool specification for NodeBase contract content."""

    model_config = ConfigDict(extra="forbid")

    main_tool_class: str = Field(
        ...,
        description="Main tool class name for the node",
    )
    input_model: str | None = Field(
        None,
        description="Input model class name",
    )
    output_model: str | None = Field(
        None,
        description="Output model class name",
    )
    tool_version: str | None = Field(
        None,
        description="Tool version specification",
    )
    description: str | None = Field(
        None,
        description="Tool description",
    )
