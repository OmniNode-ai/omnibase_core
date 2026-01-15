"""
Connection Security Model.

SSL/TLS and security configuration for network connections.
Part of the ModelConnectionInfo restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict
from omnibase_core.types.typed_dict_ssl_context_options import (
    TypedDictSSLContextOptions,
)


class ModelConnectionSecurity(BaseModel):
    """
    Connection security configuration.

    Contains SSL/TLS settings and security options
    without endpoint or authentication concerns.
    """

    # SSL/TLS configuration
    use_ssl: bool = Field(default=False, description="Whether to use SSL/TLS")
    ssl_verify: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )

    # Certificate paths
    ssl_cert_path: Path | None = Field(default=None, description="SSL certificate path")
    ssl_key_path: Path | None = Field(default=None, description="SSL key path")
    ssl_ca_path: Path | None = Field(default=None, description="SSL CA bundle path")

    @model_validator(mode="after")
    def validate_ssl_configuration(self) -> ModelConnectionSecurity:
        """Validate SSL certificate paths exist when SSL is enabled."""
        if self.use_ssl:
            if self.ssl_cert_path and not self.ssl_cert_path.exists():
                raise ModelOnexError(
                    message=f"SSL certificate path does not exist: {self.ssl_cert_path}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if self.ssl_key_path and not self.ssl_key_path.exists():
                raise ModelOnexError(
                    message=f"SSL key path does not exist: {self.ssl_key_path}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if self.ssl_ca_path and not self.ssl_ca_path.exists():
                raise ModelOnexError(
                    message=f"SSL CA bundle path does not exist: {self.ssl_ca_path}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
        return self

    def is_secure_connection(self) -> bool:
        """Check if connection uses secure protocols."""
        return self.use_ssl

    def has_client_certificates(self) -> bool:
        """Check if client certificates are configured."""
        return bool(self.ssl_cert_path and self.ssl_key_path)

    def has_ca_bundle(self) -> bool:
        """Check if CA bundle is configured."""
        return bool(self.ssl_ca_path)

    def get_ssl_context_options(self) -> TypedDictSSLContextOptions:
        """Get SSL context options for connection libraries.
        Implements Core protocols:
        - Configurable: Configuration management capabilities
        - Validatable: Validation and verification
        - Serializable: Data serialization/deserialization
        """
        return {
            "verify": self.ssl_verify,
            "cert": self.ssl_cert_path,
            "key": self.ssl_key_path,
            "ca_certs": self.ssl_ca_path,
        }

    def enable_ssl(
        self,
        verify: bool = True,
        cert_path: Path | None = None,
        key_path: Path | None = None,
        ca_path: Path | None = None,
    ) -> None:
        """Enable SSL with optional certificate configuration."""
        self.use_ssl = True
        self.ssl_verify = verify
        if cert_path:
            self.ssl_cert_path = cert_path
        if key_path:
            self.ssl_key_path = key_path
        if ca_path:
            self.ssl_ca_path = ca_path

    def disable_ssl(self) -> None:
        """Disable SSL and clear certificate paths."""
        self.use_ssl = False
        self.ssl_verify = True
        self.ssl_cert_path = None
        self.ssl_key_path = None
        self.ssl_ca_path = None

    @classmethod
    def create_secure(
        cls,
        verify: bool = True,
        cert_path: Path | None = None,
        key_path: Path | None = None,
        ca_path: Path | None = None,
    ) -> ModelConnectionSecurity:
        """Create secure SSL configuration."""
        return cls(
            use_ssl=True,
            ssl_verify=verify,
            ssl_cert_path=cert_path,
            ssl_key_path=key_path,
            ssl_ca_path=ca_path,
        )

    @classmethod
    def create_insecure(cls) -> ModelConnectionSecurity:
        """Create insecure (no SSL) configuration."""
        return cls(
            use_ssl=False,
            ssl_cert_path=None,
            ssl_key_path=None,
            ssl_ca_path=None,
        )

    @classmethod
    def create_self_signed(cls) -> ModelConnectionSecurity:
        """Create configuration for self-signed certificates."""
        return cls(
            use_ssl=True,
            ssl_verify=False,
            ssl_cert_path=None,
            ssl_key_path=None,
            ssl_ca_path=None,
        )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            # These are raised by setattr with Pydantic validate_assignment=True
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelConnectionSecurity"]
