"""
Model for schema to Pydantic conversion result.

This model contains the results of converting schemas to Pydantic
model definitions.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_definition import ModelDefinition


class ModelSchemaToPydanticResult(BaseModel):
    """Result of schema to Pydantic conversion."""

    models: dict[str, ModelDefinition] = Field(
        default_factory=dict,
        description="Generated models by name",
    )
    enums: dict[str, str] = Field(
        default_factory=dict,
        description="Generated enum definitions by name",
    )
    imports: set[str] = Field(
        default_factory=set,
        description="All import statements needed",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of conversion errors",
    )
