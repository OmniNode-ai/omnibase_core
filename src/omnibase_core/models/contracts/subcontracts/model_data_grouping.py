from pydantic import Field

"""
Data Grouping Model.

Individual model for data grouping configuration.
Part of the Aggregation Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDataGrouping(BaseModel):
    """
    Data grouping configuration.

    Defines grouping strategies, keys, and
    aggregation scope for data processing.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
