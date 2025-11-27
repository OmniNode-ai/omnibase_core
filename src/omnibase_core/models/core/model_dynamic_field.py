"""Dynamic field model for flexible data without using Any type."""

from pydantic import BaseModel, Field


class ModelDynamicField(BaseModel):
    """
    Represents a dynamic field that can contain various types of data.

    This model provides a type-safe alternative to untyped dict[str, Any]ionaries by
    explicitly defining the allowed field types.
    """

    field_type: str = Field(
        description="Type of the field data (string, number, boolean, list[Any], dict[str, Any], model)",
    )

    string_value: str | None = Field(
        default=None,
        description="String value if field_type is 'string'",
    )

    number_value: int | float | None = Field(
        default=None,
        description="Numeric value if field_type is 'number'",
    )

    boolean_value: bool | None = Field(
        default=None,
        description="Boolean value if field_type is 'boolean'",
    )

    list_value: list["ModelDynamicField"] | None = Field(
        default=None,
        description="List of dynamic fields if field_type is 'list[Any]'",
    )

    dict_value: dict[str, "ModelDynamicField"] | None = Field(
        default=None,
        description="Dictionary of dynamic fields if field_type is 'dict[str, Any]'",
    )

    model_class: str | None = Field(
        default=None,
        description="Pydantic model class name if field_type is 'model'",
    )

    model_data: dict[str, "ModelDynamicField"] | None = Field(
        default=None,
        description="Model field data if field_type is 'model'",
    )


# Update forward references
ModelDynamicField.model_rebuild()
