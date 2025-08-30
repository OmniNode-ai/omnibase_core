"""
ONEX Model: Tool Execution State Model

Strongly typed model for tool execution state management.
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class ModelToolExecutionState(BaseModel):
    """Strongly typed model for tool execution state."""

    conversation_buffer: list[dict] = Field(
        default_factory=list,
        description="Buffer of conversation interactions",
    )
    current_user_message: str = Field(default="", description="Current user message")
    current_task_context: str = Field(default="", description="Current task context")
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Session ID",
    )
    tools_used_in_interaction: list[str] = Field(
        default_factory=list,
        description="Tools used in current interaction",
    )
    interaction_start_time: datetime | None = Field(
        None,
        description="Start time of current interaction",
    )

    def reset_interaction(self) -> None:
        """Reset the current interaction state."""
        self.tools_used_in_interaction = []
        self.interaction_start_time = None
        self.current_user_message = ""
        self.current_task_context = ""

    def start_interaction(self, user_message: str = "", task_context: str = "") -> None:
        """Start a new interaction."""
        self.reset_interaction()
        self.current_user_message = user_message
        self.current_task_context = task_context
        self.interaction_start_time = datetime.now()

    def add_tool_usage(self, tool_name: str) -> None:
        """Record that a tool was used."""
        if tool_name not in self.tools_used_in_interaction:
            self.tools_used_in_interaction.append(tool_name)
