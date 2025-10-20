from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelOnexField(BaseModel):
    """
    Canonical, extensible ONEX field model for all flexible/optional/structured node fields.
    Use this for any field that may contain arbitrary or structured data in ONEX nodes.

    Implements ProtocolModelOnexField with field_name, field_value, and field_type attributes.
    """

    # Protocol-required fields
    field_name: str = Field(default="output_field", description="Name of the field")
    field_value: Any = Field(default=None, description="Value stored in the field")
    field_type: str = Field(
        default="generic", description="Type identifier for the field"
    )

    data: dict[str, Any] | None = Field(
        default=None, description="Arbitrary ONEX field data"
    )

    # Optionally, add more required methods or attributes as needed
