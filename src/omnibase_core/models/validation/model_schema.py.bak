"""Schema validation models and compatibility aliases.

This module provides a consolidated interface for all schema-related models,
including compatibility aliases for consistent naming.
"""

from omnibase_core.models.validation.model_required_fields_model import (
    ModelRequiredFieldsModel,
    RequiredFieldsModel,
)
from omnibase_core.models.validation.model_schema_class import ModelSchema, SchemaModel
from omnibase_core.models.validation.model_schema_properties_model import (
    ModelSchemaPropertiesModel,
    SchemaPropertiesModel,
)
from omnibase_core.models.validation.model_schema_property import ModelSchemaProperty

# Additional compatibility alias for ModelSchemaProperty
SchemaPropertyModel = ModelSchemaProperty

# Rebuild models to resolve forward references now that all models are imported
ModelSchemaProperty.model_rebuild()
ModelSchemaPropertiesModel.model_rebuild()
ModelSchema.model_rebuild()

__all__ = [
    "ModelSchema",
    "ModelSchemaPropertiesModel",
    "ModelRequiredFieldsModel",
    "SchemaPropertyModel",
    "SchemaPropertiesModel",
    "RequiredFieldsModel",
    "SchemaModel",
]
