"""
ONEX Envelope Model Implementation

Pydantic model implementing the ONEX standard envelope pattern.
Provides request wrapping with metadata, correlation IDs, and security context.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from omnibase_core.core.adapters.adapter_bus_shim import ModelEventBusMessage
from omnibase_core.core.models.model_onex_security_context import \
    ModelOnexSecurityContext
from omnibase_core.core.protocols.protocol_onex_validation import \
    ModelOnexMetadata
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelOnexEnvelope(BaseModel):
    """
    ONEX standard envelope implementation.

    Wraps request payloads with standardized metadata, correlation tracking,
    and security context for ONEX tool communication.
    """

    # === CORE ENVELOPE FIELDS ===
    envelope_id: UUID = Field(
        default_factory=uuid4, description="Unique envelope identifier"
    )
    correlation_id: UUID = Field(
        default_factory=uuid4, description="Request correlation identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Envelope creation timestamp"
    )

    # === ROUTING INFORMATION ===
    source_tool: Optional[str] = Field(
        default=None, description="Source tool identifier"
    )
    target_tool: Optional[str] = Field(
        default=None, description="Target tool identifier"
    )
    operation: Optional[str] = Field(default=None, description="Requested operation")

    # === PAYLOAD ===
    payload: ModelEventBusMessage = Field(description="The actual event bus message")
    payload_type: str = Field(description="Type of event payload")

    # === SECURITY CONTEXT ===
    security_context: Optional[ModelOnexSecurityContext] = Field(
        default=None, description="Security context information"
    )

    # === METADATA ===
    metadata: Optional[ModelOnexMetadata] = Field(
        default=None, description="Additional envelope metadata"
    )

    # === ONEX COMPLIANCE ===
    onex_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="ONEX standard version",
    )
    envelope_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Envelope schema version",
    )

    # === TRACKING INFORMATION ===
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    trace_id: Optional[str] = Field(
        default=None, description="Distributed trace identifier"
    )
    span_id: Optional[str] = Field(default=None, description="Trace span identifier")

    # === QUALITY OF SERVICE ===
    priority: int = Field(default=5, description="Request priority (1-10, 10=highest)")
    timeout_seconds: Optional[int] = Field(
        default=None, description="Request timeout in seconds"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")

    class Config:
        """Pydantic configuration."""

        frozen = True
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}

    @validator("priority")
    def validate_priority(cls, v: int) -> int:
        """Validate priority is within valid range."""
        if v < 1 or v > 10:
            raise ValueError("Priority must be between 1 and 10")
        return v

    @validator("timeout_seconds")
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout is positive."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @validator("retry_count")
    def validate_retry_count(cls, v: int) -> int:
        """Validate retry count is non-negative."""
        if v < 0:
            raise ValueError("Retry count must be non-negative")
        return v

    @validator("payload_type")
    def validate_payload_type(cls, v: str) -> str:
        """Validate payload type is specified."""
        if not v or not v.strip():
            raise ValueError("Payload type must be specified")
        return v.strip()

    def with_metadata(self, metadata: ModelOnexMetadata) -> "ModelOnexEnvelope":
        """
        Add metadata to the envelope.

        Args:
            metadata: Structured metadata model

        Returns:
            New envelope instance with metadata
        """
        return self.copy(update={"metadata": metadata})

    def with_security_context(
        self, security_context: ModelOnexSecurityContext
    ) -> "ModelOnexEnvelope":
        """
        Add security context to the envelope.

        Args:
            security_context: Security context to add

        Returns:
            New envelope instance with security context
        """
        return self.copy(update={"security_context": security_context})

    def with_routing(
        self, source_tool: str, target_tool: str, operation: str
    ) -> "ModelOnexEnvelope":
        """
        Add routing information to the envelope.

        Args:
            source_tool: Source tool identifier
            target_tool: Target tool identifier
            operation: Operation to perform

        Returns:
            New envelope instance with routing information
        """
        return self.copy(
            update={
                "source_tool": source_tool,
                "target_tool": target_tool,
                "operation": operation,
            }
        )

    def with_tracing(
        self, trace_id: str, span_id: str, request_id: Optional[str] = None
    ) -> "ModelOnexEnvelope":
        """
        Add distributed tracing information to the envelope.

        Args:
            trace_id: Distributed trace identifier
            span_id: Trace span identifier
            request_id: Optional request identifier

        Returns:
            New envelope instance with tracing information
        """
        return self.copy(
            update={"trace_id": trace_id, "span_id": span_id, "request_id": request_id}
        )

    def increment_retry_count(self) -> "ModelOnexEnvelope":
        """
        Increment the retry count for the envelope.

        Returns:
            New envelope instance with incremented retry count
        """
        return self.copy(update={"retry_count": self.retry_count + 1})

    def is_high_priority(self) -> bool:
        """Check if envelope has high priority (>= 8)."""
        return self.priority >= 8

    def is_expired(self) -> bool:
        """Check if envelope has expired based on timeout."""
        if self.timeout_seconds is None:
            return False

        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.timeout_seconds

    def has_security_context(self) -> bool:
        """Check if envelope has security context."""
        return self.security_context is not None

    def is_retry(self) -> bool:
        """Check if this is a retry request."""
        return self.retry_count > 0

    def get_elapsed_time(self) -> float:
        """Get elapsed time since envelope creation in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()

    def to_dict(self) -> Dict[str, str]:
        """Convert envelope to dictionary representation."""
        return {
            "envelope_id": str(self.envelope_id),
            "correlation_id": str(self.correlation_id),
            "timestamp": self.timestamp.isoformat(),
            "source_tool": self.source_tool,
            "target_tool": self.target_tool,
            "operation": self.operation,
            "payload": str(self.payload.dict()) if self.payload else "",
            "payload_type": self.payload_type or "",
            "security_context": (
                str(self.security_context.dict()) if self.security_context else ""
            ),
            "metadata": str(self.metadata.dict()) if self.metadata else "",
            "onex_version": str(self.onex_version),
            "envelope_version": str(self.envelope_version),
            "request_id": self.request_id or "",
            "trace_id": self.trace_id or "",
            "span_id": self.span_id or "",
            "priority": str(self.priority),
            "timeout_seconds": str(self.timeout_seconds),
            "retry_count": str(self.retry_count),
        }
