"""Service Health Validation Result Model.

Result model for service health validation in the service registry.

This model provides detailed information about service health validation
including validation status, health metrics, and diagnostic information.
Used by the validate_service_health() method in ServiceRegistry.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumHealthStatus
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceHealthValidationResult(BaseModel):
    """
    Result of service health validation.

    Provides comprehensive health validation results for a registered service,
    including health status, metrics, and diagnostic information.

    Attributes:
        registration_id: ID of the service registration validated
        is_healthy: Overall health status
        health_status: Detailed health status
        validation_time: When the validation was performed
        response_time_ms: Time taken to validate in milliseconds
        instance_count: Number of active instances
        last_access_time: Last time the service was accessed
        error_message: Error message if validation failed
        warnings: List of warning messages
        diagnostics: Additional diagnostic information

    Example:
        ```python
        from uuid import UUID
        from omnibase_core.enums import EnumHealthStatus
        result = ModelServiceHealthValidationResult(
            registration_id=UUID("12345678-..."),
            is_healthy=True,
            health_status=EnumHealthStatus.HEALTHY,
            response_time_ms=5.2,
            instance_count=1,
        )
        ```
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    registration_id: UUID = Field(
        description="ID of the service registration validated"
    )
    is_healthy: bool = Field(
        default=True,
        description="Overall health status",
    )
    health_status: EnumHealthStatus = Field(
        default=EnumHealthStatus.HEALTHY,
        description="Detailed health status",
    )
    validation_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the validation was performed",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Time taken to validate in milliseconds",
    )
    instance_count: int = Field(
        default=0,
        ge=0,
        description="Number of active instances",
    )
    last_access_time: datetime | None = Field(
        default=None,
        description="Last time the service was accessed",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if validation failed",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages",
    )
    diagnostics: SerializedDict = Field(
        default_factory=dict,
        description="Additional diagnostic information",
    )

    @property
    def has_warnings(self) -> bool:
        """Check if validation produced warnings."""
        return len(self.warnings) > 0

    @property
    def has_error(self) -> bool:
        """Check if validation produced an error."""
        return self.error_message is not None

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def set_error(self, error: str) -> None:
        """Set the error message and mark as unhealthy."""
        self.error_message = error
        self.is_healthy = False
        self.health_status = EnumHealthStatus.UNHEALTHY

    def add_diagnostic(self, key: str, value: str | int | float | bool | None) -> None:
        """Add diagnostic information."""
        self.diagnostics[key] = value

    @classmethod
    def healthy(
        cls,
        registration_id: UUID,
        instance_count: int = 1,
        response_time_ms: float | None = None,
    ) -> "ModelServiceHealthValidationResult":
        """Create a healthy validation result."""
        return cls(
            registration_id=registration_id,
            is_healthy=True,
            health_status=EnumHealthStatus.HEALTHY,
            instance_count=instance_count,
            response_time_ms=response_time_ms,
        )

    @classmethod
    def unhealthy(
        cls,
        registration_id: UUID,
        error_message: str,
        diagnostics: SerializedDict | None = None,
    ) -> "ModelServiceHealthValidationResult":
        """Create an unhealthy validation result."""
        return cls(
            registration_id=registration_id,
            is_healthy=False,
            health_status=EnumHealthStatus.UNHEALTHY,
            error_message=error_message,
            diagnostics=diagnostics or {},
        )

    @classmethod
    def degraded(
        cls,
        registration_id: UUID,
        warnings: list[str],
        instance_count: int = 1,
    ) -> "ModelServiceHealthValidationResult":
        """Create a degraded validation result."""
        return cls(
            registration_id=registration_id,
            is_healthy=True,
            health_status=EnumHealthStatus.DEGRADED,
            instance_count=instance_count,
            warnings=warnings,
        )


__all__ = ["ModelServiceHealthValidationResult"]
