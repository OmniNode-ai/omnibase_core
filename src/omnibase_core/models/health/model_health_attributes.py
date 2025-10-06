from typing import Any, Dict

from pydantic import Field

"""
Health Attributes Model

Type-safe health attributes that replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields


class ModelHealthAttributes(BaseModel):
    """
    Type-safe health attributes.

    Provides structured custom attributes for health system extensibility.
    """

    # Infrastructure attributes
    cluster_name: str | None = Field(None, description="Kubernetes cluster name")
    region: str | None = Field(None, description="Cloud region")
    availability_zone: str | None = Field(
        None,
        description="Cloud availability zone",
    )
    instance_type: str | None = Field(None, description="Instance/VM type")

    # Monitoring attributes
    monitoring_backend: str | None = Field(
        None,
        description="Monitoring system (prometheus, datadog, etc.)",
    )
    metrics_endpoint: str | None = Field(None, description="Metrics endpoint URL")
    log_aggregator: str | None = Field(None, description="Log aggregation system")

    # SLA/SLO attributes
    sla_tier: str | None = Field(
        None,
        description="SLA tier (basic, standard, premium)",
    )
    uptime_target: float | None = Field(
        None,
        description="Target uptime percentage",
        ge=0,
        le=100,
    )
    response_time_target_ms: int | None = Field(
        None,
        description="Target response time in milliseconds",
    )

    # Organization attributes
    team_name: str | None = Field(None, description="Responsible team")
    cost_center: str | None = Field(None, description="Cost center code")
    project_code: str | None = Field(None, description="Project code")

    # Feature flags
    feature_flags: list[str] = Field(
        default_factory=list,
        description="Enabled feature flags",
    )
    experimental_features: list[str] = Field(
        default_factory=list,
        description="Experimental features",
    )

    # Capacity planning
    max_concurrent_users: int | None = Field(
        None,
        description="Maximum concurrent users",
    )
    max_requests_per_second: int | None = Field(None, description="Maximum RPS")
    storage_quota_gb: float | None = Field(None, description="Storage quota in GB")

    # Custom fields for future extensibility
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Additional custom attributes",
    )
