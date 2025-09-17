"""Model for tool pre-execution hook event."""

from omnibase_core.models.hook_events.model_tool_execution_event import (
    ModelToolExecutionEvent,
)


class ModelToolPreExecutionEvent(ModelToolExecutionEvent):
    """Event fired before tool execution in Claude Code.

    This event captures complete tool parameters and context
    before the tool is executed, enabling real-time context
    injection and parameter analysis.

    Inherits from ModelToolExecutionEvent for clean, consistent structure.
    """

    def __init__(self, **data):
        """Initialize pre-execution event."""
        data["event_type"] = "pre-execution"
        super().__init__(**data)
