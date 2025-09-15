# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# description: Secure event payload model with zero-trust validation and input sanitization
# lifecycle: active
# meta_type: model
# name: model_secure_event_payload.py
# namespace: python://omnibase.model.intelligence.model_secure_event_payload
# owner: OmniNode Team
# version: 1.0.0
# === /OmniNode:Metadata ===

import re
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.exceptions import OnexError


class ModelSecureEventPayload(BaseModel):
    """
    Enterprise-grade secure event payload with zero-trust validation.

    Provides comprehensive input sanitization, validation, and security controls
    for all event data crossing system boundaries.

    Security Features:
    - Zero-trust validation of all input fields
    - Input sanitization against injection attacks
    - Size limits to prevent DoS attacks
    - Content filtering for malicious patterns
    - Structured validation with fail-fast patterns
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict: no extra fields allowed for security
        validate_assignment=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

    # Core payload fields with security constraints
    event_data: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict,
        description="Sanitized event payload data with restricted types",
        max_length=50,  # Maximum 50 key-value pairs
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Event metadata (string values only for security)",
        max_length=20,  # Maximum 20 metadata entries
    )

    source_node_id: str = Field(
        ...,
        description="Validated source node identifier",
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_-]+$",  # Alphanumeric, underscore, dash only
    )

    correlation_id: UUID | None = Field(
        None,
        description="Correlation UUID for request tracing",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event creation timestamp (UTC)",
    )

    security_context: dict[str, str] = Field(
        default_factory=dict,
        description="Security context information",
        max_length=10,  # Limited security context entries
    )

    # Security validation patterns
    MALICIOUS_PATTERNS: ClassVar[list[str]] = [
        r"<script\b",  # XSS attempts
        r"javascript:",  # JavaScript injection
        r"on\w+\s*=",  # Event handler injection
        r"eval\s*\(",  # Code evaluation
        r"exec\s*\(",  # Code execution
        r"import\s+",  # Import statements
        r"__\w+__",  # Python dunder methods
        r"\$\{.*\}",  # Template injection
        r"<%.*%>",  # Template injection
        r"union\s+select",  # SQL injection (case insensitive)
        r"drop\s+table",  # SQL injection
        r"delete\s+from",  # SQL injection
        r"\.\./",  # Path traversal
        r"file://",  # File URI
        r"ftp://",  # FTP URI
    ]

    # Compiled regex patterns for performance
    _compiled_patterns: list[re.Pattern] | None = None

    @classmethod
    def _get_compiled_patterns(cls) -> list[re.Pattern]:
        """Get compiled regex patterns for malicious content detection."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE) for pattern in cls.MALICIOUS_PATTERNS
            ]
        return cls._compiled_patterns

    @field_validator("event_data")
    @classmethod
    def validate_event_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and sanitize event data with zero-trust security.

        Args:
            v: Raw event data dictionary

        Returns:
            Sanitized and validated event data

        Raises:
            OnexError: If validation fails or malicious content detected
        """
        if not isinstance(v, dict):
            msg = "Event data must be a dictionary"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_event_data",
                },
            )

        # Check size limits (DoS prevention)
        if len(v) > 50:
            msg = f"Event data exceeds maximum size limit: {len(v)} > 50"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_event_data",
                },
            )

        sanitized_data = {}
        patterns = cls._get_compiled_patterns()

        for key, value in v.items():
            # Validate key format
            if not isinstance(key, str) or len(key) > 128:
                msg = f"Invalid event data key: {key}"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_event_data",
                        "key": str(key),
                    },
                )

            # Sanitize and validate key
            sanitized_key = cls._sanitize_string(key)
            cls._check_malicious_patterns(sanitized_key, patterns, f"key '{key}'")

            # Initialize sanitized_value with proper type
            sanitized_value: str | int | float | bool | list[str] = ""

            # Validate and sanitize value based on type
            if isinstance(value, str):
                if len(value) > 10000:  # 10KB limit per string
                    msg = f"String value too large: {len(value)} characters"
                    raise OnexError(
                        CoreErrorCode.VALIDATION_ERROR,
                        msg,
                        details={
                            "component": "ModelSecureEventPayload",
                            "operation": "validate_event_data",
                            "value_length": len(value),
                        },
                    )
                sanitized_value = cls._sanitize_string(value)
                cls._check_malicious_patterns(
                    sanitized_value,
                    patterns,
                    f"value for '{key}'",
                )

            elif isinstance(value, (int, float, bool)):
                sanitized_value = value

            elif isinstance(value, list):
                if len(value) > 100:  # Max 100 items per list
                    msg = f"List too large: {len(value)} items"
                    raise OnexError(
                        CoreErrorCode.VALIDATION_ERROR,
                        msg,
                        details={
                            "component": "ModelSecureEventPayload",
                            "operation": "validate_event_data",
                            "list_length": len(value),
                        },
                    )

                sanitized_list: list[str] = []
                for item in value:
                    if not isinstance(item, str):
                        msg = f"List items must be strings, got: {type(item)}"
                        raise OnexError(
                            CoreErrorCode.VALIDATION_ERROR,
                            msg,
                            details={
                                "component": "ModelSecureEventPayload",
                                "operation": "validate_event_data",
                                "item_type": str(type(item)),
                            },
                        )
                    if len(item) > 1000:  # 1KB limit per list item
                        msg = f"List item too large: {len(item)} characters"
                        raise OnexError(
                            CoreErrorCode.VALIDATION_ERROR,
                            msg,
                            details={
                                "component": "ModelSecureEventPayload",
                                "operation": "validate_event_data",
                                "item_length": len(item),
                            },
                        )

                    sanitized_item = cls._sanitize_string(item)
                    cls._check_malicious_patterns(
                        sanitized_item,
                        patterns,
                        f"list item in '{key}'",
                    )
                    sanitized_list.append(sanitized_item)
                sanitized_value = sanitized_list

            else:
                msg = f"Unsupported value type: {type(value)} for key '{key}'"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_event_data",
                        "key": key,
                        "value_type": str(type(value)),
                    },
                )

            sanitized_data[sanitized_key] = sanitized_value

        return sanitized_data

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, str]) -> dict[str, str]:
        """
        Validate and sanitize metadata with security controls.

        Args:
            v: Raw metadata dictionary

        Returns:
            Sanitized and validated metadata

        Raises:
            OnexError: If validation fails
        """
        if not isinstance(v, dict):
            msg = "Metadata must be a dictionary"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_metadata",
                },
            )

        if len(v) > 20:
            msg = f"Metadata exceeds maximum size limit: {len(v)} > 20"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_metadata",
                    "actual_size": len(v),
                },
            )

        sanitized_metadata = {}
        patterns = cls._get_compiled_patterns()

        for key, value in v.items():
            # Validate types
            if not isinstance(key, str) or not isinstance(value, str):
                msg = "Metadata keys and values must be strings"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_metadata",
                        "key_type": str(type(key)),
                        "value_type": str(type(value)),
                    },
                )

            # Validate lengths
            if len(key) > 128 or len(value) > 1000:
                msg = "Metadata key/value too large"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_metadata",
                        "key_length": len(key),
                        "value_length": len(value),
                    },
                )

            # Sanitize and check for malicious content
            sanitized_key = cls._sanitize_string(key)
            sanitized_value = cls._sanitize_string(value)

            cls._check_malicious_patterns(
                sanitized_key,
                patterns,
                f"metadata key '{key}'",
            )
            cls._check_malicious_patterns(
                sanitized_value,
                patterns,
                f"metadata value for '{key}'",
            )

            sanitized_metadata[sanitized_key] = sanitized_value

        return sanitized_metadata

    @field_validator("security_context")
    @classmethod
    def validate_security_context(cls, v: dict[str, str]) -> dict[str, str]:
        """
        Validate security context with strict controls.

        Args:
            v: Raw security context dictionary

        Returns:
            Validated security context

        Raises:
            OnexError: If validation fails
        """
        if not isinstance(v, dict):
            msg = "Security context must be a dictionary"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_security_context",
                },
            )

        if len(v) > 10:
            msg = f"Security context exceeds maximum size: {len(v)} > 10"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_security_context",
                    "actual_size": len(v),
                },
            )

        # Only allow specific security context keys
        allowed_keys = {
            "user_id",
            "session_id",
            "request_id",
            "source_ip",
            "user_agent",
            "authentication_method",
            "authorization_level",
            "tenant_id",
            "organization_id",
            "environment",
        }

        sanitized_context = {}
        patterns = cls._get_compiled_patterns()

        for key, value in v.items():
            if key not in allowed_keys:
                msg = f"Unauthorized security context key: {key}"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_security_context",
                        "unauthorized_key": key,
                    },
                )

            if not isinstance(value, str) or len(value) > 256:
                msg = f"Invalid security context value for '{key}'"
                raise OnexError(
                    CoreErrorCode.VALIDATION_ERROR,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "validate_security_context",
                        "key": key,
                        "value_length": len(value) if isinstance(value, str) else 0,
                    },
                )

            sanitized_value = cls._sanitize_string(value)
            cls._check_malicious_patterns(
                sanitized_value,
                patterns,
                f"security context '{key}'",
            )

            sanitized_context[key] = sanitized_value

        return sanitized_context

    @model_validator(mode="after")
    def validate_total_payload_size(self) -> "ModelSecureEventPayload":
        """
        Validate total payload size to prevent DoS attacks.

        Returns:
            Validated model instance

        Raises:
            OnexError: If total payload exceeds size limits
        """
        # Estimate total payload size (rough calculation)
        total_size = 0

        # Event data size
        for key, value in self.event_data.items():
            total_size += len(key)
            if isinstance(value, str):
                total_size += len(value)
            elif isinstance(value, list):
                total_size += sum(len(item) for item in value)
            else:
                total_size += 50  # Rough estimate for numbers/booleans

        # Metadata size
        for key, value in self.metadata.items():
            total_size += len(key) + len(value)

        # Security context size
        for key, value in self.security_context.items():
            total_size += len(key) + len(value)

        # Other fields (rough estimates)
        total_size += len(self.source_node_id) + 100  # timestamps, UUIDs, etc.

        # 100KB total payload limit
        if total_size > 100_000:
            msg = f"Total payload size exceeds 100KB limit: {total_size} bytes"
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                msg,
                details={
                    "component": "ModelSecureEventPayload",
                    "operation": "validate_total_payload_size",
                    "actual_size": total_size,
                    "limit": 100_000,
                },
            )

        return self

    @staticmethod
    def _sanitize_string(value: str) -> str:
        """
        Sanitize string input by removing/escaping dangerous characters.

        Args:
            value: Raw string value

        Returns:
            Sanitized string value
        """
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes and control characters (except common whitespace)
        sanitized = "".join(
            char for char in value if ord(char) >= 32 or char in "\t\n\r"
        )

        # Normalize unicode and strip excessive whitespace
        sanitized = sanitized.strip()

        # Replace multiple consecutive whitespace with single space
        return re.sub(r"\s+", " ", sanitized)

    @classmethod
    def _check_malicious_patterns(
        cls,
        value: str,
        patterns: list[re.Pattern],
        context: str,
    ) -> None:
        """
        Check string for malicious patterns.

        Args:
            value: String to check
            patterns: Compiled regex patterns
            context: Context description for error messages

        Raises:
            OnexError: If malicious pattern detected
        """
        for pattern in patterns:
            if pattern.search(value):
                msg = f"Malicious pattern detected in {context}: {pattern.pattern}"
                raise OnexError(
                    CoreErrorCode.SECURITY_VIOLATION,
                    msg,
                    details={
                        "component": "ModelSecureEventPayload",
                        "operation": "_check_malicious_patterns",
                        "context": context,
                        "pattern": pattern.pattern,
                    },
                )

    def get_total_size_bytes(self) -> int:
        """
        Calculate total payload size in bytes.

        Returns:
            Total size in bytes
        """
        total_size = 0

        # Event data size
        for key, value in self.event_data.items():
            total_size += len(key.encode("utf-8"))
            if isinstance(value, str):
                total_size += len(value.encode("utf-8"))
            elif isinstance(value, list):
                total_size += sum(len(item.encode("utf-8")) for item in value)
            else:
                total_size += len(str(value).encode("utf-8"))

        # Metadata and security context size
        for key, value in self.metadata.items():
            total_size += len(key.encode("utf-8")) + len(value.encode("utf-8"))

        for key, value in self.security_context.items():
            total_size += len(key.encode("utf-8")) + len(value.encode("utf-8"))

        return total_size

    def to_audit_dict(self) -> dict[str, Any]:
        """
        Convert payload to audit-safe dictionary.

        Returns:
            Dictionary suitable for audit logging
        """
        return {
            "source_node_id": self.source_node_id,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "timestamp": self.timestamp.isoformat(),
            "event_data_keys": list(self.event_data.keys()),
            "metadata_keys": list(self.metadata.keys()),
            "security_context_keys": list(self.security_context.keys()),
            "total_size_bytes": self.get_total_size_bytes(),
        }
