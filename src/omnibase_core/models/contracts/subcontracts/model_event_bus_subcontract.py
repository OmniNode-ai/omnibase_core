"""
Event Bus Subcontract Model.



Dedicated subcontract model for event bus functionality providing:
- Event bus configuration and connection management
- Event emission and routing policies
- Queue management and batch processing
- Correlation tracking and monitoring
- Event logging and performance metrics

This model is composed into node contracts that require event bus functionality,
providing clean separation between node logic and event communication behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants import KAFKA_REQUEST_TIMEOUT_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.subcontracts.model_topic_meta import ModelTopicMeta
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventBusSubcontract(BaseModel):
    """
    Event Bus subcontract model for event communication functionality.

    Comprehensive event bus subcontract providing event emission, routing,
    queue management, and monitoring capabilities. Designed for composition
    into node contracts requiring event-driven communication.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core event bus configuration
    event_bus_enabled: bool = Field(
        default=True,
        description="Enable event bus functionality",
    )

    event_bus_type: str = Field(
        default="hybrid",
        description="Event bus type: memory, hybrid, or distributed",
    )

    # Event logging and monitoring
    enable_event_logging: bool = Field(
        default=True,
        description="Enable structured logging for all events",
    )

    log_event_payloads: bool = Field(
        default=False,
        description="Include event payloads in logs (may contain sensitive data)",
    )

    # Correlation tracking
    correlation_tracking: bool = Field(
        default=True,
        description="Enable correlation ID tracking across events",
    )

    correlation_id_propagation: bool = Field(
        default=True,
        description="Propagate correlation IDs to downstream events",
    )

    # Queue management
    max_queue_size: int = Field(
        default=10000,
        description="Maximum number of events in queue",
        ge=100,
        le=100000,
    )

    queue_overflow_strategy: str = Field(
        default="block",
        description="Strategy when queue is full: block, drop_oldest, drop_newest",
    )

    # Batch processing
    batch_size: int = Field(
        default=100,
        description="Number of events to process in a batch",
        ge=1,
        le=1000,
    )

    batch_timeout_ms: int = Field(
        default=KAFKA_REQUEST_TIMEOUT_MS,
        description="Maximum time to wait for batch completion",
        ge=100,
        le=60000,
    )

    # Event emission configuration
    enable_lifecycle_events: bool = Field(
        default=True,
        description="Emit NODE_START, NODE_SUCCESS, NODE_FAILURE events",
    )

    enable_introspection_events: bool = Field(
        default=True,
        description="Emit introspection events for service discovery",
    )

    # Event retry and resilience
    enable_event_retry: bool = Field(
        default=True,
        description="Enable retry logic for failed event publishing",
    )

    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=1,
        le=10,
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retry attempts in milliseconds",
        ge=100,
        le=30000,
    )

    # Event validation
    enable_event_validation: bool = Field(
        default=True,
        description="Validate events before publishing",
    )

    fail_fast_on_validation_errors: bool = Field(
        default=True,
        description="Fail immediately on event validation errors",
    )

    # Performance configuration
    enable_event_caching: bool = Field(
        default=True,
        description="Enable caching for frequently created events",
    )

    cache_max_size: int = Field(
        default=100,
        description="Maximum number of events to cache",
        ge=10,
        le=1000,
    )

    # Monitoring and metrics
    metrics_enabled: bool = Field(
        default=True,
        description="Enable event bus metrics collection",
    )

    detailed_metrics: bool = Field(
        default=False,
        description="Enable detailed event bus metrics",
    )

    performance_monitoring: bool = Field(
        default=True,
        description="Enable event bus performance monitoring",
    )

    # Event patterns and routing
    use_contract_event_patterns: bool = Field(
        default=True,
        description="Extract event patterns from contract YAML first",
    )

    fallback_to_node_name_patterns: bool = Field(
        default=True,
        description="Fall back to node name-based patterns if no contract patterns",
    )

    default_event_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.discovery.*",
            "core.discovery.introspection_request",
        ],
        description="Default event patterns if no other patterns can be determined",
    )

    # Topic-based routing configuration (OMN-1537)
    publish_topics: list[str] = Field(
        default_factory=list,
        description="Topic suffixes this node publishes to. Format: onex.{kind}.{producer}.{event-name}.v{n}",
    )

    subscribe_topics: list[str] = Field(
        default_factory=list,
        description="Topic suffixes this node subscribes to. Format: onex.{kind}.{producer}.{event-name}.v{n}",
    )

    # Extension path for future schema_ref support
    publish_topic_metadata: dict[str, ModelTopicMeta] | None = Field(
        default=None,
        description="Optional metadata per publish topic suffix (keyed by suffix string)",
    )

    subscribe_topic_metadata: dict[str, ModelTopicMeta] | None = Field(
        default=None,
        description="Optional metadata per subscribe topic suffix (keyed by suffix string)",
    )

    @field_validator("publish_topics", "subscribe_topics", mode="after")
    @classmethod
    def validate_topic_suffixes(cls, topics: list[str]) -> list[str]:
        """Validate each topic suffix against ONEX naming convention."""
        # Import here to avoid circular import at module load time
        from omnibase_core.validation import validate_topic_suffix

        for topic in topics:
            result = validate_topic_suffix(topic)
            if not result.is_valid:
                raise ValueError(f"Invalid topic suffix '{topic}': {result.error}")
        return topics

    @model_validator(mode="after")
    def validate_event_bus_configuration(self) -> "ModelEventBusSubcontract":
        """Validate event bus configuration fields after model construction."""
        # Validate event_bus_type
        allowed_bus_types = ["memory", "hybrid", "distributed"]
        if self.event_bus_type not in allowed_bus_types:
            msg = f"event_bus_type must be one of {allowed_bus_types}, got '{self.event_bus_type}'"
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
                            allowed_bus_types
                        ),
                        "provided_value": ModelSchemaValue.from_value(
                            self.event_bus_type
                        ),
                    },
                ),
            )

        # Validate queue_overflow_strategy
        allowed_overflow_strategies = ["block", "drop_oldest", "drop_newest"]
        if self.queue_overflow_strategy not in allowed_overflow_strategies:
            msg = f"queue_overflow_strategy must be one of {allowed_overflow_strategies}, got '{self.queue_overflow_strategy}'"
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
                            self.queue_overflow_strategy
                        ),
                    },
                ),
            )

        # Validate max_queue_size
        if self.max_queue_size > 50000:
            msg = (
                "max_queue_size exceeding 50000 may cause memory issues; "
                "consider using distributed event bus"
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
                        "max_safe_value": ModelSchemaValue.from_value(50000),
                        "provided_value": ModelSchemaValue.from_value(
                            self.max_queue_size
                        ),
                    },
                ),
            )

        # Validate batch_size
        if self.batch_size > 500:
            msg = (
                "batch_size exceeding 500 may cause performance degradation; "
                "consider smaller batch sizes with more frequent processing"
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
                        "recommended_max_value": ModelSchemaValue.from_value(500),
                        "provided_value": ModelSchemaValue.from_value(self.batch_size),
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
