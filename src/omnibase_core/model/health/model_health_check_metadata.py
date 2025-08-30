"""
Health Check Metadata Model

Type-safe health check metadata that replaces Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


class ModelHealthCheckMetadata(BaseModel):
    """
    Type-safe health check metadata.

    Provides structured metadata for health check configuration.
    """

    # Check identification
    check_name: Optional[str] = Field(None, description="Health check name")
    check_version: Optional[str] = Field(None, description="Health check version")
    check_description: Optional[str] = Field(
        None, description="Health check description"
    )

    # Check categorization
    check_type: Optional[str] = Field(
        None, description="Type of check (http, tcp, custom)"
    )
    check_category: Optional[str] = Field(
        None, description="Check category (basic, detailed, diagnostic)"
    )
    check_tags: List[str] = Field(
        default_factory=list, description="Tags for check organization"
    )

    # Business context
    business_impact: Optional[str] = Field(
        None, description="Business impact if check fails"
    )
    sla_critical: bool = Field(False, description="Whether this check affects SLA")

    # Technical details
    expected_response_time_ms: Optional[int] = Field(
        None, description="Expected response time"
    )
    max_retries: Optional[int] = Field(None, description="Maximum retry attempts")
    retry_delay_ms: Optional[int] = Field(None, description="Delay between retries")

    # Dependencies
    depends_on_checks: List[str] = Field(
        default_factory=list, description="Other checks this depends on"
    )
    dependent_services: List[str] = Field(
        default_factory=list, description="Services that depend on this check"
    )

    # Alert configuration
    alert_on_failure: bool = Field(True, description="Whether to alert on failure")
    alert_channels: List[str] = Field(
        default_factory=list, description="Alert channels (email, slack, pager)"
    )
    alert_cooldown_minutes: Optional[int] = Field(
        None, description="Cooldown between alerts"
    )

    # Custom fields for extensibility
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Additional custom metadata"
    )
