"""
SchemaProperty model.
"""

from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel

if TYPE_CHECKING:
    from .model_schema import (ModelRequiredFieldsModel,
                               ModelSchemaPropertiesModel)


class ModelSchemaProperty(BaseModel):
    """
    Strongly typed model for a single property in a JSON schema.
    Includes common JSON Schema fields and is extensible for M1+.
    """

    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Union[str, int, float, bool, list, dict]] = None
    enum: Optional[List[Union[str, int, float, bool]]] = None
    format: Optional[str] = None
    items: Optional["ModelSchemaProperty"] = None
    properties: Optional["ModelSchemaPropertiesModel"] = None
    required: Optional["ModelRequiredFieldsModel"] = None
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
