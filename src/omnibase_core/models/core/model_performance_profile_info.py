"""
PerformanceProfileInfo model for node introspection.
"""

from pydantic import BaseModel


class ModelPerformanceProfileInfo(BaseModel):
    """Model for performance profile information."""

    cpu: float | None = None
    memory: float | None = None
    disk: float | None = None
    throughput: float | None = None
    latency_ms: float | None = None
    notes: str | None = None
    # Add more fields as needed for protocol
