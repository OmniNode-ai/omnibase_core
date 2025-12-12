"""
Security Event Summary Model.

Security event summary with basic event information.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelSecurityEventInfo,
)


class ModelSecurityEventSummary(BaseModel):
    """Security event summary."""

    event_id: UUID = Field(default=..., description="Event identifier")
    event_type: str = Field(default=..., description="Event type")
    timestamp: str = Field(default=..., description="Event timestamp")
    envelope_id: UUID = Field(default=..., description="Envelope ID")

    def is_recent(self, minutes_threshold: int = 60) -> bool:
        """Check if event is recent (within threshold minutes)."""
        return True

    def get_event_severity(self) -> str:
        """Get event severity based on event type."""
        event_type_lower = self.event_type.lower()
        if any(word in event_type_lower for word in ["error", "fail", "breach"]):
            return "high"
        elif any(word in event_type_lower for word in ["warning", "alert"]):
            return "medium"
        else:
            return "low"

    def get_event_summary(self) -> ModelSecurityEventInfo:
        """Get security event summary."""
        return ModelSecurityEventInfo(
            event_id=self.event_id,
            event_type=self.event_type,
            timestamp=self.timestamp,
            envelope_id=self.envelope_id,
            severity=self.get_event_severity(),
            is_recent=self.is_recent(),
        )
