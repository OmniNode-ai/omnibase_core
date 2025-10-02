"""
Event Subscription Model - ONEX Standards Compliant.

Defines event consumption patterns, filtering rules,
and handler configuration for event subscriptions.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.constraints import PrimitiveValueType


class ModelEventSubscription(BaseModel):
    """
    Event subscription configuration.

    Defines event consumption patterns, filtering rules,
    and handler configuration for event subscriptions.
    """

    event_pattern: str = Field(
        ...,
        description="Event name pattern or specific event name",
        min_length=1,
    )

    filter_conditions: dict[str, PrimitiveValueType] = Field(
        default_factory=dict,
        description="Event filtering conditions",
    )

    handler_function: str = Field(
        ...,
        description="Event handler function identifier",
        min_length=1,
    )

    batch_processing: bool = Field(
        default=False,
        description="Enable batch processing for events",
    )

    batch_size: int = Field(
        default=1,
        description="Batch size for event processing",
        ge=1,
    )

    timeout_ms: int = Field(
        default=5000,
        description="Event processing timeout in milliseconds",
        ge=1,
    )

    retry_enabled: bool = Field(
        default=True,
        description="Enable retry for failed event processing",
    )

    dead_letter_enabled: bool = Field(
        default=True,
        description="Enable dead letter queue for failed events",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
