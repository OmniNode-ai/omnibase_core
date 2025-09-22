"""
Connection metrics model for network performance tracking.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics."""

    latency_ms: float = Field(
        default=0.0,
        description="Connection latency in milliseconds",
    )
    throughput_mbps: float = Field(
        default=0.0,
        description="Throughput in Mbps",
    )
    packet_loss_percent: float = Field(
        default=0.0,
        description="Packet loss percentage",
    )
    jitter_ms: float = Field(
        default=0.0,
        description="Jitter in milliseconds",
    )
    bytes_sent: int = Field(
        default=0,
        description="Total bytes sent",
    )
    bytes_received: int = Field(
        default=0,
        description="Total bytes received",
    )
    connections_active: int = Field(
        default=0,
        description="Number of active connections",
    )
    connections_total: int = Field(
        default=0,
        description="Total connections opened",
    )
    errors_count: int = Field(
        default=0,
        description="Number of connection errors",
    )
    timeouts_count: int = Field(
        default=0,
        description="Number of connection timeouts",
    )
