from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelVerificationDetails(BaseModel):
    """Detailed verification information for signature verification."""

    certificate_validation: dict[str, str | None] = Field(
        default_factory=dict,
        description="Certificate validation details",
    )
    signature_algorithm: str = Field(default="", description="Signature algorithm used")
    certificate_id: UUID = Field(
        default_factory=uuid4, description="Certificate identifier"
    )
    security_level: str = Field(
        default="basic",
        description="Security level assessment",
    )
    compliance_level: str = Field(
        default="basic",
        description="Compliance level assessment",
    )
    trust_level: str = Field(default="untrusted", description="Trust level assessment")
    verification_time_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Time breakdown for verification steps",
    )
    performance_optimizations: dict[str, bool] = Field(
        default_factory=dict,
        description="Performance optimization flags",
    )
