"""
Component Health Detail Model.

Strongly-typed model for component health details.
Replaces dict[str, str] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_health_detail_type import EnumHealthDetailType
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelComponentHealthDetail(BaseModel):
    """
    Strongly-typed component health detail.

    Provides structured health information with proper validation
    and type safety.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    detail_key: str = Field(
        ...,
        description="Key identifying the health detail",
        min_length=1,
    )

    detail_value: str = Field(
        ...,
        description="Value of the health detail",
    )

    detail_type: EnumHealthDetailType = Field(
        default=EnumHealthDetailType.INFO,
        description="Type of detail (info, metric, warning, error, diagnostic)",
    )

    is_critical: bool = Field(
        default=False,
        description="Whether this detail indicates a critical issue",
    )

    timestamp_ms: int | None = Field(
        default=None,
        description="Timestamp when this detail was captured (milliseconds since epoch)",
        ge=0,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
