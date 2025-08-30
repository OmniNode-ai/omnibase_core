"""ModelRoutingContext: Routing context for cross-component coordination"""

from pydantic import BaseModel, Field


class ModelRoutingContext(BaseModel):
    """Routing context for cross-component coordination"""

    target_services: list[str] = Field(
        default_factory=list,
        description="List of target service identifiers",
    )
    routing_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value routing hints",
    )
    reply_to_topic: str | None = Field(None, description="Topic for response events")
