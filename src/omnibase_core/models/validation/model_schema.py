"""Schema validation models."""

from .model_required_fields_model import ModelRequiredFieldsModel
from .model_schema_class import ModelSchema
from .model_schema_properties_model import ModelSchemaPropertiesModel
from .model_schema_property import ModelSchemaProperty

# Compatibility aliases
SchemaPropertyModel = ModelSchemaProperty
SchemaPropertiesModel = ModelSchemaPropertiesModel
RequiredFieldsModel = ModelRequiredFieldsModel
SchemaModel = ModelSchema

__all__ = [
    "ModelSchema",
    "ModelSchemaPropertiesModel",
    "ModelRequiredFieldsModel",
    "SchemaPropertyModel",
    "SchemaPropertiesModel",
    "RequiredFieldsModel",
    "SchemaModel",
]
