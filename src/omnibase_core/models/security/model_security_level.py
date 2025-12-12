from pydantic import Field

"\nSecurity Level Model\n\nExtensible security configuration model that replaces hardcoded\nsecurity enums with flexible, nuanced security settings.\n"
from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_custom_security_settings import (
    ModelCustomSecuritySettings,
    SecuritySettingValue,
)
from omnibase_core.models.security.model_network_restrictions import (
    ModelNetworkRestrictions,
)
from omnibase_core.models.security.model_password_policy import ModelPasswordPolicy
from omnibase_core.models.security.model_session_policy import ModelSessionPolicy


class ModelSecurityLevel(BaseModel):
    """
    Extensible security level configuration model.

    This model provides nuanced security configuration beyond
    simple high/medium/low classifications.
    """

    level_name: str = Field(
        default="standard",
        description="Security level name",
        pattern="^[a-z][a-z0-9_-]*$",
    )
    display_name: str = Field(
        default="Standard Security", description="Human-readable security level name"
    )
    security_score: float = Field(
        default=0.5,
        description="Numeric security score (0.0 = none, 1.0 = maximum)",
        ge=0.0,
        le=1.0,
    )
    encryption_required: bool = Field(
        default=True, description="Whether encryption is required"
    )
    authentication_required: bool = Field(
        default=True, description="Whether authentication is required"
    )
    authorization_required: bool = Field(
        default=True, description="Whether authorization is required"
    )
    audit_logging_required: bool = Field(
        default=True, description="Whether audit logging is required"
    )
    input_validation_strict: bool = Field(
        default=True, description="Whether strict input validation is required"
    )
    rate_limiting_enabled: bool = Field(
        default=True, description="Whether rate limiting is enabled"
    )
    allowed_protocols: list[str] = Field(
        default_factory=lambda: ["https", "tls"],
        description="List of allowed communication protocols",
    )
    blocked_protocols: list[str] = Field(
        default_factory=lambda: ["http", "ftp", "telnet"],
        description="List of blocked communication protocols",
    )
    minimum_tls_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=2, patch=0),
        description="Minimum TLS version required",
    )
    password_policy: ModelPasswordPolicy = Field(
        default_factory=ModelPasswordPolicy, description="Password policy requirements"
    )
    session_policy: ModelSessionPolicy = Field(
        default_factory=ModelSessionPolicy, description="Session management policy"
    )
    network_restrictions: ModelNetworkRestrictions = Field(
        default_factory=ModelNetworkRestrictions,
        description="Network access restrictions",
    )
    compliance_requirements: list[str] = Field(
        default_factory=list, description="Compliance standards that must be met"
    )
    security_headers: dict[str, str] = Field(
        default_factory=lambda: {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        },
        description="Required security headers",
    )
    custom_security_settings: ModelCustomSecuritySettings = Field(
        default_factory=ModelCustomSecuritySettings,
        description="Custom security settings",
    )

    def is_low_security(self) -> bool:
        """Check if this is a low security level."""
        return self.security_score < 0.3

    def is_medium_security(self) -> bool:
        """Check if this is a medium security level."""
        return 0.3 <= self.security_score < 0.7

    def is_high_security(self) -> bool:
        """Check if this is a high security level."""
        return self.security_score >= 0.7

    def requires_encryption(self) -> bool:
        """Check if encryption is required."""
        return self.encryption_required

    def requires_authentication(self) -> bool:
        """Check if authentication is required."""
        return self.authentication_required

    def requires_authorization(self) -> bool:
        """Check if authorization is required."""
        return self.authorization_required

    def requires_audit_logging(self) -> bool:
        """Check if audit logging is required."""
        return self.audit_logging_required

    def is_protocol_allowed(self, protocol: str) -> bool:
        """Check if a protocol is allowed."""
        protocol_lower = protocol.lower()
        return (
            protocol_lower in self.allowed_protocols
            and protocol_lower not in self.blocked_protocols
        )

    def get_session_timeout_minutes(self) -> int:
        """Get session timeout in minutes."""
        return self.session_policy.idle_timeout_minutes

    def get_max_session_duration_minutes(self) -> int:
        """Get maximum session duration in minutes."""
        return self.session_policy.max_duration_minutes

    def get_password_min_length(self) -> int:
        """Get minimum password length."""
        return self.password_policy.min_length

    def add_compliance_requirement(self, requirement: str) -> None:
        """Add a compliance requirement."""
        if requirement not in self.compliance_requirements:
            self.compliance_requirements.append(requirement)

    def add_security_header(self, header: str, value: str) -> None:
        """Add a security header."""
        self.security_headers[header] = value

    def add_custom_setting(self, key: str, value: SecuritySettingValue) -> None:
        """Add a custom security setting."""
        self.custom_security_settings.add_setting(key, value)

    def get_custom_setting(
        self, key: str, default: SecuritySettingValue = None
    ) -> SecuritySettingValue:
        """Get a custom security setting."""
        return self.custom_security_settings.get_setting(key, default)

    def meets_compliance(self, required_standards: list[str]) -> bool:
        """Check if this security level meets required compliance standards."""
        return all(std in self.compliance_requirements for std in required_standards)

    def to_environment_dict(self) -> dict[str, str]:
        """Convert to environment variables dictionary."""
        return {
            "ONEX_SECURITY_LEVEL": self.level_name,
            "ONEX_SECURITY_SCORE": str(self.security_score),
            "ONEX_ENCRYPTION_REQUIRED": str(self.encryption_required).lower(),
            "ONEX_AUTH_REQUIRED": str(self.authentication_required).lower(),
            "ONEX_AUTHZ_REQUIRED": str(self.authorization_required).lower(),
            "ONEX_AUDIT_LOGGING": str(self.audit_logging_required).lower(),
            "ONEX_STRICT_VALIDATION": str(self.input_validation_strict).lower(),
            "ONEX_RATE_LIMITING": str(self.rate_limiting_enabled).lower(),
            "ONEX_MIN_TLS_VERSION": str(self.minimum_tls_version),
            "ONEX_SESSION_TIMEOUT": str(self.get_session_timeout_minutes()),
            "ONEX_MAX_SESSION_DURATION": str(self.get_max_session_duration_minutes()),
        }

    @classmethod
    def create_minimal(cls) -> "ModelSecurityLevel":
        """Create minimal security configuration."""
        return cls(
            level_name="minimal",
            display_name="Minimal Security",
            security_score=0.1,
            encryption_required=False,
            authentication_required=False,
            authorization_required=False,
            audit_logging_required=False,
            input_validation_strict=False,
            rate_limiting_enabled=False,
            allowed_protocols=["http", "https", "ftp"],
            blocked_protocols=[],
        )

    @classmethod
    def create_standard(cls) -> "ModelSecurityLevel":
        """Create standard security configuration."""
        return cls(
            level_name="standard",
            display_name="Standard Security",
            security_score=0.5,
            encryption_required=True,
            authentication_required=True,
            authorization_required=True,
            audit_logging_required=True,
            input_validation_strict=True,
            rate_limiting_enabled=True,
        )

    @classmethod
    def create_high_security(cls) -> "ModelSecurityLevel":
        """Create high security configuration."""
        return cls(
            level_name="high_security",
            display_name="High Security",
            security_score=0.8,
            encryption_required=True,
            authentication_required=True,
            authorization_required=True,
            audit_logging_required=True,
            input_validation_strict=True,
            rate_limiting_enabled=True,
            minimum_tls_version=ModelSemVer(major=1, minor=3, patch=0),
            password_policy=ModelPasswordPolicy.create_strict(),
            session_policy=ModelSessionPolicy.create_strict(),
            compliance_requirements=["SOC2", "ISO27001"],
        )

    @classmethod
    def create_maximum(cls) -> "ModelSecurityLevel":
        """Create maximum security configuration."""
        return cls(
            level_name="maximum",
            display_name="Maximum Security",
            security_score=1.0,
            encryption_required=True,
            authentication_required=True,
            authorization_required=True,
            audit_logging_required=True,
            input_validation_strict=True,
            rate_limiting_enabled=True,
            minimum_tls_version=ModelSemVer(major=1, minor=3, patch=0),
            allowed_protocols=["https"],
            blocked_protocols=["http", "ftp", "telnet", "ssh"],
            password_policy=ModelPasswordPolicy.create_maximum(),
            session_policy=ModelSessionPolicy.create_maximum(),
            network_restrictions=ModelNetworkRestrictions.create_maximum(),
            compliance_requirements=["SOC2", "ISO27001", "FedRAMP", "HIPAA"],
        )
