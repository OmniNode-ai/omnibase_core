from typing import Any

from pydantic import Field

"""
Data Grouping Model - ONEX Standards Compliant.

Individual model for data grouping configuration.
Part of the Aggregation Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel


class ModelDataGrouping(BaseModel):
    """
    Data grouping configuration.

    Defines grouping strategies, keys, and
    aggregation scope for data processing.
    """

    grouping_enabled: bool = Field(default=True, description="Enable data grouping")

    grouping_fields: list[str] = Field(
        default_factory=list,
        description="Fields to group by for aggregation",
    )

    grouping_strategy: str = Field(
        default="hash_based",
        description="Strategy for data grouping",
    )

    case_sensitive_grouping: bool = Field(
        default=True,
        description="Case sensitivity for grouping keys",
    )

    null_group_handling: str = Field(
        default="separate",
        description="How to handle null grouping values",
    )

    max_groups: int | None = Field(
        default=None,
        description="Maximum number of groups to maintain",
        ge=1,
    )

    group_expiration_ms: int | None = Field(
        default=None,
        description="Expiration time for inactive groups",
        ge=1000,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
