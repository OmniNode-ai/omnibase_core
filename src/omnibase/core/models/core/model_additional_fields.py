"""
Additional Fields Model for ONEX Configuration System.

Strongly typed model for additional metadata fields.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelAdditionalFields(BaseModel):
    """
    Strongly typed model for additional metadata fields.

    Represents additional fields passed to metadata block creation.
    """

    uuid: Optional[str] = Field(default=None, description="Optional UUID override")
    created_at: Optional[str] = Field(
        default=None, description="Optional created_at override"
    )
    tools: Optional[str] = Field(
        default=None, description="Optional tools configuration"
    )
    metadata_version: Optional[str] = Field(
        default=None, description="Optional metadata version override"
    )
    protocol_version: Optional[str] = Field(
        default=None, description="Optional protocol version override"
    )
    schema_version: Optional[str] = Field(
        default=None, description="Optional schema version override"
    )

    def get_field(self, field_name: str) -> Optional[str]:
        """Get a field value by name."""
        return getattr(self, field_name, None)

    def has_field(self, field_name: str) -> bool:
        """Check if field exists and is not None."""
        return getattr(self, field_name, None) is not None

    def remove_field(self, field_name: str) -> None:
        """Remove a field by setting it to None."""
        if hasattr(self, field_name):
            setattr(self, field_name, None)
