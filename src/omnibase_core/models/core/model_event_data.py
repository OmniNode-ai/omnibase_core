"""
Event data models.

Provides typed models for event payload data,
replacing dict[str, Any] patterns in event models.
"""

from pydantic import BaseModel, Field


class ModelEventData(BaseModel):
    """
    Typed model for event payload data.

    Replaces dict[str, Any] data field in ModelOnexEvent with
    strongly-typed fields for common event data patterns.
    """

    # String data fields
    string_data: dict[str, str] = Field(
        default_factory=dict,
        description="String data fields",
    )
    # Integer data fields
    int_data: dict[str, int] = Field(
        default_factory=dict,
        description="Integer data fields",
    )
    # Float data fields
    float_data: dict[str, float] = Field(
        default_factory=dict,
        description="Float data fields",
    )
    # Boolean data fields
    bool_data: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean data fields",
    )
    # List data fields
    list_data: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List data fields",
    )

    # Common event fields
    source: str | None = Field(
        default=None,
        description="Event source identifier",
    )
    target: str | None = Field(
        default=None,
        description="Event target identifier",
    )
    action: str | None = Field(
        default=None,
        description="Action performed",
    )
    status: str | None = Field(
        default=None,
        description="Status of the event",
    )
    message: str | None = Field(
        default=None,
        description="Event message",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code if applicable",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if applicable",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string data field."""
        return self.string_data.get(key, default)

    def set_string(self, key: str, value: str) -> None:
        """Set a string data field."""
        self.string_data[key] = value


__all__ = ["ModelEventData"]
