"""Parsed node model."""

from pydantic import BaseModel, Field


class ModelParsedNode(BaseModel):
    """Result of parsing enhanced node configuration."""

    id: str = Field(..., description="Node identifier")
    tool: str = Field(..., description="Tool name")
    inputs: list[str] | None = Field(default=None, description="Input dependencies")
    parameters: str | list[str] | None = Field(
        default=None,
        description="Node parameters",
    )
    retry_config: str | None = Field(
        default=None,
        description="Retry configuration data",
    )
    conditional_config: str | None = Field(
        default=None,
        description="Conditional configuration data",
    )
    loop_config: str | None = Field(
        default=None,
        description="Loop configuration data",
    )
