"""Runtime Policy Enforcement Utility for ONEX Security Compliance.

This utility provides runtime enforcement of logging and security policies,
ensuring sensitive data is never logged and security patterns are followed.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.utils.policy.utility_policy_loader import (
    get_coding_standards_policy, get_logging_policy)

logger = logging.getLogger(__name__)


@dataclass
class SecurityViolation:
    """Represents a security policy violation."""

    violation_type: str
    field_name: str
    original_value: str
    suggested_action: str
    severity: str  # critical, high, medium, low


class UtilityRuntimePolicyEnforcement:
    """Utility for runtime enforcement of ONEX security and logging policies."""

    def __init__(self):
        """Initialize runtime policy enforcement."""
        self._compiled_patterns: Optional[Dict[str, re.Pattern]] = None
        self._policy_cache_valid = False

    def _ensure_patterns_compiled(self) -> None:
        """Ensure security patterns are compiled for performance."""
        if self._compiled_patterns is not None and self._policy_cache_valid:
            return

        try:
            policy = get_logging_policy()
            self._compiled_patterns = {}

            # Compile never_log patterns
            for pattern in policy.logging_policy.security.never_log:
                pattern_key = f"never_log_{pattern}"
                # Create case-insensitive pattern for field names
                self._compiled_patterns[pattern_key] = re.compile(
                    rf"\b{re.escape(pattern)}\b", re.IGNORECASE
                )

            # Compile sanitize_patterns
            for pattern in policy.logging_policy.security.sanitize_patterns:
                pattern_key = f"sanitize_{pattern}"
                # Match patterns like "password=", "token:", etc.
                self._compiled_patterns[pattern_key] = re.compile(
                    pattern.replace("=", r"\s*[=:]\s*[^\s,}]+"), re.IGNORECASE
                )

            # Compile PII patterns
            for (
                pii_type,
                pattern,
            ) in policy.logging_policy.security.pii_detection.items():
                pattern_key = f"pii_{pii_type}"
                self._compiled_patterns[pattern_key] = re.compile(
                    pattern, re.IGNORECASE
                )

            self._policy_cache_valid = True

        except Exception as e:
            logger.error(
                "Failed to compile security patterns",
                extra={"error": str(e), "operation": "compile_patterns"},
                exc_info=True,
            )
            self._compiled_patterns = {}

    def sanitize_log_data(
        self, data: Union[str, Dict, List], context: str = "unknown"
    ) -> Tuple[Union[str, Dict, List], List[SecurityViolation]]:
        """Sanitize data before logging to remove sensitive information.

        Args:
            data: Data to sanitize (string, dict, or list)
            context: Context where this data will be logged

        Returns:
            Tuple of (sanitized_data, violations_found)
        """
        self._ensure_patterns_compiled()
        violations: List[SecurityViolation] = []

        if isinstance(data, str):
            sanitized, str_violations = self._sanitize_string(data, context)
            violations.extend(str_violations)
            return sanitized, violations

        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized_key, key_violations = self._sanitize_field_name(key, context)
                violations.extend(key_violations)

                sanitized_value, value_violations = self.sanitize_log_data(
                    value, f"{context}.{key}"
                )
                violations.extend(value_violations)

                sanitized[sanitized_key] = sanitized_value
            return sanitized, violations

        elif isinstance(data, list):
            sanitized = []
            for i, item in enumerate(data):
                sanitized_item, item_violations = self.sanitize_log_data(
                    item, f"{context}[{i}]"
                )
                violations.extend(item_violations)
                sanitized.append(sanitized_item)
            return sanitized, violations

        else:
            # For other types (int, float, bool, None), return as-is
            return data, violations

    def _sanitize_string(
        self, text: str, context: str
    ) -> Tuple[str, List[SecurityViolation]]:
        """Sanitize a string by removing sensitive patterns."""
        violations: List[SecurityViolation] = []
        sanitized = text

        if not self._compiled_patterns:
            return sanitized, violations

        # Apply sanitize patterns (e.g., password=value -> password=[REDACTED])
        for pattern_name, compiled_pattern in self._compiled_patterns.items():
            if pattern_name.startswith("sanitize_"):
                matches = compiled_pattern.findall(sanitized)
                if matches:
                    violation = SecurityViolation(
                        violation_type="sensitive_data_pattern",
                        field_name=context,
                        original_value=f"Found {len(matches)} sensitive patterns",
                        suggested_action="Sanitized with [REDACTED]",
                        severity="high",
                    )
                    violations.append(violation)

                    sanitized = compiled_pattern.sub("[REDACTED]", sanitized)

        # Detect PII patterns
        for pattern_name, compiled_pattern in self._compiled_patterns.items():
            if pattern_name.startswith("pii_"):
                matches = compiled_pattern.findall(sanitized)
                if matches:
                    pii_type = pattern_name.replace("pii_", "")
                    violation = SecurityViolation(
                        violation_type="pii_detected",
                        field_name=context,
                        original_value=f"Detected {pii_type} pattern",
                        suggested_action="Consider removing PII from logs",
                        severity="critical",
                    )
                    violations.append(violation)

                    # Replace PII with generic placeholder
                    sanitized = compiled_pattern.sub(
                        f"[{pii_type.upper()}_REDACTED]", sanitized
                    )

        return sanitized, violations

    def _sanitize_field_name(
        self, field_name: str, context: str
    ) -> Tuple[str, List[SecurityViolation]]:
        """Check if a field name contains sensitive information."""
        violations: List[SecurityViolation] = []

        if not self._compiled_patterns:
            return field_name, violations

        # Check if field name matches never_log patterns
        for pattern_name, compiled_pattern in self._compiled_patterns.items():
            if pattern_name.startswith("never_log_"):
                if compiled_pattern.search(field_name):
                    violation = SecurityViolation(
                        violation_type="sensitive_field_name",
                        field_name=f"{context}.{field_name}",
                        original_value=field_name,
                        suggested_action="Field should not be logged",
                        severity="critical",
                    )
                    violations.append(violation)
                    # Return redacted field name
                    return "[SENSITIVE_FIELD]", violations

        return field_name, violations

    def validate_log_entry(
        self,
        log_data: Dict[str, Union[str, int, float, bool, List, Dict]],
        subsystem: str = "default",
    ) -> Tuple[bool, List[SecurityViolation]]:
        """Validate a log entry against security policies.

        Args:
            log_data: Log data to validate
            subsystem: Subsystem name for context

        Returns:
            Tuple of (is_safe_to_log, violations_found)
        """
        violations: List[SecurityViolation] = []

        # Sanitize the entire log entry
        sanitized_data, sanitize_violations = self.sanitize_log_data(
            log_data, subsystem
        )
        violations.extend(sanitize_violations)

        # Check for critical violations that should block logging
        critical_violations = [v for v in violations if v.severity == "critical"]

        if critical_violations:
            logger.warning(
                "Critical security violations found in log data",
                extra={
                    "subsystem": subsystem,
                    "critical_violations": len(critical_violations),
                    "total_violations": len(violations),
                },
            )
            return False, violations

        return True, violations

    def get_safe_log_data(
        self,
        log_data: Dict[str, Union[str, int, float, bool, List, Dict]],
        subsystem: str = "default",
    ) -> Dict[str, Union[str, int, float, bool, List, Dict]]:
        """Get sanitized version of log data that's safe to log.

        Args:
            log_data: Original log data
            subsystem: Subsystem name for context

        Returns:
            Sanitized log data safe for logging
        """
        sanitized_data, violations = self.sanitize_log_data(log_data, subsystem)

        if violations:
            logger.debug(
                "Log data sanitized",
                extra={
                    "subsystem": subsystem,
                    "violations_found": len(violations),
                    "violation_types": list(set(v.violation_type for v in violations)),
                },
            )

        # Ensure sanitized_data is a dict
        if isinstance(sanitized_data, dict):
            return sanitized_data
        else:
            return {"sanitized_content": sanitized_data}

    def enforce_coding_standards(
        self, code_content: str, file_path: Path
    ) -> List[SecurityViolation]:
        """Enforce coding standards on code content.

        Args:
            code_content: Code content to check
            file_path: Path to the code file

        Returns:
            List of coding standard violations
        """
        violations: List[SecurityViolation] = []

        try:
            policy = get_coding_standards_policy()

            # Check for prohibited types
            for prohibited_type in policy.coding_standards_policy.prohibited_types:
                if prohibited_type in code_content:
                    violation = SecurityViolation(
                        violation_type="prohibited_type",
                        field_name=str(file_path),
                        original_value=f"Found prohibited type: {prohibited_type}",
                        suggested_action=f"Replace {prohibited_type} with specific types",
                        severity="critical",
                    )
                    violations.append(violation)

            # Check for magic strings in imports
            import_lines = [
                line.strip()
                for line in code_content.split("\n")
                if line.strip().startswith("import") or line.strip().startswith("from")
            ]
            for line in import_lines:
                # Look for string literals in imports that aren't standard patterns
                if '"' in line or "'" in line:
                    # Skip standard patterns like 'from typing import ...'
                    if not any(
                        pattern in line
                        for pattern in ["from typing", "import typing", "__future__"]
                    ):
                        violation = SecurityViolation(
                            violation_type="potential_magic_string",
                            field_name=str(file_path),
                            original_value=line,
                            suggested_action="Consider using enums or constants",
                            severity="medium",
                        )
                        violations.append(violation)

            return violations

        except Exception as e:
            logger.error(
                "Failed to enforce coding standards",
                extra={"file_path": str(file_path), "error": str(e)},
                exc_info=True,
            )
            return violations

    def create_secure_logger(
        self, name: str, subsystem: str = "default"
    ) -> logging.Logger:
        """Create a logger with automatic security policy enforcement.

        Args:
            name: Logger name
            subsystem: Subsystem name for policy context

        Returns:
            Logger with security enforcement
        """
        # Get base logger
        secure_logger = logging.getLogger(name)

        # Add custom handler that enforces security policies
        if not any(
            isinstance(handler, SecurePolicyHandler)
            for handler in secure_logger.handlers
        ):
            security_handler = SecurePolicyHandler(self, subsystem)
            secure_logger.addHandler(security_handler)

        return secure_logger

    def clear_cache(self):
        """Clear compiled pattern cache to force reload."""
        self._compiled_patterns = None
        self._policy_cache_valid = False


class SecurePolicyHandler(logging.Handler):
    """Logging handler that enforces security policies."""

    def __init__(self, enforcement: UtilityRuntimePolicyEnforcement, subsystem: str):
        """Initialize security policy handler."""
        super().__init__()
        self.enforcement = enforcement
        self.subsystem = subsystem

    def emit(self, record: logging.LogRecord):
        """Process log record through security enforcement."""
        try:
            # Extract extra fields for security validation
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]:
                    extra_data[key] = value

            # Validate log data
            is_safe, violations = self.enforcement.validate_log_entry(
                extra_data, self.subsystem
            )

            if not is_safe:
                # Block logging for critical security violations
                blocked_logger = logging.getLogger(f"{record.name}.security_blocked")
                blocked_logger.warning(
                    f"Log entry blocked due to security violations",
                    extra={
                        "original_logger": record.name,
                        "violations_count": len(violations),
                        "subsystem": self.subsystem,
                    },
                )
                return

            # Sanitize the extra data
            safe_data = self.enforcement.get_safe_log_data(extra_data, self.subsystem)

            # Update record with sanitized data
            for key, value in safe_data.items():
                setattr(record, key, value)

            # Continue with normal logging

        except Exception as e:
            # Don't break logging if security enforcement fails
            error_logger = logging.getLogger(f"{record.name}.security_error")
            error_logger.error(f"Security enforcement error: {e}", exc_info=True)


# Global instance for easy access
runtime_enforcer = UtilityRuntimePolicyEnforcement()


def sanitize_for_logging(
    data: Union[str, Dict, List], context: str = "log"
) -> Union[str, Dict, List]:
    """Convenience function to sanitize data for logging.

    Args:
        data: Data to sanitize
        context: Context for sanitization

    Returns:
        Sanitized data safe for logging
    """
    sanitized, violations = runtime_enforcer.sanitize_log_data(data, context)
    return sanitized


def create_secure_logger(name: str, subsystem: str = "default") -> logging.Logger:
    """Convenience function to create a security-enforced logger.

    Args:
        name: Logger name
        subsystem: Subsystem name

    Returns:
        Logger with automatic security enforcement
    """
    return runtime_enforcer.create_secure_logger(name, subsystem)


def validate_code_security(
    code_content: str, file_path: Path
) -> List[SecurityViolation]:
    """Convenience function to validate code against security standards.

    Args:
        code_content: Code content to validate
        file_path: Path to the code file

    Returns:
        List of security violations found
    """
    return runtime_enforcer.enforce_coding_standards(code_content, file_path)
