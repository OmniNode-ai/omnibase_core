"""
ONEX Model: MCP Session Model

Strongly typed model for MCP session management.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMCPSession(BaseModel):
    """Strongly typed model for MCP session data."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Session creation timestamp",
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now,
        description="Last access timestamp",
    )
    metadata: dict | None = Field(
        default_factory=dict,
        description="Session metadata",
    )
    is_active: bool = Field(default=True, description="Whether session is active")

    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = False
        json_encoders = {datetime: lambda v: v.isoformat()}
