"""
ModelLogSafeData: Log-safe data representation.

This model provides structured log-safe data without using Any types.
"""

from pydantic import BaseModel, Field


class ModelLogSafeData(BaseModel):
    """Log-safe data representation."""

    service_name: str | None = Field(default=None, description="Service name")
    connection_status: str | None = Field(default=None, description="Connection status")
    host_info: str | None = Field(default=None, description="Host information (masked)")
    port_info: str | None = Field(default=None, description="Port information")
    username_info: str | None = Field(
        default=None,
        description="Username information (masked)",
    )
    additional_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional masked fields",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Safe metadata fields",
    )
