"""
Event Type Subcontract Model.



Dedicated subcontract model for event-driven architecture functionality providing:
- Primary event definitions with categories and routing
- Event publishing and subscription configuration
- Event transformation and filtering rules
- Event routing strategies and target groups
- Event persistence and replay configuration

This model is composed into node contracts that participate in event-driven workflows,
providing clean separation between node logic and event handling behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import individual event model components
from .model_event_definition import ModelEventDefinition
from .model_event_persistence import ModelEventPersistence
from .model_event_routing import ModelEventRouting
from .model_event_transformation import ModelEventTransformation


class ModelEventTypeSubcontract(BaseModel):
    """
    Event Type subcontract model for event-driven architecture.

    Comprehensive event handling subcontract providing event definitions,
    transformations, routing, and persistence configuration.
    Designed for composition into node contracts participating in event workflows.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (auto-generated as 1.0.0 if not provided)",
    )

    # Primary event configuration
    primary_events: list[str] = Field(
        default=...,
        description="Primary events that this node produces/handles",
    )

    event_categories: list[str] = Field(
        default=...,
        description="Event categories for classification and routing",
    )

    # Event behavior configuration
    publish_events: bool = Field(
        default=True,
        description="Whether this node publishes events",
    )

    subscribe_events: bool = Field(
        default=False,
        description="Whether this node subscribes to events",
    )

    event_routing: str = Field(
        default=...,
        description="Event routing strategy or target routing group",
    )

    # Advanced event definitions (optional)
    event_definitions: list[ModelEventDefinition] = Field(
        default_factory=list,
        description="Detailed event type definitions",
    )

    # Event processing configuration
    transformations: list[ModelEventTransformation] = Field(
        default_factory=list,
        description="Event transformation specifications",
    )

    routing_config: ModelEventRouting | None = Field(
        default=None,
        description="Advanced routing configuration",
    )

    persistence_config: ModelEventPersistence | None = Field(
        default=None,
        description="Event persistence configuration",
    )

    # Event filtering and processing
    event_filters: list[str] = Field(
        default_factory=list,
        description="Filters for incoming events",
    )

    batch_processing: bool = Field(
        default=False,
        description="Enable batch processing for events",
    )

    batch_size: int = Field(
        default=100,
        description="Batch size for event processing",
    )

    batch_timeout_ms: int = Field(
        default=5000,
        description="Timeout for batch processing",
        ge=100,
    )

    # Event ordering and delivery guarantees
    ordering_required: bool = Field(
        default=False,
        description="Whether event ordering must be preserved",
    )

    delivery_guarantee: str = Field(
        default="at_least_once",
        description="Delivery guarantee level",
    )

    deduplication_enabled: bool = Field(
        default=False,
        description="Enable event deduplication",
    )

    deduplication_window_ms: int = Field(
        default=60000,
        description="Deduplication time window",
    )

    # Performance and monitoring
    async_processing: bool = Field(
        default=True,
        description="Enable asynchronous event processing",
    )

    max_concurrent_events: int = Field(
        default=100,
        description="Maximum concurrent events to process",
        ge=1,
    )

    event_metrics_enabled: bool = Field(
        default=True,
        description="Enable event processing metrics",
    )

    event_tracing_enabled: bool = Field(
        default=False,
        description="Enable distributed tracing for events",
    )

    @model_validator(mode="after")
    def validate_event_lists(self) -> "ModelEventTypeSubcontract":
        """Validate that primary events and event categories are not empty."""
        if not self.primary_events:
            msg = "primary_events must contain at least one event type"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        if not self.event_categories:
            msg = "event_categories must contain at least one category"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        return self

    @model_validator(mode="after")
    def validate_batch_configuration(self) -> "ModelEventTypeSubcontract":
        """Validate batch size when batch processing is enabled."""
        if self.batch_processing:
            if self.batch_size < 1:
                msg = "batch_size must be positive when batch processing is enabled"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_deduplication_configuration(self) -> "ModelEventTypeSubcontract":
        """Validate deduplication window when deduplication is enabled."""
        if self.deduplication_enabled:
            if self.deduplication_window_ms < 1000:
                msg = "deduplication_window_ms must be at least 1000ms when enabled"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
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
