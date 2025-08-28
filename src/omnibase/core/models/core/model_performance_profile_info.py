"""
PerformanceProfileInfo model for node introspection.
"""

from typing import Optional

from pydantic import BaseModel


class ModelPerformanceProfileInfo(BaseModel):
    """Model for performance profile information."""

    cpu: Optional[float] = None
    memory: Optional[float] = None
    disk: Optional[float] = None
    throughput: Optional[float] = None
    latency_ms: Optional[float] = None
    notes: Optional[str] = None
    # Add more fields as needed for protocol
