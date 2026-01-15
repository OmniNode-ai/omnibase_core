from __future__ import annotations

__all__ = ["ModelEventBusOutputState"]

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import MAX_ERROR_MESSAGE_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_error_summary import ModelErrorSummary
from omnibase_core.models.core.model_monitoring_metrics import ModelMonitoringMetrics
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
    parse_semver_from_string,
)
from omnibase_core.models.services.model_error_details import ModelErrorDetails

from .model_event_bus_output_field import ModelEventBusOutputField

if TYPE_CHECKING:
    from omnibase_core.models.core.model_business_impact import ModelBusinessImpact


class ModelEventBusOutputState(BaseModel):
    """
    Enterprise-grade output state for event bus nodes with comprehensive status tracking,
    operational metrics, and business intelligence capabilities.

    Features:
    - Comprehensive status tracking with business logic
    - Performance metrics and timing analysis
    - Error handling and recovery recommendations
    - Operational metadata and monitoring integration
    - Business intelligence and analytics support
    - Factory methods for common scenarios

    Note:
        Error codes are validated using a SIMPLER pattern (_ERROR_CODE_PATTERN)
        than the standard ERROR_CODE_PATTERN. This pattern accepts simple codes
        like "UNKNOWN", "TIMEOUT", etc. without requiring the CATEGORY_NNN suffix.
        This is intentional for event bus status codes which have different
        requirements than structured error codes.
    """

    # Private pattern for event bus error codes - intentionally simpler than
    # the centralized ERROR_CODE_PATTERN. Accepts codes like "UNKNOWN", "TIMEOUT"
    # without requiring the underscore-digit suffix (e.g., AUTH_001).
    _ERROR_CODE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Z][A-Z0-9_]*$")

    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Schema version for output state (matches input)",
    )
    status: EnumOnexStatus = Field(
        default=..., description="Execution status with business context"
    )
    message: str = Field(
        default=...,
        description="Human-readable result message with details",
        min_length=1,
        max_length=MAX_ERROR_MESSAGE_LENGTH,
    )
    output_field: ModelEventBusOutputField | None = Field(
        default=None, description="Canonical output field with processing results"
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking across operations",
    )
    event_id: UUID | None = Field(
        default=None,
        description="Unique event identifier",
    )
    processing_time_ms: int | None = Field(
        default=None, description="Processing time in milliseconds", ge=0
    )
    retry_attempt: int | None = Field(
        default=0, description="Current retry attempt number", ge=0, le=10
    )
    error_code: str | None = Field(
        default=None,
        description="Specific error code for programmatic handling",
        max_length=50,
    )
    # Note: type: ignore[type-arg] is intentional here. ModelErrorDetails is generic
    # with TContext bound to BaseModel, but we don't constrain to a specific context type
    # for event bus output. The context_data field within ModelErrorDetails accepts both
    # typed contexts AND dict[str, ModelSchemaValue], so this is safe at runtime.
    error_details: ModelErrorDetails | None = Field(  # type: ignore[type-arg]
        default=None, description="Detailed error information for debugging"
    )
    metrics: ModelMonitoringMetrics = Field(
        default_factory=lambda: ModelMonitoringMetrics(
            response_time_ms=None,
            throughput_rps=None,
            error_rate=None,
            success_rate=None,
            cpu_usage_percent=None,
            memory_usage_mb=None,
            disk_usage_gb=None,
            network_bandwidth_mbps=None,
            queue_depth=None,
            items_processed=None,
            items_failed=None,
            processing_lag_ms=None,
            compliance_score=None,
            reliability_score=None,
            availability_percent=None,
            uptime_seconds=None,
            last_error_timestamp=None,
            start_time=None,
            end_time=None,
            health_score=None,
            custom_metrics=None,
        ),
        description="Performance and operational metrics",
    )
    warnings: list[str] | None = Field(
        default_factory=list, description="Non-fatal warnings during processing"
    )
    next_retry_at: str | None = Field(
        default=None, description="ISO timestamp for next retry attempt"
    )

    @field_validator("version", mode="before")
    @classmethod
    def parse_version(cls, v: Any) -> ModelSemVer:
        """Parse and validate semantic version."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "version must be a string, dict[str, Any], or ModelSemVer"
        raise ModelOnexError(error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message content."""
        if not v or not v.strip():
            msg = "message cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        return v.strip()

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v: str | None) -> str | None:
        """Validate error code format using the simpler event bus pattern.

        Event bus error codes use a MORE PERMISSIVE pattern than the standard
        ERROR_CODE_PATTERN. This allows simple codes like "UNKNOWN", "TIMEOUT",
        "ERROR", etc. without requiring the CATEGORY_NNN suffix.

        The pattern accepts: uppercase letters, digits, and underscores.

        Args:
            v: The error code string to validate, or None.

        Returns:
            The validated error code (uppercase, stripped), or None.

        Raises:
            ModelOnexError: If the error code contains invalid characters.
        """
        if v is None:
            return v
        v = v.strip().upper()
        if not v:
            return None

        if not cls._ERROR_CODE_PATTERN.match(v):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Invalid error_code format '{v}': expected uppercase letters, "
                    f"digits, and underscores only (e.g., UNKNOWN, TIMEOUT, AUTH_001)."
                ),
            )
        return v

    def is_successful(self) -> bool:
        """Check if the operation was successful."""
        return self.status == EnumOnexStatus.SUCCESS

    def is_failed(self) -> bool:
        """Check if the operation failed."""
        return self.status in [EnumOnexStatus.ERROR, EnumOnexStatus.UNKNOWN]

    def is_retryable(self) -> bool:
        """Check if the operation can be retried."""
        retryable_statuses = [EnumOnexStatus.ERROR, EnumOnexStatus.PARTIAL]
        if self.retry_attempt and self.retry_attempt >= 5:
            return False
        return self.status in retryable_statuses

    def is_warning_only(self) -> bool:
        """Check if this represents a warning without failure."""
        return self.status == EnumOnexStatus.WARNING

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return bool(self.warnings)

    def get_severity_level(self) -> str:
        """Get human-readable severity level."""
        severity_map = {
            EnumOnexStatus.SUCCESS: "info",
            EnumOnexStatus.WARNING: "warning",
            EnumOnexStatus.ERROR: "error",
            EnumOnexStatus.SKIPPED: "info",
            EnumOnexStatus.FIXED: "info",
            EnumOnexStatus.PARTIAL: "warning",
            EnumOnexStatus.INFO: "info",
            EnumOnexStatus.UNKNOWN: "error",
        }
        return severity_map.get(self.status, "unknown")

    def get_performance_category(self) -> str:
        """Categorize performance based on processing time."""
        if not self.processing_time_ms:
            return "unknown"
        if self.processing_time_ms < 100:
            return "excellent"
        if self.processing_time_ms < 500:
            return "good"
        if self.processing_time_ms < 2000:
            return "acceptable"
        if self.processing_time_ms < 10000:
            return "slow"
        return "very_slow"

    def is_performance_concerning(self) -> bool:
        """Check if performance metrics indicate potential issues."""
        category = self.get_performance_category()
        return category in ["slow", "very_slow"]

    def get_processing_time_human(self) -> str:
        """Get human-readable processing time."""
        if not self.processing_time_ms:
            return "unknown"
        if self.processing_time_ms < 1000:
            return f"{self.processing_time_ms}ms"
        seconds = self.processing_time_ms / 1000
        return f"{seconds:.2f}s"

    def get_performance_recommendations(self) -> list[str]:
        """Get performance improvement recommendations."""
        recommendations = []
        if self.is_performance_concerning():
            recommendations.append(
                "Consider optimizing processing logic for better performance"
            )
        if self.retry_attempt and self.retry_attempt > 2:
            recommendations.append(
                "High retry count indicates potential systemic issues"
            )
        if self.has_warnings():
            recommendations.append(
                "Review warnings to prevent potential future failures"
            )
        return recommendations

    def get_error_summary(self) -> ModelErrorSummary | None:
        """Get comprehensive error summary."""
        if not self.is_failed():
            return None
        return ModelErrorSummary(
            error_code=self.error_code or "UNKNOWN",
            error_type=self.status.value,
            error_message=self.message,
            component="event_bus",
            operation="output_processing",
            stack_trace=None,
            impact_level="high" if self.status == EnumOnexStatus.ERROR else "medium",
            context_data={
                "retry_attempt": str(self.retry_attempt),
                "retryable": str(self.is_retryable()),
                "next_retry_at": self.next_retry_at or "",
            },
            error_id=self.correlation_id if self.correlation_id else None,
            correlation_id=self.correlation_id if self.correlation_id else None,
            has_been_reported=False,
        )

    def get_troubleshooting_steps(self) -> list[str]:
        """Get troubleshooting recommendations based on error patterns."""
        steps = []
        if self.error_code:
            steps.append(f"Check documentation for error code: {self.error_code}")
        if self.retry_attempt and self.retry_attempt > 0:
            steps.append("Review system logs for patterns in retry failures")
        if self.processing_time_ms and self.processing_time_ms > 30000:
            steps.append("Check for timeout-related issues or resource constraints")
        if self.is_retryable():
            steps.append("Consider increasing retry delays or checking system capacity")
        return steps

    def get_monitoring_metrics(self) -> ModelMonitoringMetrics:
        """Get metrics suitable for monitoring systems."""
        from omnibase_core.models.core.model_monitoring_metrics import (
            ModelMonitoringMetrics,
        )
        from omnibase_core.models.discovery.model_metric_value import ModelMetricValue

        success_rate = 100.0 if self.is_successful() else 0.0
        error_rate = 100.0 if self.is_failed() else 0.0
        return ModelMonitoringMetrics(
            response_time_ms=(
                float(self.processing_time_ms) if self.processing_time_ms else None
            ),
            success_rate=success_rate,
            error_rate=error_rate,
            health_score=(
                100.0
                if self.is_successful()
                else 50.0
                if self.is_warning_only()
                else 0.0
            ),
            custom_metrics={
                "status": ModelMetricValue(
                    name="status",
                    value=self.status.value,
                    metric_type="string",
                ),
                "severity": ModelMetricValue(
                    name="severity",
                    value=self.get_severity_level(),
                    metric_type="string",
                ),
                "retry_attempt": ModelMetricValue(
                    name="retry_attempt",
                    value=self.retry_attempt or 0,
                    metric_type="counter",
                ),
                "warnings": ModelMetricValue(
                    name="warnings",
                    value=len(self.warnings) if self.warnings else 0,
                    metric_type="counter",
                ),
            },
            throughput_rps=None,
            cpu_usage_percent=None,
            memory_usage_mb=None,
            disk_usage_gb=None,
            network_bandwidth_mbps=None,
            queue_depth=None,
            items_processed=None,
            items_failed=None,
            processing_lag_ms=None,
            compliance_score=None,
            reliability_score=None,
            availability_percent=None,
            uptime_seconds=None,
            last_error_timestamp=None,
            start_time=None,
            end_time=None,
        )

    def get_log_context(self) -> dict[str, str]:
        """Get structured logging context."""
        context = {
            "status": self.status.value,
            "severity": self.get_severity_level(),
            "version": str(self.version),
        }
        if self.correlation_id:
            context["correlation_id"] = str(self.correlation_id)
        if self.event_id:
            context["event_id"] = str(self.event_id)
        if self.processing_time_ms:
            context["processing_time"] = self.get_processing_time_human()
        if self.error_code:
            context["error_code"] = self.error_code
        return context

    def get_business_impact(self) -> ModelBusinessImpact:
        """Assess business impact of the operation result."""
        from omnibase_core.enums.enum_impact_severity import EnumImpactSeverity
        from omnibase_core.models.core.model_business_impact import ModelBusinessImpact

        severity = (
            EnumImpactSeverity.CRITICAL
            if self.is_failed()
            else (
                EnumImpactSeverity.MEDIUM
                if self.is_warning_only()
                else EnumImpactSeverity.MINIMAL
            )
        )
        return ModelBusinessImpact(
            severity=severity,
            downtime_minutes=(
                float(self.processing_time_ms) / 60000.0
                if self.processing_time_ms and self.is_failed()
                else None
            ),
            sla_violated=self.is_failed(),
            automated_recovery_successful=(
                self.is_retryable() if self.is_failed() else None
            ),
            confidence_score=(
                1.0 - self.retry_attempt * 0.1 if self.retry_attempt else 1.0
            ),
            affected_users=None,
            revenue_impact_usd=None,
            recovery_time_estimate_minutes=None,
            time_to_detection_minutes=None,
            time_to_resolution_minutes=None,
            customer_satisfaction_impact=None,
            reputation_risk=None,
            manual_interventions_required=None,
            escalation_required=None,
            operational_cost_usd=None,
            mitigation_cost_usd=None,
            opportunity_cost_usd=None,
            total_cost_usd=None,
            assessed_by=None,
        )

    def _calculate_reliability_score(self) -> float:
        """Calculate reliability score based on execution characteristics."""
        base_score = 1.0 if self.is_successful() else 0.0
        if self.retry_attempt:
            base_score *= 1.0 - self.retry_attempt * 0.1
        if self.warnings:
            base_score *= 1.0 - len(self.warnings) * 0.05
        if self.is_performance_concerning():
            base_score *= 0.8
        return max(0.0, base_score)

    def _assess_user_experience_impact(self) -> str:
        """Assess impact on user experience."""
        if self.is_failed():
            return "high_negative"
        if self.is_warning_only() or self.has_warnings():
            return "medium_negative"
        if self.is_performance_concerning():
            return "low_negative"
        if self.is_successful() and self.get_performance_category() in {
            "excellent",
            "good",
        }:
            return "positive"
        return "neutral"

    def _estimate_operational_cost(self) -> str:
        """Estimate operational cost impact."""
        if self.retry_attempt and self.retry_attempt >= 3:
            return "high"
        if self.processing_time_ms and self.processing_time_ms > 10000:
            return "medium"
        if self.has_warnings():
            return "low"
        return "minimal"

    @classmethod
    def _create_metrics(
        cls,
        response_time_ms: float | None = None,
        success_rate: float | None = None,
        error_rate: float | None = None,
        health_score: float | None = None,
    ) -> ModelMonitoringMetrics:
        """Helper method to create complete monitoring metrics."""
        return ModelMonitoringMetrics(
            response_time_ms=response_time_ms,
            throughput_rps=None,
            error_rate=error_rate,
            success_rate=success_rate,
            cpu_usage_percent=None,
            memory_usage_mb=None,
            disk_usage_gb=None,
            network_bandwidth_mbps=None,
            queue_depth=None,
            items_processed=None,
            items_failed=None,
            processing_lag_ms=None,
            compliance_score=None,
            reliability_score=None,
            availability_percent=None,
            uptime_seconds=None,
            last_error_timestamp=None,
            start_time=None,
            end_time=None,
            health_score=health_score,
            custom_metrics=None,
        )

    @classmethod
    def create_success(
        cls,
        version: ModelSemVer | str,
        message: str = "Operation completed successfully",
        processing_time_ms: int | None = None,
    ) -> ModelEventBusOutputState:
        """Create successful output state."""
        return cls(
            version=(
                parse_semver_from_string(str(version))
                if not isinstance(version, ModelSemVer)
                else version
            ),
            status=EnumOnexStatus.SUCCESS,
            message=message,
            processing_time_ms=processing_time_ms,
            metrics=cls._create_metrics(
                response_time_ms=(
                    float(processing_time_ms) if processing_time_ms else None
                ),
                success_rate=100.0,
                error_rate=0.0,
                health_score=100.0,
            ),
        )

    @classmethod
    def create_error(
        cls,
        version: ModelSemVer | str,
        message: str,
        error_code: str | None = None,
        retry_attempt: int = 0,
    ) -> ModelEventBusOutputState:
        """Create error output state."""
        return cls(
            version=(
                parse_semver_from_string(str(version))
                if not isinstance(version, ModelSemVer)
                else version
            ),
            status=EnumOnexStatus.ERROR,
            message=message,
            error_code=error_code,
            retry_attempt=retry_attempt,
            metrics=cls._create_metrics(
                success_rate=0.0, error_rate=100.0, health_score=0.0
            ),
        )

    @classmethod
    def create_warning(
        cls,
        version: ModelSemVer | str,
        message: str,
        warnings: list[str],
        processing_time_ms: int | None = None,
    ) -> ModelEventBusOutputState:
        """Create warning output state."""
        return cls(
            version=(
                parse_semver_from_string(str(version))
                if not isinstance(version, ModelSemVer)
                else version
            ),
            status=EnumOnexStatus.WARNING,
            message=message,
            warnings=warnings,
            processing_time_ms=processing_time_ms,
            metrics=cls._create_metrics(
                response_time_ms=(
                    float(processing_time_ms) if processing_time_ms else None
                ),
                success_rate=100.0,
                error_rate=0.0,
                health_score=50.0,
            ),
        )

    @classmethod
    def create_retry(
        cls,
        version: ModelSemVer | str,
        message: str,
        retry_attempt: int,
        next_retry_delay_seconds: int = 30,
    ) -> ModelEventBusOutputState:
        """Create output state for retry scenarios."""
        next_retry_at = (
            datetime.now() + timedelta(seconds=next_retry_delay_seconds)
        ).isoformat()
        return cls(
            version=(
                parse_semver_from_string(str(version))
                if not isinstance(version, ModelSemVer)
                else version
            ),
            status=EnumOnexStatus.ERROR,
            message=message,
            retry_attempt=retry_attempt,
            next_retry_at=next_retry_at,
            metrics=cls._create_metrics(
                success_rate=0.0, error_rate=100.0, health_score=0.0
            ),
        )

    @classmethod
    def create_with_tracking(
        cls,
        version: ModelSemVer | str,
        status: EnumOnexStatus | str,
        message: str,
        correlation_id: UUID,
        event_id: UUID,
        processing_time_ms: int | None = None,
    ) -> ModelEventBusOutputState:
        """Create output state with full tracking information."""
        # Normalize status to EnumOnexStatus
        if isinstance(status, EnumOnexStatus):
            status_enum = status
        else:
            try:
                status_enum = EnumOnexStatus(status)
            except ValueError as e:
                raise ModelOnexError(
                    message=f"Invalid status value: {e}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    context={"value": status},
                ) from e
        is_success = status_enum == EnumOnexStatus.SUCCESS
        return cls(
            version=(
                parse_semver_from_string(str(version))
                if not isinstance(version, ModelSemVer)
                else version
            ),
            status=status_enum,
            message=message,
            correlation_id=correlation_id,
            event_id=event_id,
            processing_time_ms=processing_time_ms,
            metrics=cls._create_metrics(
                response_time_ms=(
                    float(processing_time_ms) if processing_time_ms else None
                ),
                success_rate=100.0 if is_success else 0.0,
                error_rate=0.0 if is_success else 100.0,
                health_score=100.0 if is_success else 0.0,
            ),
        )
