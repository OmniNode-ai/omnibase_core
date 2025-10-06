from pydantic import Field

"""
Connection metrics model for network performance tracking.
"""

from pydantic import BaseModel, Field


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics."""

    latency_ms: float | None = Field(
        None,
        description="Connection latency in milliseconds",
    )
    throughput_mbps: float | None = Field(None, description="Throughput in Mbps")
    packet_loss_percent: float | None = Field(
        None,
        description="Packet loss percentage",
    )
    jitter_ms: float | None = Field(None, description="Jitter in milliseconds")
