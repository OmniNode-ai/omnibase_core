"""
ONEX-compliant model for hub event data.

Replaces Dict[str, Any] with strongly typed Pydantic model following ONEX standards.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.hub.model_hub_status import ModelHubStatus
from omnibase_core.model.hub.model_tool_specification import ModelToolSpecification


class ModelHubEventData(BaseModel):
    """
    Hub event data model for event bus communications.

    Replaces Dict[str, Any] usage with strongly typed ONEX-compliant structure.
    Uses Union types to handle different event payload types while avoiding Any.
    """

    event_type: str = Field(..., description="Type of hub event")
    hub_id: str = Field(..., description="Hub identifier that generated the event")
    timestamp: float = Field(..., description="Event timestamp")

    # Event-specific payload using Union types instead of Any
    tool_spec: ModelToolSpecification | None = Field(
        None,
        description="Tool specification for tool-related events",
    )
    hub_status: ModelHubStatus | None = Field(
        None,
        description="Hub status for status events",
    )
    tool_name: str | None = Field(
        None,
        description="Tool name for tool-specific events",
    )
    error_message: str | None = Field(
        None,
        description="Error message for error events",
    )
    success: bool | None = Field(
        None,
        description="Success indicator for operation events",
    )

    # Generic data for custom events (using Union instead of Any)
    custom_data: str | int | float | bool | dict | list | None = Field(
        None,
        description="Custom event data with strongly typed values",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "event_type": "tool_loaded",
                "hub_id": "generation_hub_001",
                "timestamp": 1690728000.0,
                "tool_spec": {
                    "name": "tool_example_processor",
                    "version": {"major": 1, "minor": 0, "patch": 0},
                    "path": "/omnibase/tools/processing/tool_example_processor/v1_0_0",
                    "capabilities": ["processing"],
                },
                "success": True,
            },
        }
