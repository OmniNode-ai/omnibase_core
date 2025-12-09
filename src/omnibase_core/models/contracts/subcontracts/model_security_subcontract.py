"""
Security Subcontract Model.



Dedicated subcontract model for security functionality providing:
- Sensitive data redaction and pattern detection
- Field encryption configuration
- Security audit logging
- Access control settings
- Input validation and output sanitization
- Field length constraints for security

This model is composed into node contracts that require security functionality,
providing clean separation between node logic and security behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSecuritySubcontract(BaseModel):
    """
    Security subcontract model for security functionality.

    Comprehensive security subcontract providing data redaction,
    encryption, audit logging, access control, and input/output validation.
    Designed for composition into node contracts requiring security functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Data redaction configuration
    enable_redaction: bool = Field(
        default=True,
        description="Enable sensitive data redaction in logs and outputs",
    )

    sensitive_field_patterns: list[str] = Field(
        default_factory=lambda: ["password", "secret", "token", "key", "credential"],
        description="Patterns for detecting sensitive fields (case-insensitive)",
    )

    redaction_placeholder: str = Field(
        default="[REDACTED]",
        description="Placeholder text for redacted values",
        min_length=1,
    )

    # Encryption configuration
    enable_encryption: bool = Field(
        default=False,
        description="Enable field-level encryption for sensitive data",
    )

    encryption_algorithm: str = Field(
        default="aes-256-gcm",
        description="Encryption algorithm to use",
    )

    enable_encryption_at_rest: bool = Field(
        default=False,
        description="Enable encryption for data at rest",
    )

    # Audit logging
    enable_audit_logging: bool = Field(
        default=True,
        description="Enable security audit logging for sensitive operations",
    )

    audit_sensitive_operations: bool = Field(
        default=True,
        description="Audit operations on sensitive data",
    )

    audit_access_attempts: bool = Field(
        default=True,
        description="Audit all access attempts (success and failure)",
    )

    # Access control
    enable_access_control: bool = Field(
        default=True,
        description="Enable access control checks",
    )

    require_authentication: bool = Field(
        default=True,
        description="Require authentication for operations",
    )

    require_authorization: bool = Field(
        default=True,
        description="Require authorization for sensitive operations",
    )

    # Input validation
    enable_input_validation: bool = Field(
        default=True,
        description="Enable input validation for security",
    )

    max_field_length: int = Field(
        default=10000,
        description="Maximum allowed field length for input validation",
        ge=100,
        le=1000000,
    )

    enable_sql_injection_protection: bool = Field(
        default=True,
        description="Enable SQL injection protection",
    )

    enable_xss_protection: bool = Field(
        default=True,
        description="Enable XSS (Cross-Site Scripting) protection",
    )

    # Output sanitization
    enable_output_sanitization: bool = Field(
        default=True,
        description="Enable output sanitization before returning data",
    )

    sanitize_html: bool = Field(
        default=True,
        description="Sanitize HTML content in outputs",
    )

    sanitize_scripts: bool = Field(
        default=True,
        description="Remove script tags from outputs",
    )

    # Security policies
    enforce_https: bool = Field(
        default=True,
        description="Enforce HTTPS for all connections",
    )

    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting for security",
    )

    enable_csrf_protection: bool = Field(
        default=True,
        description="Enable CSRF (Cross-Site Request Forgery) protection",
    )

    @model_validator(mode="after")
    def validate_patterns(self) -> "ModelSecuritySubcontract":
        """Validate and normalize sensitive field patterns."""
        # Allow empty patterns - will be validated in model_validator context
        if not self.sensitive_field_patterns:
            return self

        # Normalize patterns to lowercase for case-insensitive matching
        normalized = [pattern.lower() for pattern in self.sensitive_field_patterns]

        # Check for duplicates after normalization
        if len(normalized) != len(set(normalized)):
            msg = "sensitive_field_patterns contains duplicate patterns"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "original_patterns": ModelSchemaValue.from_value(
                            str(self.sensitive_field_patterns),
                        ),
                        "normalized_patterns": ModelSchemaValue.from_value(
                            str(normalized),
                        ),
                    },
                ),
            )

        # Update the field with normalized patterns using object.__setattr__
        # to bypass validate_assignment and avoid infinite recursion
        object.__setattr__(self, "sensitive_field_patterns", normalized)
        return self

    @model_validator(mode="after")
    def validate_encryption_algorithm(self) -> "ModelSecuritySubcontract":
        """Validate encryption algorithm is one of the supported types."""
        allowed_algorithms = ["aes-256-gcm", "aes-128-gcm", "chacha20-poly1305"]
        if self.encryption_algorithm not in allowed_algorithms:
            msg = f"encryption_algorithm must be one of {allowed_algorithms}, got '{self.encryption_algorithm}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_algorithms": ModelSchemaValue.from_value(
                            str(allowed_algorithms),
                        ),
                        "received_algorithm": ModelSchemaValue.from_value(
                            self.encryption_algorithm,
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_encryption_configuration(self) -> "ModelSecuritySubcontract":
        """Validate that encryption configuration is consistent."""
        if self.enable_encryption_at_rest and not self.enable_encryption:
            msg = (
                "enable_encryption must be True when enable_encryption_at_rest is True"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "enable_encryption": ModelSchemaValue.from_value(
                            str(self.enable_encryption),
                        ),
                        "enable_encryption_at_rest": ModelSchemaValue.from_value(
                            str(self.enable_encryption_at_rest),
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_redaction_configuration(self) -> "ModelSecuritySubcontract":
        """Validate that redaction configuration is consistent."""
        if self.enable_redaction and not self.sensitive_field_patterns:
            msg = "sensitive_field_patterns must be provided when enable_redaction is True"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "enable_redaction": ModelSchemaValue.from_value(
                            str(self.enable_redaction),
                        ),
                        "patterns_provided": ModelSchemaValue.from_value(
                            str(bool(self.sensitive_field_patterns)),
                        ),
                    },
                ),
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
