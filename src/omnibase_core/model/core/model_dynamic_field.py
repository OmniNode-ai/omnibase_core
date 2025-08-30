"""Dynamic field model for flexible data without using Any type."""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelDynamicField(BaseModel):
    """
    Represents a dynamic field that can contain various types of data.

    This model provides a type-safe alternative to untyped dictionaries by
    explicitly defining the allowed field types.
    """

    field_type: str = Field(
        description="Type of the field data (string, number, boolean, list, dict, model)"
    )

    string_value: Optional[str] = Field(
        default=None, description="String value if field_type is 'string'"
    )

    number_value: Optional[Union[int, float]] = Field(
        default=None, description="Numeric value if field_type is 'number'"
    )

    boolean_value: Optional[bool] = Field(
        default=None, description="Boolean value if field_type is 'boolean'"
    )

    list_value: Optional[List["ModelDynamicField"]] = Field(
        default=None, description="List of dynamic fields if field_type is 'list'"
    )

    dict_value: Optional[Dict[str, "ModelDynamicField"]] = Field(
        default=None, description="Dictionary of dynamic fields if field_type is 'dict'"
    )

    model_class: Optional[str] = Field(
        default=None, description="Pydantic model class name if field_type is 'model'"
    )

    model_data: Optional[Dict[str, "ModelDynamicField"]] = Field(
        default=None, description="Model field data if field_type is 'model'"
    )


# Update forward references
ModelDynamicField.model_rebuild()
