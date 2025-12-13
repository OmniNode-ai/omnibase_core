"""
Event channels model for node introspection.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventChannels(BaseModel):
    """Model for event channel specification in introspection."""

    subscribes_to: list[str] = Field(
        default_factory=list,
        description="Event channels this node subscribes to for receiving events",
    )
    publishes_to: list[str] = Field(
        default_factory=list,
        description="Event channels this node publishes events to",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "subscribes_to": [
                        "onex.discovery.broadcast",
                        "onex.registry.query",
                        "onex.node.health_check",
                    ],
                    "publishes_to": [
                        "onex.discovery.response",
                        "onex.registry.update",
                        "onex.node.status",
                    ],
                },
            ],
        },
    )
