"""Compliance Metadata Model.

Compliance and regulatory metadata for secure event envelopes.
"""

from pydantic import BaseModel, Field


class ModelComplianceMetadata(BaseModel):
    """Compliance and regulatory metadata."""

    frameworks: list[str] = Field(
        default_factory=list,
        description="Applicable frameworks",
    )
    classification: str = Field(
        default="internal",
        description="Data classification level",
    )
    retention_period_days: int | None = Field(
        default=None,
        description="Retention period in days",
    )
    jurisdiction: str | None = Field(default=None, description="Legal jurisdiction")
    consent_required: bool = Field(
        default=False,
        description="Explicit consent required",
    )
    audit_level: str = Field(
        default="standard",
        description="Required audit detail level",
    )

    # Specific compliance flags
    contains_pii: bool = Field(
        default=False,
        description="Contains personally identifiable information",
    )
    contains_phi: bool = Field(
        default=False,
        description="Contains protected health information",
    )
    contains_financial: bool = Field(
        default=False,
        description="Contains financial data",
    )
    export_controlled: bool = Field(
        default=False,
        description="Subject to export controls",
    )
