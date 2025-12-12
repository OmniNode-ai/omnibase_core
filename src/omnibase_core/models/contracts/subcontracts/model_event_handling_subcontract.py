"""
Event Handling Subcontract Model.



Dedicated subcontract model for event handling functionality providing:
- Event subscription and handler registration
- Event filtering by node ID and node name patterns
- Introspection and discovery request handling
- Async and sync event bus support
- Event handler lifecycle management
- Dead letter queue configuration for failed events

This model is composed into node contracts that require event handling functionality,
providing clean separation between node logic and event-driven behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventHandlingSubcontract(BaseModel):
    """
    Event Handling subcontract model for event-driven node behavior.

    Comprehensive event handling subcontract providing event subscription,
    filtering, introspection/discovery request handling, and lifecycle management.
    Designed for composition into node contracts requiring event-driven capabilities.

    Based on MixinEventHandler implementation, this subcontract configures:
    - Automatic subscription to introspection and discovery events
    - Pattern-based event filtering (node ID, node name)
    - Async and sync event bus handler registration
    - Event handler cleanup and lifecycle management
    - Failed event handling with retry and dead letter queue support

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core event handling configuration
    enabled: bool = Field(
        default=True,
        description="Enable event handling functionality",
    )

    # Event subscription configuration
    subscribed_events: list[str] = Field(
        default_factory=lambda: [
            "NODE_INTROSPECTION_REQUEST",
            "NODE_DISCOVERY_REQUEST",
        ],
        description="Event types to subscribe to (supports wildcard patterns)",
    )

    auto_subscribe_on_init: bool = Field(
        default=True,
        description="Automatically subscribe to events during node initialization",
    )

    # Event filtering configuration
    event_filters: dict[str, str] = Field(
        default_factory=dict,
        description="Event filtering rules (e.g., {'node_id': 'pattern*', 'node_name': 'compute*'})",
    )

    enable_node_id_filtering: bool = Field(
        default=True,
        description="Enable filtering by node ID using fnmatch patterns",
    )

    enable_node_name_filtering: bool = Field(
        default=True,
        description="Enable filtering by node name using fnmatch patterns",
    )

    respond_to_all_when_no_filter: bool = Field(
        default=True,
        description="Respond to all events when no specific filters are present",
    )

    # Introspection configuration
    handle_introspection_requests: bool = Field(
        default=True,
        description="Handle NODE_INTROSPECTION_REQUEST events",
    )

    handle_discovery_requests: bool = Field(
        default=True,
        description="Handle NODE_DISCOVERY_REQUEST events",
    )

    filter_introspection_data: bool = Field(
        default=True,
        description="Filter introspection data based on requested_types in event metadata",
    )

    # Event handler lifecycle
    async_event_bus_support: bool = Field(
        default=True,
        description="Support async event bus subscription using subscribe_async",
    )

    sync_event_bus_fallback: bool = Field(
        default=True,
        description="Fall back to sync subscribe when async is unavailable",
    )

    cleanup_on_shutdown: bool = Field(
        default=True,
        description="Automatically cleanup event handlers on node shutdown",
    )

    # Retry and resilience configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries for failed event handling (0 = no retries)",
    )

    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Delay between retries in seconds",
    )

    retry_exponential_backoff: bool = Field(
        default=True,
        description="Use exponential backoff for retry delays",
    )

    # Dead letter queue configuration
    dead_letter_channel: str | None = Field(
        default=None,
        description="Dead letter queue channel for failed events (None = no DLQ)",
    )

    dead_letter_max_events: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum number of events in dead letter queue",
    )

    dead_letter_overflow_strategy: str = Field(
        default="drop_oldest",
        description="Strategy when DLQ is full: drop_oldest, drop_newest, block",
    )

    # Error handling configuration
    fail_fast_on_handler_errors: bool = Field(
        default=False,
        description="Fail immediately on event handler errors (vs. log and continue)",
    )

    log_handler_errors: bool = Field(
        default=True,
        description="Log errors from event handlers",
    )

    emit_error_events: bool = Field(
        default=True,
        description="Emit ERROR events when event handling fails",
    )

    # Performance and monitoring
    track_handler_performance: bool = Field(
        default=True,
        description="Track event handler execution time and performance metrics",
    )

    handler_timeout_seconds: float | None = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for event handler execution (None = no timeout)",
    )

    @field_validator("subscribed_events")
    @classmethod
    def validate_subscribed_events(cls, v: list[str]) -> list[str]:
        """Validate that subscribed_events list is not empty when enabled."""
        if not v:
            msg = "subscribed_events cannot be empty when event handling is enabled"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "field_validation",
                        ),
                        "field": ModelSchemaValue.from_value("subscribed_events"),
                    },
                ),
            )
        return v

    @field_validator("dead_letter_channel")
    @classmethod
    def validate_dead_letter_channel(cls, v: str | None) -> str | None:
        """Validate dead letter channel format if provided."""
        if v is not None:
            # Channel name must be valid identifier (alphanumeric + underscores + dots)
            if not v.replace("_", "").replace(".", "").replace("-", "").isalnum():
                msg = f"dead_letter_channel must be alphanumeric with underscores, dots, or hyphens, got '{v}'"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "field_validation",
                            ),
                            "field": ModelSchemaValue.from_value("dead_letter_channel"),
                            "provided_value": ModelSchemaValue.from_value(v),
                        },
                    ),
                )
        return v

    @model_validator(mode="after")
    def validate_event_handling_configuration(self) -> "ModelEventHandlingSubcontract":
        """Validate event handling configuration fields after model construction."""
        # Validate dead_letter_overflow_strategy
        allowed_overflow_strategies = ["drop_oldest", "drop_newest", "block"]
        if self.dead_letter_overflow_strategy not in allowed_overflow_strategies:
            msg = f"dead_letter_overflow_strategy must be one of {allowed_overflow_strategies}, got '{self.dead_letter_overflow_strategy}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_values": ModelSchemaValue.from_value(
                            allowed_overflow_strategies
                        ),
                        "provided_value": ModelSchemaValue.from_value(
                            self.dead_letter_overflow_strategy
                        ),
                    },
                ),
            )

        # Validate retry configuration consistency
        if self.max_retries > 0 and self.retry_delay_seconds <= 0:
            msg = "retry_delay_seconds must be > 0 when max_retries > 0"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "max_retries": ModelSchemaValue.from_value(self.max_retries),
                        "retry_delay_seconds": ModelSchemaValue.from_value(
                            self.retry_delay_seconds
                        ),
                    },
                ),
            )

        # Validate handler timeout is reasonable
        if (
            self.handler_timeout_seconds is not None
            and self.handler_timeout_seconds < 1.0
        ):
            msg = "handler_timeout_seconds must be >= 1.0 second when specified"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("handler_timeout_seconds"),
                        "provided_value": ModelSchemaValue.from_value(
                            self.handler_timeout_seconds
                        ),
                    },
                ),
            )

        # Validate DLQ max_events is reasonable
        if self.dead_letter_max_events > 5000:
            msg = (
                f"dead_letter_max_events ({self.dead_letter_max_events}) exceeding 5000 "
                "may cause memory issues; consider external DLQ storage"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "recommended_max_value": ModelSchemaValue.from_value(5000),
                        "provided_value": ModelSchemaValue.from_value(
                            self.dead_letter_max_events
                        ),
                    },
                ),
            )

        # Validate async/sync configuration consistency
        if not self.async_event_bus_support and not self.sync_event_bus_fallback:
            msg = "At least one of async_event_bus_support or sync_event_bus_fallback must be enabled"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "async_event_bus_support": ModelSchemaValue.from_value(
                            self.async_event_bus_support
                        ),
                        "sync_event_bus_fallback": ModelSchemaValue.from_value(
                            self.sync_event_bus_fallback
                        ),
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
