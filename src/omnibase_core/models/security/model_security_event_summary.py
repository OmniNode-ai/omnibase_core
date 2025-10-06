"""
Security Event Summary Model.

Security event summary with basic event information.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.security.model_security_summary import (
        ModelSecuritySummary,
    )


class ModelSecurityEventSummary(BaseModel):
    """Security event summary."""

    event_id: str = Field(default=..., description="Event identifier")
    event_type: str = Field(default=..., description="Event type")
    timestamp: str = Field(default=..., description="Event timestamp")
    envelope_id: str = Field(default=..., description="Envelope ID")
    # Additional fields from the actual event can be included as needed

    def is_recent(self, minutes_threshold: int = 60) -> bool:
        """Check if event is recent (within threshold minutes)."""
        # This is a simplified implementation - in practice you'd parse the timestamp
        return True  # Placeholder implementation

    def get_event_severity(self) -> str:
        """Get event severity based on event type."""
        event_type_lower = self.event_type.lower()
        if any(word in event_type_lower for word in ["error", "fail", "breach"]):
            return "high"
        elif any(word in event_type_lower for word in ["warning", "alert"]):
            return "medium"
        else:
            return "low"

    def get_event_summary(self) -> dict[str, Any]:
        """Get security event summary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "envelope_id": self.envelope_id,
            "severity": self.get_event_severity(),
            "is_recent": self.is_recent(),
        }
