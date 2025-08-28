"""
Model for schema to Pydantic conversion result.

This model contains the results of converting schemas to Pydantic
model definitions.
"""

from typing import Dict, List, Set

from pydantic import BaseModel, Field

from omnibase.model.core.model_definition import ModelDefinition


class ModelSchemaToPydanticResult(BaseModel):
    """Result of schema to Pydantic conversion."""

    models: Dict[str, ModelDefinition] = Field(
        default_factory=dict, description="Generated models by name"
    )
    enums: Dict[str, str] = Field(
        default_factory=dict, description="Generated enum definitions by name"
    )
    imports: Set[str] = Field(
        default_factory=set, description="All import statements needed"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of conversion errors"
    )
