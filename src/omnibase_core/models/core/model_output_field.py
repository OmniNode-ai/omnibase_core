from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Re-export from split module
from .model_onex_field_data import ModelOnexFieldData


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


__all__ = ["ModelOnexField", "ModelOnexFieldData"]
