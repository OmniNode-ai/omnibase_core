"""Enterprise-grade security utilities for credential masking and security operations."""

import re
from collections.abc import Mapping, Sequence

from omnibase_core.enums.enum_credential_strength import EnumCredentialStrength
from omnibase_core.models.security.model_credential_audit_report import (
    ModelCredentialAuditReport,
)
from omnibase_core.models.security.model_credential_strength_assessment import (
    ModelCredentialStrengthAssessment,
)
from omnibase_core.models.security.model_secure_mask_config import ModelSecureMaskConfig


class UtilSecurity:
    """
    Enterprise-grade security utilities for credential masking and security operations.

    Features:
    - Comprehensive credential masking strategies
    - Recursive dictionary credential masking
    - Configurable masking patterns
    - Security pattern detection
    - Credential strength assessment
    - Audit trail support

    Thread Safety:
        UtilSecurity is fully thread-safe. All methods are static and stateless,
        operating only on their input parameters and returning new data structures.
        The class-level DEFAULT_SENSITIVE_PATTERNS set is read-only and never
        modified at runtime. Methods that process collections (mask_dict_credentials,
        audit_credential_usage) create fresh output structures for each call,
        ensuring no shared mutable state exists between concurrent invocations.

    Example:
        >>> from omnibase_core.utils import UtilSecurity
        >>> masked = UtilSecurity.mask_credential("my-secret-token")
        >>> print(masked)  # "my********en"

    .. note::
        Previously named ``ModelSecurityUtils``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Util``
        prefix indicates a utility class.
    """

    # Default sensitive field patterns
    DEFAULT_SENSITIVE_PATTERNS = {
        "password",
        "token",
        "key",
        "secret",
        "credential",
        "auth",
        "api_key",
        "bearer_token",
        "sasl_password",
        "ssl_password",
        "private_key",
        "cert_key",
        "access_token",
        "refresh_token",
    }

    @staticmethod
    def mask_credential(
        value: str,
        mask_char: str = "*",
        visible_chars: int = 2,
        min_mask_length: int = 8,
    ) -> str:
        """
        Mask a credential string, showing only the first and last few characters.

        Args:
            value: The credential to mask
            mask_char: Character to use for masking
            visible_chars: Number of characters to show at start and end
            min_mask_length: Minimum length of masked section

        Returns:
            Masked credential string
        """
        if not value or not isinstance(value, str):
            return mask_char * min_mask_length if value else ""

        # For very short values, mask completely
        if len(value) <= visible_chars * 2:
            return mask_char * max(len(value), min_mask_length)

        start = value[:visible_chars]
        end = value[-visible_chars:]
        middle_length = max(len(value) - (visible_chars * 2), min_mask_length)
        middle = mask_char * middle_length

        return f"{start}{middle}{end}"

    @staticmethod
    def mask_dict_credentials(
        data: Mapping[str, object],
        sensitive_patterns: set[str] | None = None,
        recursive: bool = True,
    ) -> dict[str, object]:
        """
        Recursively mask credential fields in a dictionary.

        Args:
            data: Dictionary that may contain credentials (read-only view)
            sensitive_patterns: Custom set of sensitive field patterns
            recursive: Whether to recursively process nested dictionaries

        Returns:
            New dictionary with credentials masked
        """
        if sensitive_patterns is None:
            sensitive_patterns = UtilSecurity.DEFAULT_SENSITIVE_PATTERNS

        masked_data: dict[str, object] = {}
        for key, value in data.items():
            if isinstance(value, Mapping) and recursive:
                # Recursively mask nested dictionaries
                masked_data[key] = UtilSecurity.mask_dict_credentials(
                    value,
                    sensitive_patterns,
                    recursive,
                )
            elif (
                isinstance(value, Sequence) and not isinstance(value, str) and recursive
            ):
                # Recursively mask lists (but not strings, which are also Sequence)
                masked_data[key] = UtilSecurity._mask_list_credentials(
                    value,
                    sensitive_patterns,
                )
            elif isinstance(value, str) and UtilSecurity._is_sensitive_field(
                key,
                sensitive_patterns,
            ):
                # Mask sensitive string values
                masked_data[key] = UtilSecurity.mask_credential(value)
            else:
                # Copy non-sensitive values as-is
                masked_data[key] = value

        return masked_data

    @staticmethod
    def _mask_list_credentials(
        data: Sequence[object],
        sensitive_patterns: set[str],
    ) -> list[object]:
        """
        Mask credentials in a list (may contain dicts and nested lists).

        Args:
            data: List that may contain credentials (read-only view)
            sensitive_patterns: Set of sensitive field patterns

        Returns:
            New list with credentials masked
        """
        masked_list: list[object] = []
        for item in data:
            if isinstance(item, Mapping):
                # Recursively mask dictionaries in the list
                masked_list.append(
                    UtilSecurity.mask_dict_credentials(
                        item,
                        sensitive_patterns,
                        recursive=True,
                    ),
                )
            elif isinstance(item, Sequence) and not isinstance(item, str):
                # Recursively mask nested lists (but not strings)
                masked_list.append(
                    UtilSecurity._mask_list_credentials(item, sensitive_patterns),
                )
            else:
                # Copy non-dictionary/list items as-is
                masked_list.append(item)

        return masked_list

    @staticmethod
    def _is_sensitive_field(field_name: str, sensitive_patterns: set[str]) -> bool:
        """Check if a field name matches sensitive patterns."""
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)

    @staticmethod
    def detect_credential_patterns(value: str) -> list[str]:
        """
        Detect potential credential patterns in a string.

        Args:
            value: String to analyze

        Returns:
            List of detected credential pattern types
        """
        patterns = []

        # API Key patterns
        if re.match(r"^sk_[a-zA-Z0-9]{20,}$", value):
            patterns.append("stripe_api_key")
        elif re.match(r"^[a-zA-Z0-9]{32}$", value):
            patterns.append("api_key_32_char")
        elif re.match(r"^[a-zA-Z0-9]{40}$", value):
            patterns.append("api_key_40_char")
        elif re.match(r"^[a-zA-Z0-9\-_]{64}$", value):
            patterns.append("api_key_64_char")

        # JWT Token pattern
        if re.match(r"^eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]*$", value):
            patterns.append("jwt_token")

        # GitHub token pattern
        if re.match(r"^ghp_[a-zA-Z0-9]{36}$", value):
            patterns.append("github_token")

        # AWS Access Key pattern
        if re.match(r"^AKIA[a-zA-Z0-9]{16}$", value):
            patterns.append("aws_access_key")

        # Password patterns (common characteristics)
        if len(value) >= 8:
            has_upper = any(c.isupper() for c in value)
            has_lower = any(c.islower() for c in value)
            has_digit = any(c.isdigit() for c in value)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value)

            if sum([has_upper, has_lower, has_digit, has_special]) >= 3:
                patterns.append("strong_password")
            elif sum([has_upper, has_lower, has_digit, has_special]) >= 2:
                patterns.append("moderate_password")

        return patterns

    @staticmethod
    def assess_credential_strength(value: str) -> ModelCredentialStrengthAssessment:
        """
        Assess the strength of a credential.

        Args:
            value: Credential to assess

        Returns:
            Strength assessment model with score and issues
        """
        issues = []
        score = 0

        # Length assessment
        if len(value) < 8:
            issues.append("Too short (minimum 8 characters)")
        elif len(value) >= 12:
            score += 2
        else:
            score += 1

        # Character variety
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value)

        variety_score = sum([has_upper, has_lower, has_digit, has_special])
        score += variety_score

        if not has_upper:
            issues.append("No uppercase letters")
        if not has_lower:
            issues.append("No lowercase letters")
        if not has_digit:
            issues.append("No numbers")
        if not has_special:
            issues.append("No special characters")

        # Common patterns
        if value.lower() in {"password", "123456", "admin", "root"}:
            issues.append("Common weak password")
            score = 0

        # Repeated characters
        if len(set(value)) < len(value) * 0.5:
            issues.append("Too many repeated characters")
            score = max(0, score - 2)

        # Determine strength
        if score >= 6:
            strength = EnumCredentialStrength.STRONG
        elif score >= 4:
            strength = EnumCredentialStrength.MODERATE
        elif score >= 2:
            strength = EnumCredentialStrength.WEAK
        else:
            strength = EnumCredentialStrength.VERY_WEAK

        return ModelCredentialStrengthAssessment(
            strength=strength,
            score=score,
            length=len(value),
            character_variety=variety_score,
            issues=issues,
            detected_patterns=UtilSecurity.detect_credential_patterns(value),
        )

    @staticmethod
    def create_secure_mask_config(
        mask_char: str = "*",
        visible_chars: int = 2,
        additional_patterns: set[str] | None = None,
    ) -> ModelSecureMaskConfig:
        """
        Create a secure masking configuration.

        Args:
            mask_char: Character to use for masking
            visible_chars: Number of visible characters at start/end
            additional_patterns: Additional sensitive field patterns

        Returns:
            Masking configuration object
        """
        patterns = UtilSecurity.DEFAULT_SENSITIVE_PATTERNS.copy()
        if additional_patterns:
            patterns.update(additional_patterns)

        return ModelSecureMaskConfig(
            mask_char=mask_char,
            visible_chars=visible_chars,
            sensitive_patterns=patterns,
            min_mask_length=8,
            recursive=True,
        )

    @staticmethod
    def audit_credential_usage(
        data: Mapping[str, object],
        config: ModelSecureMaskConfig | None = None,
    ) -> ModelCredentialAuditReport:
        """
        Audit credential usage in data structure.

        Args:
            data: Data structure to audit (read-only view)
            config: Masking configuration

        Returns:
            Audit report with security findings
        """
        if config is None:
            config = UtilSecurity.create_secure_mask_config()

        sensitive_patterns = (
            config.sensitive_patterns or UtilSecurity.DEFAULT_SENSITIVE_PATTERNS
        )

        audit_report = ModelCredentialAuditReport()

        def _audit_recursive(obj: object, path: str = "") -> None:
            """Recursively audit object for credentials."""
            if isinstance(obj, Mapping):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    audit_report.total_fields += 1

                    if UtilSecurity._is_sensitive_field(key, sensitive_patterns):
                        audit_report.sensitive_fields += 1
                        audit_report.masked_fields.append(current_path)

                        if isinstance(value, str):
                            patterns = UtilSecurity.detect_credential_patterns(
                                value,
                            )
                            if patterns:
                                audit_report.credential_patterns[current_path] = (
                                    patterns
                                )

                            strength = UtilSecurity.assess_credential_strength(
                                value,
                            )
                            if strength.strength in {
                                EnumCredentialStrength.WEAK,
                                EnumCredentialStrength.VERY_WEAK,
                            }:
                                audit_report.security_issues.append(
                                    f"Weak credential at {current_path}: {strength.strength.value}",
                                )

                    _audit_recursive(value, current_path)
            elif isinstance(obj, Sequence) and not isinstance(obj, str):
                for i, item in enumerate(obj):
                    _audit_recursive(item, f"{path}[{i}]" if path else f"[{i}]")

        _audit_recursive(data)

        return audit_report
