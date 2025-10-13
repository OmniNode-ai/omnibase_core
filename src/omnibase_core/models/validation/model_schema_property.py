from typing import Any, Optional

from pydantic import Field

"""
SchemaProperty model.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from .model_schema import ModelRequiredFieldsModel, ModelSchemaPropertiesModel


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
    items: Optional["ModelSchemaProperty"] = None
    properties: Optional["ModelSchemaPropertiesModel"] = None
    required: Optional["ModelRequiredFieldsModel"] = None
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


# Rebuild the model to resolve forward references
def _rebuild_model():
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
