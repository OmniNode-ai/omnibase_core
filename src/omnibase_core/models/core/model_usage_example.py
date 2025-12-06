"""
Model for introspection usage examples.

Provides a typed structure for tool usage examples with generic type support.
"""

from pydantic import BaseModel, Field


class ModelUsageExample[InputT, OutputT](BaseModel):
    """Model representing a usage example for introspection with typed input/output."""

    description: str = Field(
        default=...,
        description="Description of what this example demonstrates",
    )
    command: str | None = Field(
        default=None,
        description="Command line example if applicable",
    )
    input_data: InputT | None = Field(default=None, description="Example input data")
    output_data: OutputT | None = Field(
        default=None, description="Expected output data"
    )
    code_snippet: str | None = Field(default=None, description="Python code example")
