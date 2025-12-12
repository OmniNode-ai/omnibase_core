from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelOnexFieldData(BaseModel):
    """Structured data for ONEX fields."""

    string_values: dict[str, str] = Field(
        default_factory=dict, description="String key-value pairs"
    )
    numeric_values: dict[str, float] = Field(
        default_factory=dict, description="Numeric key-value pairs"
    )
    boolean_values: dict[str, bool] = Field(
        default_factory=dict, description="Boolean key-value pairs"
    )
    list_values: dict[str, list[str]] = Field(
        default_factory=dict, description="List key-value pairs"
    )


class ModelOnexField(BaseModel):
    """
    Canonical, extensible ONEX field model for all flexible/optional/structured node fields.
    Use this for any field that may contain arbitrary or structured data in ONEX nodes.

    Implements ProtocolModelOnexField with field_name, field_value, and field_type attributes.
    """

    # Protocol-required fields
    field_name: str = Field(default="output_field", description="Name of the field")
    field_value: ModelSchemaValue | None = Field(
        default=None, description="Value stored in the field"
    )
    field_type: str = Field(
        default="generic", description="Type identifier for the field"
    )

    data: ModelOnexFieldData | None = Field(
        default=None, description="Structured ONEX field data"
    )

    # Optionally, add more required methods or attributes as needed
