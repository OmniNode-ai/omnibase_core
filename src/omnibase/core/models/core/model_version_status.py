"""
VersionStatus model for node introspection.
"""

from typing import List, Optional

from pydantic import BaseModel


class ModelVersionStatus(BaseModel):
    """Model for version status information."""

    latest: Optional[str] = None
    supported: Optional[List[str]] = None
    deprecated: Optional[List[str]] = None
    # Add more fields as needed for protocol
