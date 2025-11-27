"""ModelSchema Class.

Strongly typed Pydantic model for ONEX JSON schema files.
Includes canonical fields and is extensible for M1+.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.models.validation.model_required_fields_model import (
    ModelRequiredFieldsModel,
)
from omnibase_core.models.validation.model_schema_properties_model import (
    ModelSchemaPropertiesModel,
)


class ModelSchema(BaseModel):
    """
    Strongly typed Pydantic model for ONEX JSON schema files.
    Includes canonical fields and is extensible for M1+.
    """

    schema_uri: str | None = Field(None)
    title: str | None = None
    type: str | None = None
    properties: ModelSchemaPropertiesModel | None = None
    required: ModelRequiredFieldsModel | None = None
    # TODO: Add more fields and validation logic in M1+


# Compatibility aliases
SchemaModel = ModelSchema
