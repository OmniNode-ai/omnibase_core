"""
Windowing Strategy Model.

Individual model for windowing strategy configuration.
Part of the Aggregation Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWindowingStrategy(BaseModel):
    """
    Windowing strategy for time-based aggregation.

    Defines windowing policies, sizes, and
    time-based aggregation parameters.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    windowing_enabled: bool = Field(
        default=False,
        description="Enable windowing for aggregation",
    )

    window_type: str = Field(
        default="tumbling",
        description="Type of windowing (tumbling, sliding, session)",
    )

    window_size_ms: int = Field(
        default=60000,
        description="Window size in milliseconds",
        ge=1000,
    )

    window_slide_ms: int | None = Field(
        default=None,
        description="Window slide interval for sliding windows",
        ge=1000,
    )

    session_timeout_ms: int | None = Field(
        default=None,
        description="Session timeout for session windows",
        ge=1000,
    )

    window_trigger: str = Field(
        default="time_based",
        description="Trigger for window completion",
    )

    late_arrival_handling: str = Field(
        default="ignore",
        description="Strategy for late-arriving data",
    )

    allowed_lateness_ms: int = Field(
        default=10000,
        description="Allowed lateness for events",
        ge=0,
    )

    watermark_strategy: str = Field(
        default="event_time",
        description="Watermark strategy for event ordering",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
