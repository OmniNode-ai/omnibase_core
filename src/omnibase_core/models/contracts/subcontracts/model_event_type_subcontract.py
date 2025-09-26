#!/usr/bin/env python3
"""
Event Type Subcontract Model - ONEX Standards Compliant.

Dedicated subcontract model for event-driven architecture functionality providing:
- Primary event definitions with categories and routing
- Event publishing and subscription configuration
- Event transformation and filtering rules
- Event routing strategies and target groups
- Event persistence and replay configuration

This model is composed into node contracts that participate in event-driven workflows,
providing clean separation between node logic and event handling behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

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

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Primary event configuration
    primary_events: list[str] = Field(
        ...,
        description="Primary events that this node produces/handles",
        min_length=1,
    )

    event_categories: list[str] = Field(
        ...,
        description="Event categories for classification and routing",
        min_length=1,
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
        ...,
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
        ge=1,
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
        ge=1000,
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

    @field_validator("primary_events")
    @classmethod
    def validate_primary_events_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that primary events list is not empty."""
        if not v:
            msg = "primary_events must contain at least one event type"
            raise ValueError(msg)
        return v

    @field_validator("event_categories")
    @classmethod
    def validate_event_categories_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that event categories list is not empty."""
        if not v:
            msg = "event_categories must contain at least one category"
            raise ValueError(msg)
        return v

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int, info: ValidationInfo) -> int:
        """Validate batch size when batch processing is enabled."""
        if info.data and info.data.get("batch_processing", False):
            if v < 1:
                msg = "batch_size must be positive when batch processing is enabled"
                raise ValueError(
                    msg,
                )
        return v

    @field_validator("deduplication_window_ms")
    @classmethod
    def validate_deduplication_window(cls, v: int, info: ValidationInfo) -> int:
        """Validate deduplication window when deduplication is enabled."""
        if info.data and info.data.get("deduplication_enabled", False):
            if v < 1000:
                msg = "deduplication_window_ms must be at least 1000ms when enabled"
                raise ValueError(
                    msg,
                )
        return v

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
