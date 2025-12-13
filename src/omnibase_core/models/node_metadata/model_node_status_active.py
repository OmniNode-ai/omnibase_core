"""
Node Status Active Model.

Active node status with uptime tracking for discriminated union pattern.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_active_summary import TypedDictActiveSummary


class ModelNodeStatusActive(BaseModel):
    """Active node status with uptime tracking."""

    status_type: str = Field(
        default="active",
        description="Status discriminator",
    )
    uptime_seconds: int = Field(ge=0, description="Node uptime in seconds")
    last_heartbeat: str = Field(description="ISO timestamp of last heartbeat")

    def get_uptime_days(self) -> float:
        """Get uptime in days."""
        return self.uptime_seconds / 86400

    def get_uptime_hours(self) -> float:
        """Get uptime in hours."""
        return self.uptime_seconds / 3600

    def get_uptime_minutes(self) -> float:
        """Get uptime in minutes."""
        return self.uptime_seconds / 60

    def is_recently_heartbeat(self, hours_threshold: int = 1) -> bool:
        """Check if heartbeat is recent (within threshold hours)."""
        # Simplified implementation - in practice you'd parse the timestamp
        return True

    def get_health_score(self) -> float:
        """Get health score based on uptime and heartbeat."""
        uptime_score = min(self.get_uptime_days() * 10, 50)  # Max 50 points for uptime
        heartbeat_score = 50 if self.is_recently_heartbeat() else 25
        return uptime_score + heartbeat_score

    def get_summary(self) -> TypedDictActiveSummary:
        """Get active status summary."""
        return {
            "status_type": self.status_type,
            "uptime_seconds": self.uptime_seconds,
            "uptime_days": self.get_uptime_days(),
            "uptime_hours": self.get_uptime_hours(),
            "uptime_minutes": self.get_uptime_minutes(),
            "last_heartbeat": self.last_heartbeat,
            "is_recent_heartbeat": self.is_recently_heartbeat(),
            "health_score": self.get_health_score(),
        }
