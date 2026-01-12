"""
Event Coordination Configuration Model.

Defines event-to-workflow mappings, trigger conditions,
and coordination patterns for event-driven execution.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventCoordinationConfig(BaseModel):
    """
    Event-driven workflow trigger mappings.

    Defines event-to-workflow mappings, trigger conditions,
    and coordination patterns for event-driven execution.
    """

    trigger_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Event pattern to workflow action mappings",
    )

    coordination_strategy: str = Field(
        default="immediate",
        description="Event coordination strategy (immediate, buffered, scheduled)",
    )

    buffer_size: int = Field(
        default=100,
        description="Event buffer size for buffered coordination",
        ge=1,
    )

    correlation_enabled: bool = Field(
        default=True,
        description="Enable event correlation for related events",
    )

    correlation_timeout_ms: int = Field(
        default=10000,
        description="Correlation timeout in milliseconds",
        ge=1,
    )

    ordering_guaranteed: bool = Field(
        default=False,
        description="Guarantee event processing order",
    )

    duplicate_detection_enabled: bool = Field(
        default=True,
        description="Enable duplicate event detection",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
