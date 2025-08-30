"""ModelRoutingMetrics: Strongly typed routing performance metrics"""

from pydantic import BaseModel, Field


class ModelRoutingMetrics(BaseModel):
    """Strongly typed routing performance metrics"""

    total_events_processed: int = Field(
        ...,
        description="Total number of events processed",
    )
    events_routed: int = Field(..., description="Number of events successfully routed")
    events_dropped: int = Field(..., description="Number of events dropped")
    average_processing_time_ms: float = Field(
        ...,
        description="Average processing time in milliseconds",
    )
    total_routes_registered: int = Field(
        ...,
        description="Total number of registered routes",
    )
    active_routes: int = Field(..., description="Number of currently active routes")
    error_count: int = Field(..., description="Number of routing errors encountered")
    throughput_events_per_second: float = Field(
        ...,
        description="Current throughput in events per second",
    )
