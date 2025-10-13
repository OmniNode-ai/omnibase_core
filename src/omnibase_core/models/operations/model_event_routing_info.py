from pydantic import BaseModel, Field


class ModelEventRoutingInfo(BaseModel):
    """Structured event routing information."""

    target_queue: str = Field(default="", description="Target message queue or topic")
    routing_key: str = Field(default="", description="Message routing key")
    priority: str = Field(default="normal", description="Routing priority level")
    broadcast: bool = Field(default=False, description="Whether to broadcast event")
    retry_routing: bool = Field(
        default=True,
        description="Enable routing retry on failure",
    )
    dead_letter_queue: str = Field(
        default="",
        description="Dead letter queue for failed routing",
    )
