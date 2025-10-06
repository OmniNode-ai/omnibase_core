from pydantic import BaseModel, Field


class ModelResourceMetrics(BaseModel):
    """Resource usage metrics for an agent."""

    cpu_percent: float = Field(description="CPU usage percentage (0-100)")
    memory_mb: float = Field(description="Memory usage in megabytes")
    disk_usage_mb: float = Field(description="Disk usage in megabytes")
    network_bytes_sent: int = Field(description="Network bytes sent since start")
    network_bytes_received: int = Field(
        description="Network bytes received since start",
    )
    api_requests_count: int = Field(description="Number of API requests made")
    api_tokens_used: int = Field(description="Total API tokens consumed")
