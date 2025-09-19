"""
Breakdown of nodes by various categories.

Provides strongly-typed categorization of nodes by type, status, and complexity
using enum-based keys for type safety and consistency.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import (
    EnumComplexityLevel,
    EnumNodeStatus,
    EnumNodeType,
)


class ModelCollectionNodeBreakdown(BaseModel):
    """Breakdown of nodes by various categories."""

    model_config = ConfigDict(extra="forbid")

    by_type: dict[EnumNodeType, int] = Field(
        default_factory=dict,
        description="Node count by type",
    )
    by_status: dict[EnumNodeStatus, int] = Field(
        default_factory=dict,
        description="Node count by status",
    )
    by_complexity: dict[EnumComplexityLevel, int] = Field(
        default_factory=dict,
        description="Node count by complexity",
    )
