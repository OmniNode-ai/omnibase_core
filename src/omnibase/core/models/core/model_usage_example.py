"""
Model for introspection usage examples.

Provides a typed structure for tool usage examples with generic type support.
"""

from typing import Generic, Optional, TypeVar

from pydantic import Field
from pydantic.generics import GenericModel

# Type variables for input and output types
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ModelUsageExample(GenericModel, Generic[InputT, OutputT]):
    """Model representing a usage example for introspection with typed input/output."""

    description: str = Field(
        ..., description="Description of what this example demonstrates"
    )
    command: Optional[str] = Field(
        None, description="Command line example if applicable"
    )
    input_data: Optional[InputT] = Field(None, description="Example input data")
    output_data: Optional[OutputT] = Field(None, description="Expected output data")
    code_snippet: Optional[str] = Field(None, description="Python code example")

    class Config:
        extra = "forbid"
