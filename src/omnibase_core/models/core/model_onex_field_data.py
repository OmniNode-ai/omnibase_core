"""ONEX field data model."""

from pydantic import BaseModel, ConfigDict, Field


class ModelOnexFieldData(BaseModel):
    """Structured data for ONEX fields."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

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
