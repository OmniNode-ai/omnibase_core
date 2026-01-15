"""
Enterprise Service Health Monitoring Model.

This module provides comprehensive external service health tracking with business intelligence,
connection management, and operational insights for ONEX registry services.
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from omnibase_core.constants import MAX_DESCRIPTION_LENGTH, MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_service_health_status import EnumServiceHealthStatus
from omnibase_core.enums.enum_service_type import EnumServiceType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_business_impact import ModelBusinessImpact
    from omnibase_core.models.core.model_generic_properties import (
        ModelGenericProperties,
    )
    from omnibase_core.models.core.model_monitoring_metrics import (
        ModelMonitoringMetrics,
    )


class ModelServiceHealth(BaseModel):
    """
    Enterprise-grade external service health status tracking with comprehensive monitoring,
    connection management, and operational insights.

    Features:
    - Structured service health with business logic
    - Connection analysis and security assessment
    - Performance metrics and timing analysis
    - Error categorization and recovery recommendations
    - Operational metadata and monitoring integration
    - Business intelligence and reliability scoring
    - Factory methods for common scenarios
    """

    service_name: str = Field(
        default=...,
        description="Name of the external service",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    service_type: EnumServiceType = Field(
        default=..., description="Type of the service"
    )

    status: EnumServiceHealthStatus = Field(
        default=...,
        description="Current health status of the service",
    )

    connection_string: str = Field(
        default=...,
        description="Safe connection string (credentials masked)",
        min_length=1,
        max_length=500,
    )

    error_message: str | None = Field(
        default=None,
        description="Detailed error message if service is unhealthy",
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    error_code: str | None = Field(
        default=None,
        description="Specific error code for programmatic handling",
        max_length=50,
    )

    last_check_time: str | None = Field(
        default=None,
        description="ISO timestamp of last health check",
    )

    response_time_ms: int | None = Field(
        default=None,
        description="Response time in milliseconds for health check",
        ge=0,
    )

    consecutive_failures: int | None = Field(
        default=0,
        description="Number of consecutive health check failures",
        ge=0,
    )

    uptime_seconds: int | None = Field(
        default=None,
        description="Service uptime in seconds",
        ge=0,
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Service version if available",
    )

    endpoint_url: str | None = Field(
        default=None,
        description="Primary service endpoint URL",
        max_length=500,
    )

    port: int | None = Field(
        default=None,
        description="Service port number",
        ge=1,
        le=65535,
    )

    ssl_enabled: bool | None = Field(
        default=None,
        description="Whether SSL/TLS is enabled",
    )

    authentication_type: str | None = Field(
        default=None,
        description="Type of authentication used",
        max_length=50,
    )

    configuration: "ModelGenericProperties | None" = Field(
        default=None,
        description="Service configuration summary",
    )

    metrics: "ModelMonitoringMetrics | None" = Field(
        default=None,
        description="Performance and operational metrics",
    )

    dependencies: list[str] | None = Field(
        default_factory=list,
        description="List of service dependencies",
    )

    @field_validator("service_name", mode="before")
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate service name format."""
        if not v or not v.strip():
            msg = "service_name cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        v = v.strip()

        # Check for valid service name pattern
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_\-\.]*$", v):
            msg = "service_name must start with letter and contain only alphanumeric, underscore, hyphen, and dot characters"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("connection_string", mode="before")
    @classmethod
    def validate_connection_string(cls, v: str) -> str:
        """Validate and sanitize connection string."""
        if not v or not v.strip():
            msg = "connection_string cannot be empty or whitespace"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        v = v.strip()

        # Ensure credentials are masked - handle user:pass@host pattern specially
        if re.search(r"//([^:]+):([^@]+)@", v):
            # For user:pass@host, mask both username and password
            v = re.sub(
                r"//([^:]+):([^@]+)@",
                r"//***:***@",
                v,
            )

        # Mask other credential patterns
        sensitive_patterns = [
            r"password=([^&\s]+)",
            r"pwd=([^&\s]+)",
            r"secret=([^&\s]+)",
            r"token=([^&\s]+)",
            r"key=([^&\s]+)",
        ]

        for pattern in sensitive_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                # Mask the sensitive information
                v = re.sub(
                    pattern,
                    lambda m: m.group(0).replace(m.group(1), "***"),
                    v,
                    flags=re.IGNORECASE,
                )

        return v

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v: str | None) -> str | None:
        """Validate endpoint URL format."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                msg = "endpoint_url must be a valid URL with scheme and host"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
        except (
            Exception
        ):  # fallback-ok: URL parsing exceptions converted to validation error
            msg = "endpoint_url must be a valid URL"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("last_check_time", mode="before")
    @classmethod
    def validate_last_check_time(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format (requires 'T' separator)."""
        if v is None:
            return v

        # Require strict ISO 8601 format with 'T' separator
        if not isinstance(v, str) or ("T" not in v and "t" not in v):
            msg = "last_check_time must be a valid ISO timestamp with 'T' separator"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except (AttributeError, ValueError):
            msg = "last_check_time must be a valid ISO timestamp"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

    # === Health Status Analysis ===

    def is_healthy(self) -> bool:
        """Check if the service is in a healthy state."""
        return self.status == EnumServiceHealthStatus.REACHABLE

    def is_unhealthy(self) -> bool:
        """Check if the service is in an unhealthy state."""
        return self.status in [
            EnumServiceHealthStatus.ERROR,
            EnumServiceHealthStatus.UNREACHABLE,
            EnumServiceHealthStatus.TIMEOUT,
        ]

    def is_degraded(self) -> bool:
        """Check if the service is degraded but functional."""
        return self.status == EnumServiceHealthStatus.DEGRADED

    def requires_attention(self) -> bool:
        """Check if the service requires immediate attention."""
        # Check if unhealthy
        if self.is_unhealthy():
            return True

        # Check consecutive failures
        if self.consecutive_failures is not None and self.consecutive_failures >= 3:
            return True

        # Check response time (30 second threshold for services)
        if self.response_time_ms is not None and self.response_time_ms > 30000:
            return True

        return False

    def get_severity_level(self) -> str:
        """Get human-readable severity level."""
        if self.status == EnumServiceHealthStatus.ERROR:
            return "critical"
        if self.status in {
            EnumServiceHealthStatus.UNREACHABLE,
            EnumServiceHealthStatus.TIMEOUT,
        }:
            return "high"
        if self.status == EnumServiceHealthStatus.DEGRADED:
            return "medium"
        if self.requires_attention():
            return "low"
        return "info"

    # === Connection Analysis ===

    def get_connection_type(self) -> str:
        """Determine connection type from connection string."""
        conn_lower = self.connection_string.lower()

        if (
            "ssl=true" in conn_lower
            or "tls=true" in conn_lower
            or conn_lower.startswith("https://")
        ):
            return "secure"
        if conn_lower.startswith("http://"):
            return "insecure"
        if self.ssl_enabled is True:
            return "secure"
        if self.ssl_enabled is False:
            return "insecure"
        return "unknown"

    def is_secure_connection(self) -> bool:
        """Check if the connection uses secure protocols."""
        return self.get_connection_type() == "secure"

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for the service connection."""
        recommendations = []

        if not self.is_secure_connection():
            recommendations.append("Enable SSL/TLS encryption for secure communication")

        if not self.authentication_type:
            recommendations.append("Implement authentication for enhanced security")
        elif self.authentication_type.lower() in {"basic", "plaintext"}:
            recommendations.append(
                "Consider upgrading to stronger authentication methods",
            )

        # Check for masked credentials (indicates credentials were present)
        if "***" in self.connection_string:
            recommendations.append(
                "Credentials detected and masked in connection string - consider using environment variables or secret management",
            )

        return recommendations

    # === Performance Analysis ===

    def get_performance_category(self) -> str:
        """Categorize performance based on response time."""
        if not self.response_time_ms:
            return "unknown"

        # Service thresholds are typically higher than tool thresholds
        if self.response_time_ms < 100:
            return "excellent"
        if self.response_time_ms < 500:
            return "good"
        if self.response_time_ms < 2000:
            return "acceptable"
        if self.response_time_ms < 10000:
            return "slow"
        return "very_slow"

    def is_performance_concerning(self) -> bool:
        """Check if performance metrics indicate potential issues."""
        return self.get_performance_category() in ["slow", "very_slow"]

    def get_response_time_human(self) -> str:
        """Get human-readable response time."""
        if not self.response_time_ms:
            return "unknown"

        if self.response_time_ms < 1000:
            return f"{self.response_time_ms}ms"
        seconds = self.response_time_ms / 1000
        return f"{seconds:.2f}s"

    def get_uptime_human(self) -> str:
        """Get human-readable uptime."""
        if not self.uptime_seconds:
            return "unknown"

        if self.uptime_seconds < 60:
            return f"{self.uptime_seconds}s"
        if self.uptime_seconds < 3600:
            minutes = self.uptime_seconds // 60
            return f"{minutes}m"
        if self.uptime_seconds < 86400:
            hours = self.uptime_seconds // 3600
            return f"{hours}h"
        days = self.uptime_seconds // 86400
        return f"{days}d"

    # === Reliability Analysis ===

    def calculate_reliability_score(self) -> float:
        """Calculate reliability score (0.0 to 1.0) based on health metrics."""
        base_score = 1.0 if self.is_healthy() else 0.0

        # Deduct for consecutive failures (cap at 1.0 = 100% reduction for extreme failures)
        if self.consecutive_failures:
            failure_penalty = min(self.consecutive_failures * 0.1, 1.0)
            base_score *= 1.0 - failure_penalty

        # Deduct for poor performance
        if self.is_performance_concerning():
            base_score *= 0.7  # More lenient for external services

        # Deduct for error conditions
        if self.status == EnumServiceHealthStatus.ERROR:
            base_score = 0.0
        elif self.status == EnumServiceHealthStatus.TIMEOUT:
            base_score *= 0.3
        elif self.status == EnumServiceHealthStatus.DEGRADED:
            base_score *= 0.5

        return max(0.0, min(1.0, base_score))

    def get_availability_category(self) -> str:
        """Get availability category based on consecutive failures."""
        if not self.consecutive_failures:
            return "highly_available"
        if self.consecutive_failures < 2:
            return "available"
        if self.consecutive_failures < 5:
            return "unstable"
        return "unavailable"

    # === Business Intelligence ===

    def get_business_impact(self) -> "ModelBusinessImpact":
        """Assess business impact of the service health."""
        from omnibase_core.models.core.model_business_impact import (
            EnumImpactSeverity,
            ModelBusinessImpact,
        )

        severity = (
            EnumImpactSeverity.CRITICAL
            if self.is_unhealthy()
            else (
                EnumImpactSeverity.HIGH
                if self.is_degraded()
                else (
                    EnumImpactSeverity.MEDIUM
                    if self.requires_attention()
                    else EnumImpactSeverity.MINIMAL
                )
            )
        )

        return ModelBusinessImpact(
            severity=severity,
            affected_services=[self.service_name],
            downtime_minutes=(
                float((self.consecutive_failures or 0) * 5)
                if self.is_unhealthy()
                else None
            ),
            sla_violated=self.is_unhealthy(),
            confidence_score=self.calculate_reliability_score(),
        )

    def _assess_performance_impact(self) -> str:
        """Assess impact on system performance."""
        if self.is_unhealthy():
            return "high_negative"
        if self.is_performance_concerning():
            return "medium_negative"
        if self.get_performance_category() in {"excellent", "good"}:
            return "positive"
        return "neutral"

    def _assess_security_risk(self) -> str:
        """Assess security risk level."""
        if not self.is_secure_connection():
            return "high"
        if (
            self.authentication_type
            and self.authentication_type.lower()
            in [
                "basic",
                "plaintext",
            ]
        ) or not self.authentication_type:
            return "medium"
        return "low"

    def _estimate_operational_cost(self) -> str:
        """Estimate operational cost impact."""
        if self.consecutive_failures and self.consecutive_failures >= 5:
            return "high"
        if self.response_time_ms and self.response_time_ms > 30000:
            return "medium"
        if self.is_degraded():
            return "low"
        return "minimal"

    # === Factory Methods ===

    @classmethod
    def create_healthy(
        cls,
        service_name: str,
        service_type: str,
        connection_string: str,
        response_time_ms: int = 200,
    ) -> "ModelServiceHealth":
        """Create a healthy service health status."""
        return cls(
            service_name=service_name,
            service_type=EnumServiceType(service_type),
            status=EnumServiceHealthStatus.REACHABLE,
            connection_string=connection_string,
            last_check_time=datetime.now().isoformat(),
            response_time_ms=response_time_ms,
            consecutive_failures=0,
        )

    @classmethod
    def create_error(
        cls,
        service_name: str,
        service_type: str,
        connection_string: str,
        error_message: str,
        error_code: str | None = None,
    ) -> "ModelServiceHealth":
        """Create an error service health status."""
        return cls(
            service_name=service_name,
            service_type=EnumServiceType(service_type),
            status=EnumServiceHealthStatus.ERROR,
            connection_string=connection_string,
            error_message=error_message,
            error_code=error_code,
            last_check_time=datetime.now().isoformat(),
            consecutive_failures=1,
        )

    @classmethod
    def create_timeout(
        cls,
        service_name: str,
        service_type: str,
        connection_string: str,
        timeout_ms: int,
    ) -> "ModelServiceHealth":
        """Create a timeout service health status."""
        return cls(
            service_name=service_name,
            service_type=EnumServiceType(service_type),
            status=EnumServiceHealthStatus.TIMEOUT,
            connection_string=connection_string,
            error_message=f"Service timeout after {timeout_ms}ms",
            last_check_time=datetime.now().isoformat(),
            response_time_ms=timeout_ms,
            consecutive_failures=1,
        )


from omnibase_core.models.core.model_business_impact import ModelBusinessImpact

# Fix forward references for Pydantic models
# Import the forward-referenced models to resolve string annotations
from omnibase_core.models.core.model_generic_properties import ModelGenericProperties
from omnibase_core.models.core.model_monitoring_metrics import ModelMonitoringMetrics

# Now rebuild the model to resolve the forward references
ModelServiceHealth.model_rebuild()
