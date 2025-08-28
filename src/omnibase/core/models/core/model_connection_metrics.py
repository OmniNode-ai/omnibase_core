"""
Connection metrics model for network performance tracking.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics."""

    latency_ms: Optional[float] = Field(
        None, description="Connection latency in milliseconds"
    )
    throughput_mbps: Optional[float] = Field(None, description="Throughput in Mbps")
    packet_loss_percent: Optional[float] = Field(
        None, description="Packet loss percentage"
    )
    jitter_ms: Optional[float] = Field(None, description="Jitter in milliseconds")
