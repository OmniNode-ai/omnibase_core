"""
Model for Pydantic model definition.

This model represents a generated Pydantic model definition,
including its code, imports, and dependencies.
"""

from pydantic import BaseModel, Field


class ModelDefinition(BaseModel):
    """Represents a generated Pydantic model definition."""

    name: str = Field(default=..., description="Name of the model class")
    code: str = Field(default=..., description="Generated Python code for the model")
    imports: set[str] = Field(
        default_factory=set,
        description="Set of import statements needed",
    )
    dependencies: set[str] = Field(
        default_factory=set,
        description="Names of other models this depends on",
    )
