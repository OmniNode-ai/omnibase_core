"""
ModelCredentialAuditReport: Audit report for credential usage.

This model represents the result of auditing credential usage in data structures.
"""

from pydantic import BaseModel, Field


class ModelCredentialAuditReport(BaseModel):
    """Audit report for credential usage in data structures."""

    total_fields: int = Field(
        default=0, description="Total number of fields audited", ge=0
    )

    sensitive_fields: int = Field(
        default=0,
        description="Number of sensitive fields found",
        ge=0,
    )

    masked_fields: list[str] = Field(
        default_factory=list,
        description="List of field paths that were masked",
    )

    credential_patterns: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Detected credential patterns by field path",
    )

    security_issues: list[str] = Field(
        default_factory=list,
        description="List of identified security issues",
    )
