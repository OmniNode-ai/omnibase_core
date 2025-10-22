from typing import TypeVar

"""
Model for introspection usage examples.

Provides a typed structure for tool usage examples with generic type support.
"""

from typing import Generic

from pydantic import BaseModel, Field

from .model_usage_example_config import ModelConfig

# Type variables for input and output types
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ModelUsageExample(BaseModel, Generic[InputT, OutputT]):
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
