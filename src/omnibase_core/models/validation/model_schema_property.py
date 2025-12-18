"""
SchemaProperty model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from omnibase_core.types.json_types import JsonValue, PrimitiveValue
from omnibase_core.utils.util_decorators import allow_dict_str_any

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_required_fields_model import (
        ModelRequiredFieldsModel,
    )
    from omnibase_core.models.validation.model_schema_properties_model import (
        ModelSchemaPropertiesModel,
    )


@allow_dict_str_any(
    "Schema property default field accepts dict[str, Any] for JSON schema "
    "default value compatibility with complex nested structures."
)
class ModelSchemaProperty(BaseModel):
    """
    Strongly typed model for a single property in a JSON schema.
    Includes common JSON Schema fields and is extensible for M1+.
    """

    type: str | None = None
    title: str | None = None
    description: str | None = None
    default: JsonValue = None
    enum: list[PrimitiveValue] | None = None
    format: str | None = None
    items: ModelSchemaProperty | None = None
    properties: ModelSchemaPropertiesModel | None = None
    required: ModelRequiredFieldsModel | None = None
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
