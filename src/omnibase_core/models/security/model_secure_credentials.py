import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, SecretStr

from omnibase_core.errors.exception_groups import VALIDATION_ERRORS

from .model_audit_data import ModelAuditData
from .model_credential_validation_result import ModelCredentialValidationResult
from .model_credentials_analysis import ModelCredentialsAnalysis
from .model_debug_data import ModelDebugData
from .model_log_safe_data import ModelLogSafeData
from .model_mask_data import ModelMaskData

logger = logging.getLogger(__name__)
T = TypeVar("T", bound="ModelSecureCredentials")

# Exclude T from wildcard imports
__all__ = ["ModelSecureCredentials"]


class ModelSecureCredentials(BaseModel, ABC):
    """
    Enterprise-grade base model for secure credential handling with comprehensive
    masking, validation, serialization, and environment integration capabilities.

    Features:
    - Advanced secret masking with pattern detection
    - Environment variable loading with prefix support
    - Secure serialization for logging and debugging
    - Credential strength assessment
    - Field-level security classification
    - Audit trail support
    """

    # === Abstract Methods ===

    @classmethod
    @abstractmethod
    def load_from_env(cls: type[T], env_prefix: str = "ONEX_") -> T:
        """Load credentials from environment variables with prefix."""
        ...

    # === Core Security Methods ===

    def get_masked_dict(self, mask_level: str = "standard") -> ModelMaskData:
        """
        Get dictionary representation with secrets masked based on security level.

        Args:
            mask_level: Masking level ('minimal', 'standard', 'aggressive')
        """
        data = self.model_dump()
        masked_data = self._mask_secrets_recursive(data, mask_level)
        if isinstance(masked_data, dict):
            return ModelMaskData.from_dict(masked_data)
        return ModelMaskData()

    def _mask_secrets_recursive(self, data: Any, mask_level: str = "standard") -> Any:
        """Recursively mask SecretStr fields and sensitive patterns in data structure."""
        if isinstance(data, dict):
            return {
                key: self._mask_secrets_recursive(value, mask_level)
                for key, value in data.items()
            }
        if isinstance(data, list):
            return [self._mask_secrets_recursive(item, mask_level) for item in data]
        if isinstance(data, SecretStr):
            return self._mask_secret_value(data.get_secret_value(), mask_level)
        if isinstance(data, str):
            return self._mask_if_sensitive_string(data, mask_level)
        return data

    def _mask_secret_value(self, value: str, mask_level: str) -> str:
        """Mask secret value based on masking level."""
        if not value:
            return value

        if mask_level == "minimal":
            # Show first and last 2 characters for debugging
            if len(value) <= 4:
                return "*" * len(value)
            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

        if mask_level == "standard":
            return "***MASKED***"

        if mask_level == "aggressive":
            return "***REDACTED***"

        return "***MASKED***"

    def _mask_if_sensitive_string(self, value: str, mask_level: str) -> str:
        """Mask string if it appears to be sensitive based on patterns."""
        # Only check patterns for aggressive masking
        if mask_level != "aggressive":
            return value

        # Patterns that indicate sensitive data
        sensitive_patterns = [
            r"^[A-Za-z0-9+/]{40,}={0,2}$",  # Base64 encoded (likely secret)
            r"^[a-f0-9]{32,}$",  # Hex strings (likely hash/token)
            r"^[A-Z0-9]{8,}_[A-Z0-9]{8,}$",  # API key pattern
            r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer token
            r"-----BEGIN[^-]+-----.*-----END[^-]+-----",  # Certificate/key
        ]

        for pattern in sensitive_patterns:
            if re.match(pattern, value, re.DOTALL):
                return self._mask_secret_value(value, mask_level)

        return value

    # === Credential Analysis ===

    def get_credential_strength_assessment(self) -> ModelCredentialsAnalysis:
        """Assess the strength and security of stored credentials."""
        total_secrets = 0
        empty_secrets = 0
        weak_secrets = 0
        strong_secrets = 0
        issues: list[str] = []
        recommendations: list[str] = []

        for field_name, _field_info in self.__class__.model_fields.items():
            field_value = getattr(self, field_name)

            if isinstance(field_value, SecretStr):
                total_secrets += 1
                secret_value = field_value.get_secret_value()

                if not secret_value:
                    empty_secrets += 1
                    issues.append(f"Empty secret: {field_name}")
                elif len(secret_value) < 8:
                    weak_secrets += 1
                    issues.append(f"Weak secret (too short): {field_name}")
                elif len(secret_value) < 16:
                    weak_secrets += 1
                    issues.append(f"Weak secret (consider longer): {field_name}")
                else:
                    strong_secrets += 1

        # Generate recommendations
        if empty_secrets > 0:
            recommendations.append("Set values for all required secrets")

        if weak_secrets > 0:
            recommendations.append("Use longer, more complex secrets")

        if total_secrets == 0:
            recommendations.append("Consider using SecretStr for sensitive fields")

        # Calculate strength score
        if total_secrets == 0:
            strength_score = 0
        else:
            strength_score = int((strong_secrets / total_secrets) * 100)

        from .model_credentials_analysis import ModelManagerAssessment

        return ModelCredentialsAnalysis(
            strength_score=strength_score,
            password_entropy=None,
            common_patterns=[],
            security_issues=issues,
            recommendations=recommendations,
            compliance_status="compliant" if len(issues) == 0 else "non_compliant",
            risk_level="low" if weak_secrets == 0 else "high",
            manager_assessment=ModelManagerAssessment(
                backend_security_level="standard",
                audit_compliance="enabled",
                fallback_resilience="medium",
            ),
        )

    def get_security_classification(self) -> dict[str, str]:
        """Get security classification for each field."""
        classification = {}

        for field_name, _field_info in self.__class__.model_fields.items():
            field_value = getattr(self, field_name)

            if isinstance(field_value, SecretStr):
                classification[field_name] = "secret"
            elif any(
                sensitive in field_name.lower()
                for sensitive in ["password", "token", "key", "secret", "credential"]
            ):
                classification[field_name] = "sensitive"
            elif any(
                pii in field_name.lower()
                for pii in ["username", "email", "name", "id", "user"]
            ):
                classification[field_name] = "pii"
            else:
                classification[field_name] = "public"

        return classification

    # === Environment Integration ===

    def validate_environment_variables(self, env_prefix: str = "ONEX_") -> list[str]:
        """Validate that required environment variables are available."""
        issues = []

        for field_name, field_info in self.__class__.model_fields.items():
            if field_info.is_required():
                env_var_name = f"{env_prefix}{field_name.upper()}"
                if not os.getenv(env_var_name):
                    issues.append(
                        f"Missing required environment variable: {env_var_name}",
                    )

        return issues

    def get_environment_mapping(self, env_prefix: str = "ONEX_") -> dict[str, str]:
        """Get mapping of model fields to environment variable names."""
        mapping = {}

        for field_name in self.__class__.model_fields:
            env_var_name = f"{env_prefix}{field_name.upper()}"
            mapping[field_name] = env_var_name

        return mapping

    def load_from_environment_with_validation(
        self,
        env_prefix: str = "ONEX_",
    ) -> list[str]:
        """Load values from environment with validation, return any issues."""
        issues = []
        env_mapping = self.get_environment_mapping(env_prefix)

        for field_name, env_var in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                try:
                    # Attempt to set the field value
                    if hasattr(self, field_name):
                        if isinstance(getattr(self, field_name), SecretStr):
                            setattr(self, field_name, SecretStr(env_value))
                        else:
                            setattr(self, field_name, env_value)
                except VALIDATION_ERRORS as e:
                    # Exception handling for field value assignment:
                    # - TypeError: Type mismatch during assignment
                    # - ValidationError: Pydantic field validator rejects the value
                    # - ValueError: Invalid value format (e.g., wrong string format)
                    # Log the specific error for debugging while adding to issues
                    logger.warning(
                        f"Failed to load environment variable {env_var} for field {field_name}: {e!s}",
                        extra={
                            "env_var": env_var,
                            "field_name": field_name,
                            "error": str(e),
                        },
                    )
                    issues.append(f"Failed to load {env_var}: {e}")

        return issues

    # === Serialization & Logging ===

    def to_log_safe_dict(self) -> ModelLogSafeData:
        """Get dictionary safe for logging (all secrets masked)."""
        mask_data = self.get_masked_dict(mask_level="standard")
        # Convert mask_data to proper dict[str, Any]format for log-safe data
        masked_dict = mask_data.to_dict()
        return ModelLogSafeData(
            service_name=(
                str(masked_dict.get("service_name"))
                if masked_dict.get("service_name") is not None
                else None
            ),
            connection_status=(
                str(masked_dict.get("connection_status"))
                if masked_dict.get("connection_status") is not None
                else None
            ),
            host_info=(
                str(masked_dict.get("host_info"))
                if masked_dict.get("host_info") is not None
                else None
            ),
            port_info=(
                str(masked_dict.get("port_info"))
                if masked_dict.get("port_info") is not None
                else None
            ),
            username_info=(
                str(masked_dict.get("username_info"))
                if masked_dict.get("username_info") is not None
                else None
            ),
            additional_fields={
                k: str(v)
                for k, v in masked_dict.items()
                if k
                not in [
                    "service_name",
                    "connection_status",
                    "host_info",
                    "port_info",
                    "username_info",
                ]
            },
            metadata={"security_level": "log_safe", "masking_applied": "standard"},
        )

    def to_debug_dict(self) -> ModelDebugData:
        """Get dictionary for debugging (minimal masking)."""
        mask_data = self.get_masked_dict(mask_level="minimal")
        # Convert mask_data to proper debug format
        masked_dict = mask_data.to_dict()
        return ModelDebugData(
            connection_details={
                k: str(v) for k, v in masked_dict.items() if k.startswith("connection_")
            },
            credential_status={
                k: str(v) for k, v in masked_dict.items() if k.startswith("credential_")
            },
            validation_results={
                k: str(v) for k, v in masked_dict.items() if k.startswith("validation_")
            },
            performance_metrics={
                k: str(v) for k, v in masked_dict.items() if k.startswith("perf_")
            },
            error_details=[
                str(v)
                for k, v in masked_dict.items()
                if k == "errors" and isinstance(v, list)
            ],
            debug_flags={
                k: bool(v) for k, v in masked_dict.items() if isinstance(v, bool)
            },
        )

    def to_audit_dict(self) -> ModelAuditData:
        """Get dictionary for audit logging (aggressive masking)."""
        return ModelAuditData(
            action="credential_access",
            resource=f"{self.__class__.__name__}",
            result="masked",
            security_level="audit",
            compliance_tags=["credential_masking", "audit_trail"],
            audit_metadata=None,  # Masked data stored elsewhere, not in typed metadata
        )

    def export_to_env_template(self, env_prefix: str = "ONEX_") -> str:
        """Export field names as environment variable template."""
        lines = ["# Environment variables template"]
        lines.append(f"# Generated from {self.__class__.__name__}")
        lines.append("")

        env_mapping = self.get_environment_mapping(env_prefix)
        classification = self.get_security_classification()

        for field_name, env_var in env_mapping.items():
            field_info = self.__class__.model_fields.get(field_name)
            description = field_info.description if field_info else ""
            security_level = classification.get(field_name, "public")

            lines.append(f"# {description} ({security_level})")
            if field_info and field_info.is_required():
                lines.append(f"{env_var}=  # REQUIRED")
            else:
                lines.append(f"# {env_var}=  # OPTIONAL")
            lines.append("")

        return "\n".join(lines)

    # === Validation & Health Checks ===

    def validate_credentials(self) -> ModelCredentialValidationResult:
        """Perform comprehensive validation of all credentials."""
        is_valid = True
        issues: list[str] = []
        warnings: list[str] = []

        strength_assessment = self.get_credential_strength_assessment()

        # Check for empty required secrets
        for field_name, field_info in self.__class__.model_fields.items():
            if field_info.is_required():
                field_value = getattr(self, field_name)
                if (
                    isinstance(field_value, SecretStr)
                    and not field_value.get_secret_value()
                ):
                    issues.append(f"Required secret is empty: {field_name}")
                    is_valid = False
                elif not field_value:
                    issues.append(f"Required field is empty: {field_name}")
                    is_valid = False

        # Add strength assessment issues
        issues.extend(strength_assessment.security_issues)

        # Count weak secrets from strength assessment - need to implement this logic
        weak_secret_count = 0
        for issue in strength_assessment.security_issues:
            if "weak secret" in issue.lower():
                weak_secret_count += 1

        if weak_secret_count > 0:
            warnings.append(f"{weak_secret_count} weak secrets detected")

        return ModelCredentialValidationResult(
            is_valid=is_valid,
            errors=issues,
            warnings=warnings,
            strength_score=strength_assessment.strength_score,
            compliance_status=strength_assessment.compliance_status,
            recommendations=strength_assessment.recommendations,
        )

    def can_connect(self) -> bool:
        """Test if credentials are sufficient for connection (override in subclasses)."""
        validation = self.validate_credentials()
        return validation.is_valid

    # === Factory Methods ===

    @classmethod
    def create_from_env_with_fallbacks(
        cls: type[T],
        env_prefix: str = "ONEX_",
        fallback_prefixes: list[str] | None = None,
    ) -> T:
        """Create instance from environment with fallback prefixes."""
        fallback_prefixes = fallback_prefixes if fallback_prefixes is not None else []

        # Helper to check if any env vars with prefix exist
        def has_env_vars(prefix: str) -> bool:
            """Check if any environment variables with the given prefix exist."""
            return any(key.startswith(prefix) for key in os.environ)

        # Try primary prefix first
        if has_env_vars(env_prefix):
            try:
                return cls.load_from_env(env_prefix)
            except VALIDATION_ERRORS as e:
                # Exception handling for load_from_env abstract method:
                # - TypeError: Type conversion fails for field value
                # - ValidationError: Pydantic model validation fails during construction
                # - ValueError: Invalid field value format in environment variable
                # We continue to fallback prefixes on failure.
                logger.debug(
                    f"Failed to load credentials with primary prefix {env_prefix}: {e!s}",
                    extra={"env_prefix": env_prefix, "error": str(e)},
                )

        # Try fallback prefixes
        for fallback_prefix in fallback_prefixes:
            if has_env_vars(fallback_prefix):
                try:
                    return cls.load_from_env(fallback_prefix)
                except VALIDATION_ERRORS as e:
                    # Exception handling for load_from_env abstract method:
                    # - TypeError: Type conversion fails for field value
                    # - ValidationError: Pydantic model validation fails during construction
                    # - ValueError: Invalid field value format in environment variable
                    # We continue to next fallback prefix on failure.
                    logger.debug(
                        f"Failed to load credentials with fallback prefix {fallback_prefix}: {e!s}",
                        extra={"fallback_prefix": fallback_prefix, "error": str(e)},
                    )
                    continue

        # If all fail, create with defaults
        logger.warning(
            f"No environment variables found for prefix {env_prefix} or fallbacks {fallback_prefixes}. "
            f"Creating instance with defaults.",
            extra={
                "env_prefix": env_prefix,
                "fallback_prefixes": fallback_prefixes,
            },
        )

        # Create with defaults and load what we can
        instance = cls()
        validation_issues = instance.load_from_environment_with_validation(env_prefix)
        if validation_issues:
            logger.info(
                f"Created credentials instance with validation issues: {validation_issues}",
                extra={"validation_issues": validation_issues},
            )
        return instance

    @classmethod
    def create_empty_template(cls: type[T]) -> T:
        """Create empty instance for template generation."""
        # Get default values for all fields
        field_defaults = {}
        for field_name, field_info in cls.model_fields.items():
            if isinstance(field_info.default, SecretStr):
                field_defaults[field_name] = SecretStr("")
            elif field_info.default is not None:
                field_defaults[field_name] = field_info.default
            # For required fields without defaults, leave them out to trigger validation errors

        return cls(**field_defaults)
