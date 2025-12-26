"""
ModelAuditData: Audit data representation.

This model provides structured audit data without using Any types.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.context import ModelAuditMetadata


class ModelAuditData(BaseModel):
    """Audit data representation."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Audit timestamp",
    )
    user_id: UUID | None = Field(default=None, description="User identifier")
    action: str = Field(default=..., description="Action performed")
    resource: str = Field(default=..., description="Resource accessed")
    result: str = Field(default=..., description="Action result")
    security_level: str = Field(default=..., description="Security classification")
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance tags",
    )
    audit_metadata: ModelAuditMetadata | None = Field(
        default=None,
        description="Structured audit metadata with typed fields",
    )
