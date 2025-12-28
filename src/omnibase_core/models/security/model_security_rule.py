"""Security rule model for individual security rules.

Defines individual access control rules that specify allowed or denied
actions on resources based on conditions and priority.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelSecurityRule(BaseModel):
    """Individual security rule for access control.

    Defines a single rule that matches resources and actions, with optional
    conditions for fine-grained access control. Rules are evaluated in
    priority order (higher priority = more important).

    Note:
        This model uses frozen=True for immutability and from_attributes=True
        to support pytest-xdist parallel execution where class identity may
        differ between workers.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

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
