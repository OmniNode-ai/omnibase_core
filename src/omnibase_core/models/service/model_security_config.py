from pydantic import Field, model_validator

from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Security configuration model for service deployment.
"""

from pathlib import Path

from pydantic import BaseModel, Field, SecretStr, model_validator


class ModelSecurityConfig(BaseModel):
    """Security configuration for service deployment."""

    enable_tls: bool = Field(default=False, description="Enable TLS/SSL")
    cert_file: Path | None = Field(
        default=None, description="TLS certificate file path"
    )
    key_file: Path | None = Field(default=None, description="TLS private key file path")
    ca_file: Path | None = Field(default=None, description="TLS CA file path")
    api_key: SecretStr | None = Field(
        default=None, description="API key for authentication"
    )

    @model_validator(mode="after")
    def validate_tls_config(self) -> "ModelSecurityConfig":
        """Validate TLS configuration consistency."""
        if self.enable_tls and (not self.cert_file or not self.key_file):
            msg = "TLS enabled but cert_file or key_file not provided"
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return self
