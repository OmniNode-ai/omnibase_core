"""
Risk Assessment Model

Type-safe risk assessment information.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelRiskAssessment(BaseModel):
    """
    Type-safe risk assessment information.

    Provides structured risk assessment data for permissions.
    """

    level: str = Field(
        "medium", description="Risk level", pattern="^(low|medium|high|critical)$"
    )

    score: int = Field(2, description="Numeric risk score", ge=1, le=5)

    compliance_tags: List[str] = Field(
        default_factory=list, description="Compliance frameworks this relates to"
    )

    data_classification_required: Optional[str] = Field(
        None,
        description="Required data classification level",
        pattern="^(public|internal|confidential|restricted|top_secret)$",
    )

    emergency_override_allowed: bool = Field(
        False, description="Whether emergency override is allowed"
    )

    threat_categories: List[str] = Field(
        default_factory=list,
        description="Categories of threats this permission could enable",
    )

    mitigation_controls: List[str] = Field(
        default_factory=list, description="Controls in place to mitigate risks"
    )

    residual_risk_acceptable: bool = Field(
        True, description="Whether residual risk after controls is acceptable"
    )

    risk_owner: Optional[str] = Field(
        None, description="Person/role responsible for this risk"
    )

    review_frequency_days: int = Field(
        90, description="How often risk assessment should be reviewed", ge=1, le=365
    )

    last_review_date: Optional[str] = Field(
        None, description="Date of last risk review (ISO format)"
    )

    next_review_date: Optional[str] = Field(
        None, description="Date of next scheduled review (ISO format)"
    )
