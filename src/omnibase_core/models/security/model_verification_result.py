from pydantic import BaseModel, Field


class ModelVerificationResult(BaseModel):
    """Verification result model."""

    is_valid: bool = Field(default=False, description="Whether verification passed")
    errors: list[str] = Field(default_factory=list, description="Verification errors")
    warnings: list[str] = Field(
        default_factory=list,
        description="Verification warnings",
    )
    trust_level: str = Field(
        default="untrusted",
        description="Trust level of verification",
    )
