"""
Health Attributes Model

Type-safe health attributes that replace Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


class ModelHealthAttributes(BaseModel):
    """
    Type-safe health attributes.

    Provides structured custom attributes for health system extensibility.
    """

    # Infrastructure attributes
    cluster_name: Optional[str] = Field(None, description="Kubernetes cluster name")
    region: Optional[str] = Field(None, description="Cloud region")
    availability_zone: Optional[str] = Field(
        None, description="Cloud availability zone"
    )
    instance_type: Optional[str] = Field(None, description="Instance/VM type")

    # Monitoring attributes
    monitoring_backend: Optional[str] = Field(
        None, description="Monitoring system (prometheus, datadog, etc.)"
    )
    metrics_endpoint: Optional[str] = Field(None, description="Metrics endpoint URL")
    log_aggregator: Optional[str] = Field(None, description="Log aggregation system")

    # SLA/SLO attributes
    sla_tier: Optional[str] = Field(
        None, description="SLA tier (basic, standard, premium)"
    )
    uptime_target: Optional[float] = Field(
        None, description="Target uptime percentage", ge=0, le=100
    )
    response_time_target_ms: Optional[int] = Field(
        None, description="Target response time in milliseconds"
    )

    # Organization attributes
    team_name: Optional[str] = Field(None, description="Responsible team")
    cost_center: Optional[str] = Field(None, description="Cost center code")
    project_code: Optional[str] = Field(None, description="Project code")

    # Feature flags
    feature_flags: List[str] = Field(
        default_factory=list, description="Enabled feature flags"
    )
    experimental_features: List[str] = Field(
        default_factory=list, description="Experimental features"
    )

    # Capacity planning
    max_concurrent_users: Optional[int] = Field(
        None, description="Maximum concurrent users"
    )
    max_requests_per_second: Optional[int] = Field(None, description="Maximum RPS")
    storage_quota_gb: Optional[float] = Field(None, description="Storage quota in GB")

    # Custom fields for future extensibility
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Additional custom attributes"
    )
