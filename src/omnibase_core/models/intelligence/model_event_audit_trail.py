# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# description: Comprehensive audit trail model for event processing
# lifecycle: active
# meta_type: model
# name: model_event_audit_trail.py
# namespace: python://omnibase.model.intelligence.model_event_audit_trail
# owner: OmniNode Team
# version: 1.0.0
# === /OmniNode:Metadata ===

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_intelligence_priority_level import (
    EnumIntelligencePriorityLevel,
)


class ModelEventProcessingStep(BaseModel):
    """Individual step in event processing pipeline."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    step_id: UUID = Field(default_factory=uuid4, description="Unique step identifier")
    step_name: str = Field(..., description="Name of processing step")
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Step start time",
    )
    completed_at: datetime | None = Field(None, description="Step completion time")
    status: str = Field(
        ...,
        description="Step status: pending, processing, completed, failed",
    )
    error_message: str | None = Field(
        None,
        description="Error message if step failed",
    )
    processing_node_id: str = Field(..., description="Node that processed this step")
    input_hash: str | None = Field(None, description="Hash of input data")
    output_hash: str | None = Field(None, description="Hash of output data")
    processing_time_ms: int | None = Field(
        None,
        description="Processing time in milliseconds",
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")


class ModelEventSecurityContext(BaseModel):
    """Security context and validation results for event."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    validation_passed: bool = Field(
        ...,
        description="Whether security validation passed",
    )
    validation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When validation occurred",
    )
    input_sanitized: bool = Field(..., description="Whether input was sanitized")
    malicious_patterns_detected: list[str] = Field(
        default_factory=list,
        description="Detected malicious patterns",
    )
    source_ip: str | None = Field(None, description="Source IP address")
    user_agent: str | None = Field(None, description="User agent string")
    authentication_method: str | None = Field(
        None,
        description="Authentication method used",
    )
    authorization_level: str | None = Field(None, description="Authorization level")
    threat_level: str = Field(
        default="low",
        description="Assessed threat level: low, medium, high, critical",
    )


class ModelEventAuditTrail(BaseModel):
    """
    Comprehensive audit trail for event processing with security monitoring.

    Provides complete tracking of event lifecycle from ingestion to completion,
    including security validation, error handling, and performance metrics.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Core audit identifiers
    audit_id: UUID = Field(
        default_factory=uuid4,
        description="Unique audit trail identifier",
    )
    event_id: UUID = Field(..., description="Original event identifier being audited")
    correlation_id: UUID | None = Field(
        None,
        description="Request correlation identifier",
    )

    # Event metadata
    event_type: str = Field(..., description="Type of event being processed")
    source_node_id: str = Field(
        ...,
        description="Node that generated the original event",
    )
    processing_node_ids: list[str] = Field(
        default_factory=list,
        description="All nodes that processed this event",
    )

    # Timing information
    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When event was first received",
    )
    processing_started_at: datetime | None = Field(
        None,
        description="When processing started",
    )
    processing_completed_at: datetime | None = Field(
        None,
        description="When processing completed",
    )
    total_processing_time_ms: int | None = Field(
        None,
        description="Total processing time in milliseconds",
    )

    # Processing pipeline
    processing_steps: list[ModelEventProcessingStep] = Field(
        default_factory=list,
        description="Detailed processing steps",
    )

    # Security context
    security_context: ModelEventSecurityContext = Field(
        ...,
        description="Security validation and context",
    )

    # Status tracking
    current_status: str = Field(
        default="received",
        description="Current status: received, validating, processing, completed, failed",
    )
    final_status: str | None = Field(None, description="Final processing status")

    # Error handling
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="All errors encountered during processing",
    )
    recovery_attempts: int = Field(
        default=0,
        description="Number of recovery attempts made",
    )
    last_error_recovery_at: datetime | None = Field(
        None,
        description="Timestamp of last error recovery",
    )

    # Performance metrics
    performance_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics: latency, throughput, etc.",
    )

    # Data integrity
    input_data_hash: str | None = Field(
        None,
        description="Hash of original input data",
    )
    output_data_hash: str | None = Field(
        None,
        description="Hash of final output data",
    )
    data_integrity_verified: bool = Field(
        default=False,
        description="Whether data integrity was verified",
    )

    # Priority and routing
    priority_level: EnumIntelligencePriorityLevel = Field(
        default=EnumIntelligencePriorityLevel.HIGH,
        description="Event processing priority",
    )
    routing_path: list[str] = Field(
        default_factory=list,
        description="Path event took through system",
    )

    # Compliance and retention
    retention_policy: str = Field(
        default="standard",
        description="Data retention policy applied",
    )
    compliance_flags: list[str] = Field(
        default_factory=list,
        description="Compliance requirements that apply",
    )

    def add_processing_step(
        self,
        step_name: str,
        processing_node_id: str,
        status: str = "processing",
        input_hash: str | None = None,
    ) -> ModelEventProcessingStep:
        """
        Add a new processing step to the audit trail.

        Args:
            step_name: Name of the processing step
            processing_node_id: Node performing the processing
            status: Initial status of the step
            input_hash: Hash of input data for this step

        Returns:
            The created processing step
        """
        step = ModelEventProcessingStep(
            step_name=step_name,
            processing_node_id=processing_node_id,
            status=status,
            input_hash=input_hash,
        )

        self.processing_steps.append(step)

        # Update processing node list
        if processing_node_id not in self.processing_node_ids:
            self.processing_node_ids.append(processing_node_id)

        # Update routing path
        if processing_node_id not in self.routing_path:
            self.routing_path.append(processing_node_id)

        return step

    def complete_processing_step(
        self,
        step_id: UUID,
        status: str = "completed",
        output_hash: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        Mark a processing step as completed.

        Args:
            step_id: ID of the step to complete
            status: Final status of the step
            output_hash: Hash of output data
            error_message: Error message if step failed

        Returns:
            True if step was found and updated, False otherwise
        """
        for step in self.processing_steps:
            if step.step_id == step_id:
                step.completed_at = datetime.utcnow()
                step.status = status
                step.output_hash = output_hash
                step.error_message = error_message

                # Calculate processing time
                if step.started_at:
                    processing_time = step.completed_at - step.started_at
                    step.processing_time_ms = int(
                        processing_time.total_seconds() * 1000,
                    )

                return True
        return False

    def add_error(
        self,
        error_type: str,
        error_message: str,
        component: str,
        operation: str,
        recovery_attempted: bool = False,
    ) -> None:
        """
        Add an error to the audit trail.

        Args:
            error_type: Type/category of error
            error_message: Detailed error message
            component: Component where error occurred
            operation: Operation that caused the error
            recovery_attempted: Whether recovery was attempted
        """
        error_entry = {
            "error_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "component": component,
            "operation": operation,
            "recovery_attempted": recovery_attempted,
        }

        self.errors.append(error_entry)

        if recovery_attempted:
            self.recovery_attempts += 1
            self.last_error_recovery_at = datetime.utcnow()

    def update_security_threat_level(self, threat_level: str, reason: str) -> None:
        """
        Update security threat level with reason.

        Args:
            threat_level: New threat level (low, medium, high, critical)
            reason: Reason for threat level change
        """
        self.security_context.threat_level = threat_level

        # Log the threat level change
        self.add_error(
            error_type="security_threat_level_change",
            error_message=f"Threat level changed to {threat_level}: {reason}",
            component="ModelEventAuditTrail",
            operation="update_security_threat_level",
            recovery_attempted=False,
        )

    def start_processing(self) -> None:
        """Mark event processing as started."""
        self.processing_started_at = datetime.utcnow()
        self.current_status = "processing"

    def complete_processing(self, final_status: str = "completed") -> None:
        """
        Mark event processing as completed.

        Args:
            final_status: Final processing status
        """
        self.processing_completed_at = datetime.utcnow()
        self.current_status = "completed"
        self.final_status = final_status

        # Calculate total processing time
        if self.processing_started_at:
            total_time = self.processing_completed_at - self.processing_started_at
            self.total_processing_time_ms = int(total_time.total_seconds() * 1000)

    def get_processing_summary(self) -> dict[str, Any]:
        """
        Get a summary of processing metrics and status.

        Returns:
            Dictionary with processing summary information
        """
        completed_steps = sum(
            1 for step in self.processing_steps if step.status == "completed"
        )
        failed_steps = sum(
            1 for step in self.processing_steps if step.status == "failed"
        )

        return {
            "audit_id": str(self.audit_id),
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "current_status": self.current_status,
            "final_status": self.final_status,
            "total_processing_time_ms": self.total_processing_time_ms,
            "total_steps": len(self.processing_steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "error_count": len(self.errors),
            "recovery_attempts": self.recovery_attempts,
            "threat_level": self.security_context.threat_level,
            "nodes_involved": len(self.processing_node_ids),
            "routing_path": self.routing_path,
            "data_integrity_verified": self.data_integrity_verified,
        }

    def is_processing_healthy(self) -> bool:
        """
        Check if event processing is healthy (no critical errors or excessive delays).

        Returns:
            True if processing is healthy, False otherwise
        """
        # Check for critical threat level
        if self.security_context.threat_level == "critical":
            return False

        # Check for excessive processing time (>30 seconds)
        if self.total_processing_time_ms and self.total_processing_time_ms > 30_000:
            return False

        # Check for too many recovery attempts (>3)
        if self.recovery_attempts > 3:
            return False

        # Check for failed steps without recovery
        for step in self.processing_steps:
            if step.status == "failed" and step.retry_count == 0:
                return False

        return True

    def should_trigger_alert(self) -> bool:
        """
        Determine if this audit trail should trigger an alert.

        Returns:
            True if alert should be triggered, False otherwise
        """
        # High/critical threat level
        if self.security_context.threat_level in ["high", "critical"]:
            return True

        # Multiple errors
        if len(self.errors) >= 3:
            return True

        # Long processing time (>10 seconds)
        if self.total_processing_time_ms and self.total_processing_time_ms > 10_000:
            return True

        # Multiple recovery attempts
        return self.recovery_attempts >= 2
