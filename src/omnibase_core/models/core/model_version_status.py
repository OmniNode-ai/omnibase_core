"""
VersionStatus model for node introspection.
"""

from pydantic import BaseModel


class ModelVersionStatus(BaseModel):
    """Model for version status information."""

    latest: str | None = None
    supported: list[str] | None = None
    deprecated: list[str] | None = None
    # Add more fields as needed for protocol
