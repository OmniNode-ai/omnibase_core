"""
ModelLogSafeData: Log-safe data representation.

This model provides structured log-safe data without using Any types.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelLogSafeData(BaseModel):
    """Log-safe data representation."""

    service_name: Optional[str] = Field(None, description="Service name")
    connection_status: Optional[str] = Field(None, description="Connection status")
    host_info: Optional[str] = Field(None, description="Host information (masked)")
    port_info: Optional[str] = Field(None, description="Port information")
    username_info: Optional[str] = Field(
        None, description="Username information (masked)"
    )
    additional_fields: Dict[str, str] = Field(
        default_factory=dict, description="Additional masked fields"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Safe metadata fields"
    )
