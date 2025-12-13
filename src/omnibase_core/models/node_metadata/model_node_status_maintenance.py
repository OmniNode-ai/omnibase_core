"""
Node Status Maintenance Model.

Maintenance node status with estimated completion for discriminated union pattern.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_maintenance_summary import (
    TypedDictMaintenanceSummary,
)


class ModelNodeStatusMaintenance(BaseModel):
    """Maintenance node status with estimated completion."""

    status_type: str = Field(
        default="maintenance",
        description="Status discriminator",
    )
    estimated_completion: str = Field(
        description="ISO timestamp of estimated completion",
    )
    maintenance_reason: str = Field(description="Reason for maintenance")

    def is_critical_maintenance(self) -> bool:
        """Check if this is critical maintenance."""
        reason_lower = self.maintenance_reason.lower()
        return any(
            keyword in reason_lower for keyword in ["critical", "urgent", "emergency"]
        )

    def is_scheduled_maintenance(self) -> bool:
        """Check if this is scheduled maintenance."""
        reason_lower = self.maintenance_reason.lower()
        return any(
            keyword in reason_lower for keyword in ["scheduled", "planned", "routine"]
        )

    def get_maintenance_priority(self) -> str:
        """Get maintenance priority level."""
        if self.is_critical_maintenance():
            return "critical"
        elif self.is_scheduled_maintenance():
            return "scheduled"
        else:
            return "normal"

    def get_maintenance_summary(self) -> TypedDictMaintenanceSummary:
        """Get maintenance status summary."""
        return {
            "status_type": self.status_type,
            "estimated_completion": self.estimated_completion,
            "maintenance_reason": self.maintenance_reason,
            "is_critical": self.is_critical_maintenance(),
            "is_scheduled": self.is_scheduled_maintenance(),
            "priority": self.get_maintenance_priority(),
        }
