"""
ModelHealthIssue - Individual health issue tracking model

Health issue model for tracking specific problems, their severity,
category, occurrence patterns, and recovery recommendations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelHealthIssue(BaseModel):
    """
    Individual health issue model for tracking specific problems

    This model tracks individual health issues including severity,
    categorization, occurrence patterns, and recovery recommendations.
    """

    issue_id: UUID = Field(default=..., description="Unique issue identifier")

    severity: str = Field(
        default=...,
        description="Issue severity level",
        pattern="^(low|medium|high|critical)$",
    )

    category: str = Field(
        default=...,
        description="Issue category",
        pattern="^(performance|connectivity|resource|configuration|security|other)$",
    )

    message: str = Field(default=..., description="Human-readable issue description")

    first_detected: datetime = Field(
        default=..., description="When issue was first detected"
    )

    last_seen: datetime = Field(default=..., description="When issue was last observed")

    count: int = Field(
        default=1,
        description="Number of times this issue occurred",
        ge=1,
    )

    auto_recoverable: bool = Field(
        default=False,
        description="Whether issue can be automatically recovered",
    )

    recovery_action: str | None = Field(
        default=None,
        description="Recommended recovery action",
    )

    def is_critical(self) -> bool:
        """Check if this is a critical issue"""
        return self.severity == "critical"

    def is_recurring(self, threshold: int = 3) -> bool:
        """Check if this is a recurring issue"""
        return self.count >= threshold

    def get_duration_seconds(self) -> int:
        """Get duration this issue has been active"""
        return int((self.last_seen - self.first_detected).total_seconds())

    @classmethod
    def create_performance_issue(
        cls,
        message: str,
        severity: str = "medium",
    ) -> "ModelHealthIssue":
        """Create a performance-related health issue"""
        return cls(
            issue_id=uuid4(),
            severity=severity,
            category="performance",
            message=message,
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

    @classmethod
    def create_connectivity_issue(
        cls,
        message: str,
        severity: str = "high",
    ) -> "ModelHealthIssue":
        """Create a connectivity-related health issue"""
        return cls(
            issue_id=uuid4(),
            severity=severity,
            category="connectivity",
            message=message,
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

    @classmethod
    def create_resource_issue(
        cls,
        message: str,
        severity: str = "high",
    ) -> "ModelHealthIssue":
        """Create a resource-related health issue"""
        return cls(
            issue_id=uuid4(),
            severity=severity,
            category="resource",
            message=message,
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
