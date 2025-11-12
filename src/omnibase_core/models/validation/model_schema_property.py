"""
SchemaProperty model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_required_fields_model import (
        ModelRequiredFieldsModel,
    )
    from omnibase_core.models.validation.model_schema_properties_model import (
        ModelSchemaPropertiesModel,
    )


class ModelSchemaProperty(BaseModel):
    """
    Strongly typed model for a single property in a JSON schema.
    Includes common JSON Schema fields and is extensible for M1+.
    """

    type: str | None = None
    title: str | None = None
    description: str | None = None
    default: str | int | float | bool | list[Any] | dict[str, Any] | None = None
    enum: list[str | int | float | bool] | None = None
    format: str | None = None
    items: Optional[ModelSchemaProperty] = None
    properties: Optional[ModelSchemaPropertiesModel] = None
    required: Optional[ModelRequiredFieldsModel] = None
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


# Rebuild the model to resolve forward references
def _rebuild_model() -> None:
    """Rebuild the model to resolve forward references."""
    try:
        from .model_required_fields_model import ModelRequiredFieldsModel
        from .model_schema_properties_model import ModelSchemaPropertiesModel

        ModelSchemaProperty.model_rebuild()
    except ImportError:
        # Forward references will be resolved when the modules are imported
        pass


# Call rebuild on module import
_rebuild_model()
