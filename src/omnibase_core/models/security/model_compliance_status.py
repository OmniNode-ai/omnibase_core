from pydantic import BaseModel, Field


class ModelComplianceStatus(BaseModel):
    """Compliance status model."""

    frameworks: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks",
    )
    classification: str | None = Field(default=None, description="Data classification")
    audit_trail_complete: bool = Field(
        default=False,
        description="Whether audit trail is complete",
    )
