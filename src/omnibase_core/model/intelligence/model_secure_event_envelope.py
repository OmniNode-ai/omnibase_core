# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# description: Secure event envelope with comprehensive validation and error recovery
# lifecycle: active
# meta_type: model
# name: model_secure_event_envelope.py
# namespace: python://omnibase.model.intelligence.model_secure_event_envelope
# owner: OmniNode Team
# version: 1.0.0
# === /OmniNode:Metadata ===

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.enums.enum_intelligence_priority_level import \
    EnumIntelligencePriorityLevel
from omnibase_core.exceptions import OnexError

from .model_event_audit_trail import (ModelEventAuditTrail,
                                      ModelEventSecurityContext)
from .model_secure_event_payload import ModelSecureEventPayload


class ModelSecureEventEnvelope(BaseModel):
    """
    Enterprise-grade secure event envelope with comprehensive validation, error recovery,
    and audit trail generation.

    Provides:
    - Zero-trust security validation
    - Comprehensive audit trail tracking
    - Error recovery mechanisms
    - Performance monitoring
    - Data integrity verification
    - Fail-safe processing patterns
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
    )

    # Core envelope metadata
    envelope_id: UUID = Field(
        default_factory=uuid4, description="Unique envelope identifier"
    )
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    correlation_id: Optional[UUID] = Field(
        None, description="Request correlation identifier"
    )

    # Event classification
    event_type: str = Field(..., description="Event type identifier")
    event_version: str = Field(default="1.0.0", description="Event schema version")
    priority: EnumIntelligencePriorityLevel = Field(
        default=EnumIntelligencePriorityLevel.HIGH,
        description="Event processing priority",
    )

    # Timing and lifecycle
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Event creation time"
    )
    expires_at: Optional[datetime] = Field(None, description="Event expiration time")
    retry_until: Optional[datetime] = Field(None, description="Retry deadline")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    current_retry: int = Field(default=0, description="Current retry attempt")

    # Source and routing information
    source_node_id: str = Field(..., description="Source node identifier")
    target_node_ids: Optional[list[str]] = Field(
        None, description="Target node identifiers"
    )
    routing_metadata: Dict[str, str] = Field(
        default_factory=dict, description="Routing metadata"
    )

    # Secure payload
    payload: ModelSecureEventPayload = Field(
        ..., description="Secure validated payload"
    )

    # Audit and security
    audit_trail: ModelEventAuditTrail = Field(
        ..., description="Comprehensive audit trail"
    )
    integrity_hash: str = Field(..., description="Payload integrity hash")
    security_verified: bool = Field(
        default=False, description="Security validation status"
    )

    # Error handling and recovery
    processing_errors: list[Dict[str, Any]] = Field(
        default_factory=list, description="Processing errors encountered"
    )
    recovery_state: Dict[str, Any] = Field(
        default_factory=dict, description="Recovery state information"
    )

    # Performance tracking
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Performance metrics"
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """
        Validate event type format.

        Args:
            v: Event type string

        Returns:
            Validated event type

        Raises:
            OnexError: If event type format is invalid
        """
        if not isinstance(v, str) or len(v) < 3 or len(v) > 128:
            raise OnexError(
                f"Invalid event type format: {v}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_event_type",
            )

        # Validate namespace.category.action format
        parts = v.split(".")
        if len(parts) < 2 or len(parts) > 4:
            raise OnexError(
                f"Event type must follow namespace.category[.subcategory].action format: {v}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_event_type",
            )

        # Check for valid characters (alphanumeric, underscore, hyphen)
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise OnexError(
                f"Event type contains invalid characters: {v}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_event_type",
            )

        return v

    @field_validator("source_node_id")
    @classmethod
    def validate_source_node_id(cls, v: str) -> str:
        """
        Validate source node identifier.

        Args:
            v: Source node ID string

        Returns:
            Validated source node ID

        Raises:
            OnexError: If source node ID is invalid
        """
        if not isinstance(v, str) or len(v) < 1 or len(v) > 128:
            raise OnexError(
                f"Invalid source node ID: {v}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_source_node_id",
            )

        # Must match the payload source node ID
        # This will be validated in model_validator

        return v

    @field_validator("target_node_ids")
    @classmethod
    def validate_target_node_ids(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """
        Validate target node identifiers.

        Args:
            v: List of target node IDs

        Returns:
            Validated list of target node IDs

        Raises:
            OnexError: If target node IDs are invalid
        """
        if v is None:
            return v

        if not isinstance(v, list) or len(v) == 0 or len(v) > 100:
            raise OnexError(
                f"Invalid target node IDs list: {len(v) if isinstance(v, list) else 'not a list'}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_target_node_ids",
            )

        for node_id in v:
            if not isinstance(node_id, str) or len(node_id) < 1 or len(node_id) > 128:
                raise OnexError(
                    f"Invalid target node ID: {node_id}",
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    component="ModelSecureEventEnvelope",
                    operation="validate_target_node_ids",
                )

        return v

    @field_validator("expires_at", "retry_until")
    @classmethod
    def validate_future_datetime(cls, v: Optional[datetime]) -> Optional[datetime]:
        """
        Validate that datetime is in the future.

        Args:
            v: Datetime value

        Returns:
            Validated datetime

        Raises:
            OnexError: If datetime is in the past
        """
        if v is not None and v <= datetime.utcnow():
            raise OnexError(
                f"Datetime must be in the future: {v}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_future_datetime",
            )

        return v

    @model_validator(mode="after")
    def validate_envelope_integrity(self) -> "ModelSecureEventEnvelope":
        """
        Validate envelope integrity and consistency.

        Returns:
            Validated envelope

        Raises:
            OnexError: If envelope integrity checks fail
        """
        # Ensure source node IDs match between envelope and payload
        if self.source_node_id != self.payload.source_node_id:
            raise OnexError(
                f"Source node ID mismatch: envelope={self.source_node_id}, payload={self.payload.source_node_id}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_envelope_integrity",
            )

        # Ensure correlation IDs match if both are present
        if self.correlation_id and self.payload.correlation_id:
            if self.correlation_id != self.payload.correlation_id:
                raise OnexError(
                    f"Correlation ID mismatch: envelope={self.correlation_id}, payload={self.payload.correlation_id}",
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    component="ModelSecureEventEnvelope",
                    operation="validate_envelope_integrity",
                )

        # Validate retry logic
        if self.current_retry > self.max_retries:
            raise OnexError(
                f"Current retry {self.current_retry} exceeds max retries {self.max_retries}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_envelope_integrity",
            )

        # Ensure audit trail has matching event ID
        if self.audit_trail.event_id != self.event_id:
            raise OnexError(
                f"Audit trail event ID mismatch: audit={self.audit_trail.event_id}, envelope={self.event_id}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
                component="ModelSecureEventEnvelope",
                operation="validate_envelope_integrity",
            )

        return self

    @classmethod
    def create_secure_envelope(
        cls,
        event_type: str,
        source_node_id: str,
        payload_data: Dict[str, Any],
        correlation_id: Optional[UUID] = None,
        priority: EnumIntelligencePriorityLevel = EnumIntelligencePriorityLevel.HIGH,
        target_node_ids: Optional[list[str]] = None,
        ttl_hours: int = 24,
    ) -> "ModelSecureEventEnvelope":
        """
        Factory method to create a secure event envelope.

        Args:
            event_type: Event type identifier
            source_node_id: Source node identifier
            payload_data: Event payload data
            correlation_id: Optional correlation identifier
            priority: Event processing priority
            target_node_ids: Optional target node identifiers
            ttl_hours: Time-to-live in hours

        Returns:
            Secure event envelope instance

        Raises:
            OnexError: If envelope creation fails
        """
        try:
            event_id = uuid4()

            # Create secure payload
            payload = ModelSecureEventPayload(
                event_data=payload_data,
                source_node_id=source_node_id,
                correlation_id=correlation_id,
            )

            # Create security context
            security_context = ModelEventSecurityContext(
                validation_passed=True,
                input_sanitized=True,
                malicious_patterns_detected=[],
                threat_level="low",
            )

            # Create audit trail
            audit_trail = ModelEventAuditTrail(
                event_id=event_id,
                correlation_id=correlation_id,
                event_type=event_type,
                source_node_id=source_node_id,
                security_context=security_context,
                priority_level=priority,
            )

            # Calculate integrity hash
            integrity_hash = cls._calculate_integrity_hash(payload)

            # Set expiration
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            retry_until = datetime.utcnow() + timedelta(
                hours=min(ttl_hours, 6)
            )  # Max 6 hours retry window

            envelope = cls(
                event_id=event_id,
                correlation_id=correlation_id,
                event_type=event_type,
                priority=priority,
                expires_at=expires_at,
                retry_until=retry_until,
                source_node_id=source_node_id,
                target_node_ids=target_node_ids,
                payload=payload,
                audit_trail=audit_trail,
                integrity_hash=integrity_hash,
                security_verified=True,
            )

            return envelope

        except Exception as e:
            raise OnexError(
                f"Failed to create secure envelope: {e}",
                error_code=CoreErrorCode.OPERATION_FAILED,
                component="ModelSecureEventEnvelope",
                operation="create_secure_envelope",
            ) from e

    @staticmethod
    def _calculate_integrity_hash(payload: ModelSecureEventPayload) -> str:
        """
        Calculate integrity hash for payload.

        Args:
            payload: Secure event payload

        Returns:
            SHA-256 hash of payload
        """
        # Create deterministic string representation
        payload_dict = {
            "event_data": payload.event_data,
            "metadata": payload.metadata,
            "source_node_id": payload.source_node_id,
            "correlation_id": (
                str(payload.correlation_id) if payload.correlation_id else None
            ),
            "security_context": payload.security_context,
        }

        payload_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify payload integrity against stored hash.

        Returns:
            True if integrity is verified, False otherwise
        """
        current_hash = self._calculate_integrity_hash(self.payload)
        return current_hash == self.integrity_hash

    def is_expired(self) -> bool:
        """
        Check if envelope has expired.

        Returns:
            True if expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def can_retry(self) -> bool:
        """
        Check if envelope can be retried.

        Returns:
            True if retry is allowed, False otherwise
        """
        if self.current_retry >= self.max_retries:
            return False

        if self.retry_until is None:
            return True

        return datetime.utcnow() <= self.retry_until

    def increment_retry(self) -> None:
        """Increment retry counter and update audit trail."""
        self.current_retry += 1
        self.audit_trail.recovery_attempts += 1
        self.audit_trail.last_error_recovery_at = datetime.utcnow()

    def add_processing_error(
        self,
        error_type: str,
        error_message: str,
        component: str,
        operation: str,
        recoverable: bool = True,
    ) -> None:
        """
        Add processing error to envelope and audit trail.

        Args:
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
            operation: Operation that failed
            recoverable: Whether error is recoverable
        """
        error_entry = {
            "error_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "component": component,
            "operation": operation,
            "recoverable": recoverable,
            "retry_attempt": self.current_retry,
        }

        self.processing_errors.append(error_entry)
        self.audit_trail.add_error(
            error_type, error_message, component, operation, recoverable
        )

    def update_performance_metric(self, metric_name: str, value: float) -> None:
        """
        Update performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        self.performance_metrics[metric_name] = value
        self.audit_trail.performance_metrics[metric_name] = value

    def get_processing_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive processing summary.

        Returns:
            Dictionary with processing summary
        """
        return {
            "envelope_id": str(self.envelope_id),
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "priority": self.priority.value,
            "source_node_id": self.source_node_id,
            "current_retry": self.current_retry,
            "max_retries": self.max_retries,
            "is_expired": self.is_expired(),
            "can_retry": self.can_retry(),
            "integrity_verified": self.verify_integrity(),
            "security_verified": self.security_verified,
            "error_count": len(self.processing_errors),
            "audit_summary": self.audit_trail.get_processing_summary(),
            "performance_metrics": dict(self.performance_metrics),
        }

    def to_secure_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary with sensitive data removed.

        Returns:
            Secure dictionary representation
        """
        return {
            "envelope_id": str(self.envelope_id),
            "event_id": str(self.event_id),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "event_type": self.event_type,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "source_node_id": self.source_node_id,
            "target_node_ids": self.target_node_ids,
            "security_verified": self.security_verified,
            "integrity_hash": self.integrity_hash,
            "current_retry": self.current_retry,
            "max_retries": self.max_retries,
            "payload_summary": self.payload.to_audit_dict(),
            "audit_summary": self.audit_trail.get_processing_summary(),
            "error_count": len(self.processing_errors),
            "performance_metrics": dict(self.performance_metrics),
        }
