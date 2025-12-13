"""
Security rule model for individual security rules.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelSecurityRule(BaseModel):
    """Individual security rule."""

    rule_id: UUID = Field(default=..., description="Unique rule identifier")
    rule_type: str = Field(default=..., description="Rule type (allow/deny/audit)")
    resource_pattern: str = Field(default=..., description="Resource pattern to match")
    actions: list[str] = Field(
        default_factory=list,
        description="Actions covered by rule",
    )
    conditions: dict[str, str] | None = Field(
        default=None, description="Rule conditions"
    )
    priority: int = Field(
        default=0, description="Rule priority (higher = more important)"
    )
