"""Model for tool post-execution hook event."""

from omnibase_core.model.hook_events.model_tool_execution_event import (
    ModelToolExecutionEvent,
)


class ModelToolPostExecutionEvent(ModelToolExecutionEvent):
    """Event fired after tool execution in Claude Code.

    This event captures tool execution results, timing, and
    success/failure status for comprehensive tool usage analytics
    and learning.

    Inherits from ModelToolExecutionEvent for clean, consistent structure.
    """

    def __init__(self, **data):
        """Initialize post-execution event."""
        data["event_type"] = "post-execution"
        super().__init__(**data)
