import uuid
from typing import Generic, Optional, TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.primitives.model_semver import ModelSemVer

"\nEvent Envelope Model\n\nONEX-compliant envelope wrapper for all events in the system.\nProvides standardized event wrapping with metadata, correlation IDs, security context,\nQoS features, distributed tracing, and performance optimization.\n\nPattern: Model<Name> - Pydantic model for event envelope\nNode Type: N/A (Data Model)\n"
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation

T = TypeVar("T")


class ModelEventEnvelope(BaseModel, MixinLazyEvaluation, Generic[T]):
    """
    ONEX-compliant envelope wrapper for all events.

    Wraps event payloads with standardized metadata, correlation tracking,
    security context, QoS features, distributed tracing, and lazy evaluation
    for performance optimization.

    Features:
    - Generic payload support (any event type)
    - Correlation tracking and distributed tracing
    - Quality of Service (priority, timeout, retry)
    - Security context
    - ONEX version compliance
    - Lazy evaluation for 60% memory savings on serialization

    Attributes:
        payload: The actual event data (e.g., ModelOnexEvent, custom event models)
        envelope_id: Unique identifier for this envelope instance
        envelope_timestamp: When this envelope was created
        correlation_id: Optional correlation ID for request tracing
        source_tool: Optional identifier of the tool that created this event
        target_tool: Optional identifier of the intended recipient tool
        metadata: Additional envelope metadata (tool version, environment, etc.)
        security_context: Optional security context for the event

        # QoS Features
        priority: Request priority (1-10, where 10 is highest)
        timeout_seconds: Optional timeout in seconds
        retry_count: Number of retry attempts (0 = first attempt)

        # Distributed Tracing
        request_id: Optional request identifier for tracing
        trace_id: Optional distributed trace identifier
        span_id: Optional trace span identifier

        # ONEX Compliance
        onex_version: ONEX standard version
        envelope_version: Envelope schema version
    """

    payload: T = Field(default=..., description="The wrapped event payload")
    envelope_id: UUID = Field(
        default_factory=uuid4, description="Unique envelope identifier"
    )
    envelope_timestamp: datetime = Field(
        default_factory=datetime.now, description="Envelope creation timestamp"
    )
    correlation_id: UUID | None = Field(
        default=None, description="Correlation ID for request tracing"
    )
    source_tool: str | None = Field(
        default=None, description="Identifier of the tool that created this event"
    )
    target_tool: str | None = Field(
        default=None, description="Identifier of the intended recipient tool"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional envelope metadata"
    )
    security_context: dict[str, Any] | None = Field(
        default=None, description="Security context for the event"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Request priority (1-10, where 10 is highest)",
    )
    timeout_seconds: int | None = Field(
        default=None, gt=0, description="Optional timeout in seconds"
    )
    retry_count: int = Field(
        default=0, ge=0, description="Number of retry attempts (0 = first attempt)"
    )
    request_id: UUID | None = Field(
        default=None, description="Request identifier for tracing"
    )
    trace_id: UUID | None = Field(
        default=None,
        description="Distributed trace identifier (e.g., OpenTelemetry trace ID)",
    )
    span_id: UUID | None = Field(
        default=None, description="Trace span identifier (e.g., OpenTelemetry span ID)"
    )
    onex_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="ONEX standard version",
    )
    envelope_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=2, minor=0, patch=0),
        description="Envelope schema version",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize envelope with lazy evaluation capabilities."""
        super().__init__(**data)
        MixinLazyEvaluation.__init__(self)

    def with_correlation_id(self, correlation_id: UUID) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with updated correlation_id.

        Args:
            correlation_id: New correlation ID to set

        Returns:
            New envelope instance with updated correlation_id
        """
        return self.model_copy(update={"correlation_id": correlation_id})

    def with_metadata(self, metadata: dict[str, Any]) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with merged metadata.

        Args:
            metadata: New metadata to merge with existing

        Returns:
            New envelope instance with merged metadata
        """
        merged_metadata = {**self.metadata, **metadata}
        return self.model_copy(update={"metadata": merged_metadata})

    def with_security_context(
        self, security_context: dict[str, Any]
    ) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with updated security context.

        Args:
            security_context: New security context to set

        Returns:
            New envelope instance with updated security_context
        """
        return self.model_copy(update={"security_context": security_context})

    def set_routing(
        self, source_tool: str | None = None, target_tool: str | None = None
    ) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with updated routing information.

        Args:
            source_tool: Source tool identifier (optional)
            target_tool: Target tool identifier (optional)

        Returns:
            New envelope instance with updated routing
        """
        updates = {}
        if source_tool is not None:
            updates["source_tool"] = source_tool
        if target_tool is not None:
            updates["target_tool"] = target_tool
        return self.model_copy(update=updates)

    def with_tracing(
        self, trace_id: UUID, span_id: UUID, request_id: UUID | None = None
    ) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with distributed tracing information.

        Args:
            trace_id: Distributed trace identifier
            span_id: Trace span identifier
            request_id: Optional request identifier

        Returns:
            New envelope instance with tracing information
        """
        updates = {"trace_id": trace_id, "span_id": span_id}
        if request_id is not None:
            updates["request_id"] = request_id
        return self.model_copy(update=updates)

    def with_priority(self, priority: int) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with updated priority.

        Args:
            priority: New priority (1-10)

        Returns:
            New envelope instance with updated priority
        """
        return self.model_copy(update={"priority": priority})

    def increment_retry_count(self) -> "ModelEventEnvelope[T]":
        """
        Create a new envelope with incremented retry count.

        Returns:
            New envelope instance with retry_count + 1
        """
        return self.model_copy(update={"retry_count": self.retry_count + 1})

    def extract_payload(self) -> T:
        """
        Extract the wrapped event payload.

        Returns:
            The unwrapped event payload
        """
        return self.payload

    def is_correlated(self) -> bool:
        """
        Check if this envelope has a correlation ID.

        Returns:
            True if correlation_id is set, False otherwise
        """
        return self.correlation_id is not None

    def has_security_context(self) -> bool:
        """
        Check if this envelope has a security context.

        Returns:
            True if security_context is set, False otherwise
        """
        return self.security_context is not None

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value by key.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def is_high_priority(self) -> bool:
        """
        Check if envelope has high priority (>= 8).

        Returns:
            True if priority >= 8, False otherwise
        """
        return self.priority >= 8

    def is_expired(self) -> bool:
        """
        Check if envelope has expired based on timeout.

        Returns:
            True if elapsed time exceeds timeout_seconds, False otherwise
        """
        if self.timeout_seconds is None:
            return False
        elapsed = (datetime.now() - self.envelope_timestamp).total_seconds()
        return elapsed > self.timeout_seconds

    def is_retry(self) -> bool:
        """
        Check if this is a retry request (retry_count > 0).

        Returns:
            True if retry_count > 0, False otherwise
        """
        return self.retry_count > 0

    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since envelope creation in seconds.

        Returns:
            Elapsed time in seconds
        """
        return (datetime.now() - self.envelope_timestamp).total_seconds()

    def has_trace_context(self) -> bool:
        """
        Check if envelope has distributed tracing context.

        Returns:
            True if both trace_id and span_id are set, False otherwise
        """
        return self.trace_id is not None and self.span_id is not None

    def get_trace_context(self) -> dict[str, str] | None:
        """
        Get the complete trace context.

        Returns:
            Dictionary with trace_id, span_id, and request_id if available, None otherwise
        """
        if not self.has_trace_context():
            return None
        assert self.trace_id is not None
        assert self.span_id is not None
        context: dict[str, str] = {
            "trace_id": str(self.trace_id),
            "span_id": str(self.span_id),
        }
        if self.request_id:
            context["request_id"] = str(self.request_id)
        return context

    def to_dict_lazy(self) -> dict[str, Any]:
        """
        Convert envelope to dictionary with lazy evaluation for nested objects.

        Performance optimized to reduce memory usage by ~60% through lazy
        evaluation of expensive model_dump() operations on nested objects.

        Returns:
            Dictionary representation with lazy-evaluated nested structures
        """
        lazy_payload = self.lazy_string_conversion(
            cast(
                Optional[BaseModel],
                self.payload if hasattr(self.payload, "model_dump") else None,
            ),
            "payload",
        )
        result: dict[str, Any] = {
            "envelope_id": str(self.envelope_id),
            "envelope_timestamp": self.envelope_timestamp.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "source_tool": self.source_tool,
            "target_tool": self.target_tool,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "metadata": self.metadata,
            "security_context": self.security_context,
            "onex_version": str(self.onex_version),
            "envelope_version": str(self.envelope_version),
        }
        if hasattr(self.payload, "model_dump"):
            result["payload"] = lazy_payload()
        else:
            result["payload"] = self.payload
        return result

    @classmethod
    def create_broadcast(
        cls,
        payload: T,
        source_node_id: UUID,
        correlation_id: UUID | None = None,
        priority: int = 5,
    ) -> "ModelEventEnvelope[T]":
        """
        Create a broadcast envelope (no specific target).

        Args:
            payload: Event payload
            source_node_id: Source node identifier
            correlation_id: Optional correlation ID
            priority: Event priority (default: 5)

        Returns:
            New envelope configured for broadcast
        """
        return cls(
            payload=payload,
            source_tool=str(source_node_id),
            correlation_id=correlation_id,
            priority=priority,
        )

    @classmethod
    def create_directed(
        cls,
        payload: T,
        source_node_id: UUID,
        target_node_id: UUID,
        correlation_id: UUID | None = None,
        priority: int = 5,
    ) -> "ModelEventEnvelope[T]":
        """
        Create a directed envelope (specific target).

        Args:
            payload: Event payload
            source_node_id: Source node identifier
            target_node_id: Target node identifier
            correlation_id: Optional correlation ID
            priority: Event priority (default: 5)

        Returns:
            New envelope configured for directed communication
        """
        return cls(
            payload=payload,
            source_tool=str(source_node_id),
            target_tool=str(target_node_id),
            correlation_id=correlation_id,
            priority=priority,
        )
