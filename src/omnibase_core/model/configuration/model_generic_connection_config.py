"""
Model for generic connection configuration.

This model serves as a fallback for unknown service types,
providing a flexible but still typed structure.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelGenericConnectionConfig(BaseModel):
    """Generic connection configuration for unknown service types."""

    host: Optional[str] = Field(default=None, description="Service host")
    port: Optional[int] = Field(default=None, description="Service port")
    url: Optional[str] = Field(default=None, description="Connection URL")
    auth_type: Optional[str] = Field(default=None, description="Authentication type")
    credentials: Optional[Dict[str, str]] = Field(
        default=None, description="Authentication credentials"
    )
    options: Optional[Dict[str, str]] = Field(
        default=None, description="Additional connection options"
    )
    timeout_seconds: Optional[int] = Field(
        default=30, description="Connection timeout in seconds"
    )

    class Config:
        extra = "allow"  # Allow additional fields for flexibility
