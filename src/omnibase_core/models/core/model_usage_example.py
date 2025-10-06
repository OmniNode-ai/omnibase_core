from typing import TypeVar

"""
Model for introspection usage examples.

Provides a typed structure for tool usage examples with generic type support.
"""

from typing import Generic, TypeVar

from pydantic import Field
from pydantic.generics import GenericModel

from .model_usage_example_config import ModelConfig

# Type variables for input and output types
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ModelUsageExample(GenericModel, Generic[InputT, OutputT]):
    """Model representing a usage example for introspection with typed input/output."""

    description: str = Field(
        ...,
        description="Description of what this example demonstrates",
    )
    command: str | None = Field(
        None,
        description="Command line example if applicable",
    )
    input_data: InputT | None = Field(None, description="Example input data")
    output_data: OutputT | None = Field(None, description="Expected output data")
    code_snippet: str | None = Field(None, description="Python code example")
