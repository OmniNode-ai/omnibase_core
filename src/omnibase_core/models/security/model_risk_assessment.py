"""
Risk Assessment Model

Type-safe risk assessment information.
"""

from pydantic import BaseModel, Field


class ModelRiskAssessment(BaseModel):
    """
    Type-safe risk assessment information.

    Provides structured risk assessment data for permissions.
    """

    level: str = Field(
        default="medium",
        description="Risk level",
        pattern="^(low|medium|high|critical)$",
    )

    score: int = Field(default=2, description="Numeric risk score", ge=1, le=5)

    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks this relates to",
    )

    data_classification_required: str | None = Field(
        default=None,
        description="Required data classification level",
        pattern="^(public|internal|confidential|restricted|top_secret)$",
    )

    emergency_override_allowed: bool = Field(
        default=False,
        description="Whether emergency override is allowed",
    )

    threat_categories: list[str] = Field(
        default_factory=list,
        description="Categories of threats this permission could enable",
    )

    mitigation_controls: list[str] = Field(
        default_factory=list,
        description="Controls in place to mitigate risks",
    )

    residual_risk_acceptable: bool = Field(
        default=True,
        description="Whether residual risk after controls is acceptable",
    )

    risk_owner: str | None = Field(
        default=None,
        description="Person/role responsible for this risk",
    )

    review_frequency_days: int = Field(
        default=90,
        description="How often risk assessment should be reviewed",
        ge=1,
        le=365,
    )

    last_review_date: str | None = Field(
        default=None,
        description="Date of last risk review (ISO format)",
    )

    next_review_date: str | None = Field(
        default=None,
        description="Date of next scheduled review (ISO format)",
    )
