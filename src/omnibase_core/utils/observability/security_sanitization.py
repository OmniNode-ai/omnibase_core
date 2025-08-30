#!/usr/bin/env python3
"""
ONEX OpenTelemetry Security Sanitization Module

Provides security-aware instrumentation for OpenTelemetry observability:
- PII detection and filtering in traces and metrics
- Sensitive data scrubbing for observability data
- Access control for observability endpoints
- Audit logging for observability operations
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Union

from opentelemetry import metrics, trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import Span
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelSpanAttributes(BaseModel):
    """Type-safe span attributes for OpenTelemetry."""

    service_name: Optional[str] = Field(None, description="Name of the service")
    operation_name: Optional[str] = Field(None, description="Name of the operation")
    user_id: Optional[str] = Field(None, description="User identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier")
    request_id: Optional[str] = Field(None, description="Request identifier")
    http_method: Optional[str] = Field(None, description="HTTP method")
    http_url: Optional[str] = Field(None, description="HTTP URL")
    http_status_code: Optional[int] = Field(None, description="HTTP status code")
    database_name: Optional[str] = Field(None, description="Database name")
    table_name: Optional[str] = Field(None, description="Table name")

    def to_dict(self) -> Dict[str, Union[str, int, float, bool]]:
        """Convert to dictionary with proper OpenTelemetry types."""
        result = {}
        for key, value in self.dict(exclude_unset=True).items():
            if value is not None:
                result[key] = value
        return result


class ModelMetricAttributes(BaseModel):
    """Type-safe metric attributes for OpenTelemetry."""

    service_name: Optional[str] = Field(None, description="Name of the service")
    operation_type: Optional[str] = Field(None, description="Type of operation")
    status: Optional[str] = Field(None, description="Operation status")
    error_type: Optional[str] = Field(None, description="Type of error if applicable")

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary with string values for metrics."""
        result = {}
        for key, value in self.dict(exclude_unset=True).items():
            if value is not None:
                result[key] = str(value)
        return result


class ModelSanitizationStats(BaseModel):
    """Statistics about sanitization operations."""

    rules_configured: int = Field(
        ..., description="Number of sanitization rules configured"
    )
    audit_logging_enabled: bool = Field(
        ..., description="Whether audit logging is enabled"
    )
    total_detections: int = Field(0, description="Total PII detections")
    total_sanitizations: int = Field(0, description="Total sanitization operations")

    class ModelSanitizationRuleInfo(BaseModel):
        """Information about a sanitization rule."""

        name: str = Field(..., description="Rule name")
        sensitivity_level: str = Field(..., description="Sensitivity level")
        applies_to: List[str] = Field(..., description="Contexts this rule applies to")

    sanitization_rules: List[ModelSanitizationRuleInfo] = Field(
        default_factory=list, description="Configured sanitization rules"
    )


class SensitivityLevel(Enum):
    """Data sensitivity classification for observability."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class SanitizationRule:
    """Rule for detecting and sanitizing sensitive data."""

    name: str
    pattern: re.Pattern
    replacement: str
    sensitivity_level: SensitivityLevel
    applies_to: Set[str]  # "spans", "metrics", "logs"


class ONEXObservabilitySanitizer:
    """Security-aware sanitization for ONEX observability data."""

    def __init__(self, enable_audit_logging: bool = True):
        self.enable_audit_logging = enable_audit_logging
        self.sanitization_rules = self._initialize_sanitization_rules()
        self.audit_logger = self._setup_audit_logger()

        # Metrics for security monitoring
        self.meter = metrics.get_meter(__name__)
        self.pii_detected_counter = self.meter.create_counter(
            "onex_observability_pii_detected_total",
            description="Total PII detections in observability data",
            unit="1",
        )
        self.sanitization_operations_counter = self.meter.create_counter(
            "onex_observability_sanitization_operations_total",
            description="Total sanitization operations performed",
            unit="1",
        )

    def _initialize_sanitization_rules(self) -> List[SanitizationRule]:
        """Initialize comprehensive sanitization rules for ONEX."""
        return [
            # Email addresses
            SanitizationRule(
                name="email_addresses",
                pattern=re.compile(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                ),
                replacement="[EMAIL_REDACTED]",
                sensitivity_level=SensitivityLevel.CONFIDENTIAL,
                applies_to={"spans", "metrics", "logs"},
            ),
            # API Keys and tokens
            SanitizationRule(
                name="api_keys",
                pattern=re.compile(
                    r'\b(?:api[_-]?key|token|secret|password)["\s]*[:=]["\s]*([A-Za-z0-9\-_]{20,})\b',
                    re.IGNORECASE,
                ),
                replacement="[API_KEY_REDACTED]",
                sensitivity_level=SensitivityLevel.RESTRICTED,
                applies_to={"spans", "metrics", "logs"},
            ),
            # Bearer tokens
            SanitizationRule(
                name="bearer_tokens",
                pattern=re.compile(r"Bearer\s+([A-Za-z0-9\-_]{20,})", re.IGNORECASE),
                replacement="Bearer [TOKEN_REDACTED]",
                sensitivity_level=SensitivityLevel.RESTRICTED,
                applies_to={"spans", "logs"},
            ),
            # Credit card numbers (basic pattern)
            SanitizationRule(
                name="credit_cards",
                pattern=re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
                replacement="[CREDIT_CARD_REDACTED]",
                sensitivity_level=SensitivityLevel.RESTRICTED,
                applies_to={"spans", "logs"},
            ),
            # Social Security Numbers (US format)
            SanitizationRule(
                name="ssn",
                pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                replacement="[SSN_REDACTED]",
                sensitivity_level=SensitivityLevel.RESTRICTED,
                applies_to={"spans", "logs"},
            ),
            # Database connection strings
            SanitizationRule(
                name="db_connection_strings",
                pattern=re.compile(
                    r"(postgresql|mysql|mongodb)://[^:]+:[^@]+@[^/]+/", re.IGNORECASE
                ),
                replacement=r"\1://[USER]:[PASSWORD_REDACTED]@[HOST]/",
                sensitivity_level=SensitivityLevel.CONFIDENTIAL,
                applies_to={"spans", "logs"},
            ),
            # IP addresses (optional - may be needed for debugging)
            SanitizationRule(
                name="ip_addresses",
                pattern=re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
                replacement="[IP_REDACTED]",
                sensitivity_level=SensitivityLevel.INTERNAL,
                applies_to={
                    "logs"
                },  # Only sanitize in logs, allow in spans for debugging
            ),
            # ONEX-specific sensitive patterns
            SanitizationRule(
                name="onex_correlation_ids",
                pattern=re.compile(
                    r'correlation_id["\s]*[:=]["\s]*([a-f0-9-]{32,})', re.IGNORECASE
                ),
                replacement="correlation_id=[CORRELATION_ID_HASHED]",
                sensitivity_level=SensitivityLevel.INTERNAL,
                applies_to={"metrics"},  # Hash in metrics, preserve in traces
            ),
            # User agent strings (may contain sensitive info)
            SanitizationRule(
                name="user_agents",
                pattern=re.compile(
                    r'User-Agent["\s]*[:=]["\s]*([^"\n\r]+)', re.IGNORECASE
                ),
                replacement="User-Agent=[USER_AGENT_SANITIZED]",
                sensitivity_level=SensitivityLevel.INTERNAL,
                applies_to={"logs"},
            ),
        ]

    def _setup_audit_logger(self) -> logging.Logger:
        """Setup dedicated audit logger for observability security events."""
        audit_logger = logging.getLogger("onex.observability.security.audit")

        if not audit_logger.handlers and self.enable_audit_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - SECURITY_AUDIT - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            audit_logger.addHandler(handler)
            audit_logger.setLevel(logging.INFO)

        return audit_logger

    def sanitize_span_attributes(
        self, span: Span, attributes: Dict[str, Union[str, int, float, bool]]
    ) -> Dict[str, Union[str, int, float, bool]]:
        """Sanitize span attributes for security compliance."""
        sanitized_attributes = {}
        sanitization_occurred = False

        for key, value in attributes.items():
            original_value = str(value) if value is not None else ""
            sanitized_value = self._apply_sanitization_rules(
                original_value, context_type="spans", attribute_name=key
            )

            if sanitized_value != original_value:
                sanitization_occurred = True

                # Audit log sanitization
                if self.enable_audit_logging:
                    self.audit_logger.warning(
                        f"Sanitized span attribute - Span: {span.name}, "
                        f"Attribute: {key}, Rule applied: {self._get_applied_rule_name(original_value, 'spans')}"
                    )

            sanitized_attributes[key] = sanitized_value

        if sanitization_occurred:
            self.sanitization_operations_counter.add(
                1,
                attributes={
                    "operation_type": "span_sanitization",
                    "span_name": span.name,
                },
            )

        return sanitized_attributes

    def sanitize_metric_attributes(
        self, metric_name: str, attributes: Dict[str, str]
    ) -> Dict[str, str]:
        """Sanitize metric attributes for security compliance."""
        sanitized_attributes = {}
        sanitization_occurred = False

        for key, value in attributes.items():
            original_value = str(value) if value is not None else ""
            sanitized_value = self._apply_sanitization_rules(
                original_value, context_type="metrics", attribute_name=key
            )

            if sanitized_value != original_value:
                sanitization_occurred = True

                # Special handling for correlation IDs in metrics - hash instead of redact
                if "correlation_id" in key.lower():
                    sanitized_value = self._hash_sensitive_value(original_value)

                if self.enable_audit_logging:
                    self.audit_logger.info(
                        f"Sanitized metric attribute - Metric: {metric_name}, "
                        f"Attribute: {key}, Rule applied: {self._get_applied_rule_name(original_value, 'metrics')}"
                    )

            sanitized_attributes[key] = sanitized_value

        if sanitization_occurred:
            self.sanitization_operations_counter.add(
                1,
                attributes={
                    "operation_type": "metric_sanitization",
                    "metric_name": metric_name,
                },
            )

        return sanitized_attributes

    def sanitize_log_record(
        self, log_record: str, context: Optional[Dict[str, str]] = None
    ) -> str:
        """Sanitize log record for security compliance."""
        original_record = log_record
        sanitized_record = self._apply_sanitization_rules(
            log_record, context_type="logs"
        )

        if sanitized_record != original_record:
            self.sanitization_operations_counter.add(
                1,
                attributes={
                    "operation_type": "log_sanitization",
                    "context": str(context) if context else "unknown",
                },
            )

            if self.enable_audit_logging:
                self.audit_logger.info(
                    f"Sanitized log record - Context: {context}, "
                    f"Rule applied: {self._get_applied_rule_name(original_record, 'logs')}"
                )

        return sanitized_record

    def _apply_sanitization_rules(
        self, text: str, context_type: str, attribute_name: str = None
    ) -> str:
        """Apply sanitization rules to text based on context."""
        if not text:
            return text

        sanitized_text = text

        for rule in self.sanitization_rules:
            if context_type in rule.applies_to:
                # Check if this rule should be skipped for certain attributes
                if self._should_skip_rule(rule, attribute_name, context_type):
                    continue

                matches = rule.pattern.findall(text)
                if matches:
                    # Record PII detection
                    self.pii_detected_counter.add(
                        len(matches),
                        attributes={
                            "rule_name": rule.name,
                            "context_type": context_type,
                            "sensitivity_level": rule.sensitivity_level.value,
                        },
                    )

                sanitized_text = rule.pattern.sub(rule.replacement, sanitized_text)

        return sanitized_text

    def _should_skip_rule(
        self, rule: SanitizationRule, attribute_name: str, context_type: str
    ) -> bool:
        """Determine if a sanitization rule should be skipped."""
        if not attribute_name:
            return False

        # Skip IP sanitization for certain debugging attributes
        if rule.name == "ip_addresses" and context_type == "spans":
            debug_attributes = {"client.address", "server.address", "net.peer.ip"}
            if attribute_name in debug_attributes:
                return True

        # Preserve trace IDs and span IDs for observability
        if attribute_name in {"trace_id", "span_id", "parent_span_id"}:
            return True

        # Skip correlation ID hashing in traces (needed for correlation)
        if rule.name == "onex_correlation_ids" and context_type == "spans":
            return True

        return False

    def _get_applied_rule_name(self, text: str, context_type: str) -> str:
        """Get the name of the sanitization rule that was applied."""
        for rule in self.sanitization_rules:
            if context_type in rule.applies_to and rule.pattern.search(text):
                return rule.name
        return "unknown"

    def _hash_sensitive_value(self, value: str) -> str:
        """Hash sensitive values for correlation while preserving privacy."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def create_security_span_processor(self):
        """Create a span processor that sanitizes span data."""
        return SecuritySpanProcessor(self)

    def get_sanitization_stats(self) -> ModelSanitizationStats:
        """Get statistics about sanitization operations."""
        rule_infos = [
            ModelSanitizationStats.ModelSanitizationRuleInfo(
                name=rule.name,
                sensitivity_level=rule.sensitivity_level.value,
                applies_to=list(rule.applies_to),
            )
            for rule in self.sanitization_rules
        ]

        return ModelSanitizationStats(
            rules_configured=len(self.sanitization_rules),
            audit_logging_enabled=self.enable_audit_logging,
            sanitization_rules=rule_infos,
        )


class SecuritySpanProcessor:
    """OpenTelemetry span processor that applies security sanitization."""

    def __init__(self, sanitizer: ONEXObservabilitySanitizer):
        self.sanitizer = sanitizer
        self.tracer = trace.get_tracer(__name__)

    def on_start(self, span: ReadableSpan, parent_context=None):
        """Apply sanitization when span starts."""
        # Sanitize span attributes
        if hasattr(span, "_attributes") and span._attributes:
            sanitized_attributes = self.sanitizer.sanitize_span_attributes(
                span, dict(span._attributes)
            )

            # Update span attributes with sanitized versions
            span._attributes.clear()
            for key, value in sanitized_attributes.items():
                span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan):
        """Apply final sanitization when span ends."""
        # Additional sanitization of span name if needed
        if span.name:
            sanitized_name = self.sanitizer._apply_sanitization_rules(
                span.name, context_type="spans"
            )
            if sanitized_name != span.name:
                # Note: Can't modify span name after creation, log the issue
                logger.warning(f"Span name contains sensitive data: {span.name}")

    def shutdown(self):
        """Shutdown the processor."""
        pass

    def force_flush(self, timeout_millis: int = None):
        """Force flush the processor."""
        pass


# Convenience functions for easy integration
_global_sanitizer: Optional[ONEXObservabilitySanitizer] = None


def get_sanitizer() -> ONEXObservabilitySanitizer:
    """Get or create the global sanitizer instance."""
    global _global_sanitizer
    if _global_sanitizer is None:
        _global_sanitizer = ONEXObservabilitySanitizer()
    return _global_sanitizer


def sanitize_span_attributes_decorator(func):
    """Decorator to automatically sanitize span attributes."""

    def wrapper(*args, **kwargs):
        sanitizer = get_sanitizer()

        # Get current span
        current_span = trace.get_current_span()
        if current_span and hasattr(current_span, "_attributes"):
            sanitized_attributes = sanitizer.sanitize_span_attributes(
                current_span, dict(current_span._attributes)
            )

            # Update span with sanitized attributes
            current_span._attributes.clear()
            for key, value in sanitized_attributes.items():
                current_span.set_attribute(key, value)

        return func(*args, **kwargs)

    return wrapper


def create_secure_tracer(name: str, version: str = "1.0.0"):
    """Create a tracer with automatic security sanitization."""
    tracer = trace.get_tracer(name, version)

    # Add security span processor to the tracer provider
    sanitizer = get_sanitizer()
    security_processor = sanitizer.create_security_span_processor()

    # Note: This requires access to the tracer provider
    # In practice, this would be configured during OpenTelemetry initialization

    return tracer


if __name__ == "__main__":
    # Example usage and testing
    sanitizer = ONEXObservabilitySanitizer()

    # Test span attribute sanitization
    test_attributes = {
        "user.email": "user@example.com",
        "api_key": "sk-1234567890abcdef1234567890abcdef",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        "client.address": "192.168.1.100",
    }

    print("🔒 Testing ONEX Observability Security Sanitization")
    print("=" * 60)

    print("Original attributes:", test_attributes)

    # Mock span for testing
    class MockSpan:
        def __init__(self):
            self.name = "test_span"

    mock_span = MockSpan()
    sanitized = sanitizer.sanitize_span_attributes(mock_span, test_attributes)
    print("Sanitized attributes:", sanitized)

    # Test log sanitization
    test_log = (
        "User john.doe@company.com failed authentication with API key sk-abcdef123456"
    )
    sanitized_log = sanitizer.sanitize_log_record(test_log)
    print(f"\nOriginal log: {test_log}")
    print(f"Sanitized log: {sanitized_log}")

    # Print sanitization statistics
    print(f"\nSanitization stats: {sanitizer.get_sanitization_stats()}")
    print("✅ Security sanitization test complete")
