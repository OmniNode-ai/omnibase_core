"""
ModelCertificateValidationLevel: Certificate validation configuration.

This model defines certificate validation requirements and settings.
"""

from pydantic import BaseModel, Field, field_validator


class ModelCertificateValidationLevel(BaseModel):
    """Certificate validation configuration and requirements."""

    level: str = Field(
        default="standard",
        description="Validation level: none, basic, standard, strict, paranoid",
        pattern=r"^(none|basic|standard|strict|paranoid)$",
    )

    check_expiration: bool = Field(
        default=True,
        description="Check certificate expiration dates",
    )

    check_revocation: bool = Field(
        default=True,
        description="Check certificate revocation status via CRL/OCSP",
    )

    check_chain: bool = Field(
        default=True, description="Validate full certificate chain"
    )

    check_hostname: bool = Field(
        default=True,
        description="Verify certificate hostname matches",
    )

    require_ct_logs: bool = Field(
        default=False,
        description="Require Certificate Transparency logs",
    )

    trusted_cas: list[str] = Field(
        default_factory=list,
        description="List of trusted CA fingerprints",
    )

    max_chain_depth: int = Field(
        default=10,
        description="Maximum certificate chain depth",
        ge=1,
        le=20,
    )

    allow_self_signed: bool = Field(
        default=False, description="Allow self-signed certificates"
    )

    minimum_key_size: int = Field(
        default=2048,
        description="Minimum RSA key size in bits",
        ge=1024,
    )

    allowed_signature_algorithms: list[str] = Field(
        default_factory=lambda: ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
        description="Allowed signature algorithms",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate certificate validation level."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        valid_levels = {"none", "basic", "standard", "strict", "paranoid"}
        if v not in valid_levels:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid validation level: {v}. Must be one of: {valid_levels}",
            )
        return v

    def apply_level_defaults(self) -> None:
        """Apply default settings based on validation level."""
        if self.level == "none":
            self.check_expiration = False
            self.check_revocation = False
            self.check_chain = False
            self.check_hostname = False
            self.allow_self_signed = True
        elif self.level == "basic":
            self.check_expiration = True
            self.check_revocation = False
            self.check_chain = False
            self.check_hostname = False
        elif self.level == "standard":
            self.check_expiration = True
            self.check_revocation = True
            self.check_chain = True
            self.check_hostname = True
        elif self.level == "strict":
            self.check_expiration = True
            self.check_revocation = True
            self.check_chain = True
            self.check_hostname = True
            self.allow_self_signed = False
        elif self.level == "paranoid":
            self.check_expiration = True
            self.check_revocation = True
            self.check_chain = True
            self.check_hostname = True
            self.require_ct_logs = True
            self.allow_self_signed = False
            self.minimum_key_size = 4096
