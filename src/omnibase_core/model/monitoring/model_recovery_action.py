"""
Model for recovery action.

Automated recovery action taken.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.monitoring.enum_recovery_action import EnumRecoveryAction


class ModelRecoveryAction(BaseModel):
    """Automated recovery action taken."""

    action_id: str = Field(..., description="Unique action identifier")
    action_type: EnumRecoveryAction = Field(..., description="Type of recovery action")

    triggered_by_alert: str = Field(..., description="Alert ID that triggered action")
    target_component: str = Field(..., description="Component being acted upon")
    target_agent: str | None = Field(
        None,
        description="Specific agent if applicable",
    )

    initiated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When action was initiated",
    )
    completed_at: datetime | None = Field(None, description="When action completed")

    success: bool | None = Field(None, description="Whether action was successful")
    error_message: str | None = Field(
        None,
        description="Error message if action failed",
    )

    parameters: str | None = Field(
        None,
        description="Action parameters as JSON string",
    )

    impact_description: str = Field(..., description="Description of expected impact")

    def mark_completed(
        self,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Mark action as completed."""
        self.completed_at = datetime.utcnow()
        self.success = success
        self.error_message = error_message

    def get_duration(self) -> float | None:
        """Get action duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.initiated_at).total_seconds()
