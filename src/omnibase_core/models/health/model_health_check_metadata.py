"""
Health Check Metadata Model

Type-safe health check metadata that replaces Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelHealthCheckMetadata(BaseModel):
    """
    Type-safe health check metadata.

    Provides structured metadata for health check configuration.
    """

    # Check identification
    check_name: str | None = Field(default=None, description="Health check name")
    check_version: ModelSemVer | None = Field(
        default=None, description="Health check version"
    )
    check_description: str | None = Field(
        default=None,
        description="Health check description",
    )

    # Check categorization
    check_type: str | None = Field(
        default=None,
        description="Type of check (http, tcp, custom)",
    )
    check_category: str | None = Field(
        default=None,
        description="Check category (basic, detailed, diagnostic)",
    )
    check_tags: list[str] = Field(
        default_factory=list,
        description="Tags for check organization",
    )

    # Business context
    business_impact: str | None = Field(
        default=None,
        description="Business impact if check fails",
    )
    sla_critical: bool = Field(
        default=False, description="Whether this check affects SLA"
    )

    # Technical details
    expected_response_time_ms: int | None = Field(
        default=None,
        description="Expected response time",
    )
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    retry_delay_ms: int | None = Field(
        default=None, description="Delay between retries"
    )

    # Dependencies
    depends_on_checks: list[str] = Field(
        default_factory=list,
        description="Other checks this depends on",
    )
    dependent_services: list[str] = Field(
        default_factory=list,
        description="Services that depend on this check",
    )

    # Alert configuration
    alert_on_failure: bool = Field(
        default=True, description="Whether to alert on failure"
    )
    alert_channels: list[str] = Field(
        default_factory=list,
        description="Alert channels (email, slack, pager)",
    )
    alert_cooldown_minutes: int | None = Field(
        default=None,
        description="Cooldown between alerts",
    )

    # Custom fields for extensibility
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Additional custom metadata",
    )
