"""
Audit Requirements Model

Type-safe audit requirements configuration.
"""

from pydantic import BaseModel, Field


class ModelAuditRequirements(BaseModel):
    """
    Type-safe audit requirements configuration.

    Defines audit logging and compliance requirements.
    """

    enabled: bool = Field(default=True, description="Whether audit logging is enabled")

    detail_level: str = Field(
        default="standard",
        description="Level of audit detail required",
        pattern="^(minimal|standard|detailed|comprehensive)$",
    )

    retention_days: int = Field(
        default=365,
        description="Days to retain audit logs",
        ge=1,
        le=7300,  # Max 20 years
    )

    export_required: bool = Field(
        default=False,
        description="Whether audit logs must be exported to external system",
    )

    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks this relates to (e.g., 'SOC2', 'HIPAA', 'GDPR')",
    )

    export_destinations: list[str] = Field(
        default_factory=list,
        description="Systems to export audit logs to",
    )

    export_format: str = Field(
        default="json",
        description="Format for exported audit logs",
        pattern="^(json|csv|syslog|cef)$",
    )

    redaction_rules: list[str] = Field(
        default_factory=list,
        description="Fields to redact from audit logs",
    )

    sampling_rate: float = Field(
        default=1.0,
        description="Sampling rate for audit logs (1.0 = 100%)",
        ge=0.0,
        le=1.0,
    )

    alert_on_anomaly: bool = Field(
        default=False,
        description="Whether to alert on anomalous audit patterns",
    )

    archive_after_days: int | None = Field(
        default=None,
        description="Days after which to archive logs",
        ge=30,
    )
