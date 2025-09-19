"""
Connection metrics model for network performance tracking.
"""

from pydantic import BaseModel, Field


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics."""

    latency_ms: float | None = Field(
        default=None,
        description="Connection latency in milliseconds",
    )
    throughput_mbps: float | None = Field(
        default=None,
        description="Throughput in Mbps",
    )
    packet_loss_percent: float | None = Field(
        default=None,
        description="Packet loss percentage",
    )
    jitter_ms: float | None = Field(
        default=None,
        description="Jitter in milliseconds",
    )
    bytes_sent: int | None = Field(
        default=None,
        description="Total bytes sent",
    )
    bytes_received: int | None = Field(
        default=None,
        description="Total bytes received",
    )
    connections_active: int | None = Field(
        default=None,
        description="Number of active connections",
    )
    connections_total: int | None = Field(
        default=None,
        description="Total connections opened",
    )
    errors_count: int | None = Field(
        default=None,
        description="Number of connection errors",
    )
    timeouts_count: int | None = Field(
        default=None,
        description="Number of connection timeouts",
    )
