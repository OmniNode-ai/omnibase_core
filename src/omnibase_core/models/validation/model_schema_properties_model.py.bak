"""ModelSchemaPropertiesModel.

Strongly typed model for the properties field in a JSON schema.
Wraps a dict[str, Any]of property names to SchemaPropertyModel.
"""

from typing import Any

from pydantic import RootModel

from omnibase_core.models.validation.model_schema_property import ModelSchemaProperty


class ModelSchemaPropertiesModel(RootModel[Any]):
    """
    Strongly typed model for the properties field in a JSON schema.
    Wraps a dict[str, Any]of property names to SchemaPropertyModel.
    """

    root: dict[str, ModelSchemaProperty]


# Compatibility alias
SchemaPropertiesModel = ModelSchemaPropertiesModel
