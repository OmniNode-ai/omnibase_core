"""
Sensitive Data Sanitizer for ONEX Memory System

Provides utilities to detect and sanitize sensitive information before storage.
"""

import logging
import re
from typing import List, Optional, Tuple

from omnibase_core.utils.security.models.model_sanitization_result import \
    ModelSanitizationResult

logger = logging.getLogger(__name__)


class SensitiveDataSanitizer:
    """Sanitize sensitive data from text before storage."""

    # Common patterns for sensitive data
    PATTERNS = {
        "api_key": [
            (
                r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]{6,}["\']?',
                "[API_KEY_REDACTED]",
            ),
            (
                r'["\']?apikey["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]{6,}["\']?',
                "[API_KEY_REDACTED]",
            ),
            (r"sk-[A-Za-z0-9_\-]{6,}", "[OPENAI_KEY_REDACTED]"),
        ],
        "token": [
            (
                r'["\']?auth[_-]?token["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{6,}["\']?',
                "[AUTH_TOKEN_REDACTED]",
            ),
            (
                r'["\']?token["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{6,}["\']?',
                "[TOKEN_REDACTED]",
            ),
            (r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [TOKEN_REDACTED]"),
        ],
        "password": [
            (
                r'["\']?password["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                "[PASSWORD_REDACTED]",
            ),
            (
                r'["\']?passwd["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                "[PASSWORD_REDACTED]",
            ),
            (
                r'["\']?pwd["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                "[PASSWORD_REDACTED]",
            ),
        ],
        "secret": [
            (
                r'["\']?client[_-]?secret["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]+["\']?',
                "[CLIENT_SECRET_REDACTED]",
            ),
            (
                r'["\']?secret["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-]+["\']?',
                "[SECRET_REDACTED]",
            ),
        ],
        "credit_card": [
            (
                r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b",
                "[CREDIT_CARD_REDACTED]",
            ),
        ],
        "ssn": [
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
            (r"\b\d{9}\b", "[SSN_REDACTED]"),
        ],
        "email": [
            # Only redact emails that look like personal emails (not system/service emails)
            (
                r"\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|hotmail|outlook|icloud|protonmail)\.(?:com|net|org)\b",
                "[PERSONAL_EMAIL_REDACTED]",
            ),
        ],
        "private_key": [
            (
                r"-----BEGIN (?:RSA |EC |)PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |)PRIVATE KEY-----",
                "[PRIVATE_KEY_REDACTED]",
            ),
            (
                r"-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]+?-----END OPENSSH PRIVATE KEY-----",
                "[SSH_PRIVATE_KEY_REDACTED]",
            ),
        ],
        "aws": [
            (r"AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY_REDACTED]"),
            (
                r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
                "[AWS_SECRET_KEY_REDACTED]",
            ),
        ],
        "database_url": [
            (
                r"(?:mongodb|postgres|postgresql|mysql|redis|sqlite):\/\/[^\s]+",
                "[DATABASE_URL_REDACTED]",
            ),
        ],
    }

    def __init__(self, custom_patterns: Optional[List[Tuple[str, str]]] = None):
        """
        Initialize the sanitizer.

        Args:
            custom_patterns: Additional patterns to check as (regex, replacement) tuples
        """
        self.custom_patterns = custom_patterns or []
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, List[Tuple[re.Pattern, str]]]:
        """Compile regex patterns for efficiency."""
        compiled = {}
        for category, patterns in self.PATTERNS.items():
            compiled[category] = [
                (re.compile(pattern, re.IGNORECASE), replacement)
                for pattern, replacement in patterns
            ]
        return compiled

    def sanitize(self, text: str, max_length: int = 10000) -> ModelSanitizationResult:
        """
        Sanitize sensitive information from text.

        Args:
            text: The text to sanitize
            max_length: Maximum length to process (for safety)

        Returns:
            ModelSanitizationResult with sanitized text and metadata
        """
        if not text:
            return ModelSanitizationResult(
                original_length=0,
                sanitized_length=0,
                sensitive_patterns_found=[],
                replacements_made=0,
                sanitized_text="",
            )

        # Truncate if necessary
        original_length = len(text)
        if original_length > max_length:
            text = text[:max_length]
            logger.warning(
                f"Text truncated from {original_length} to {max_length} characters"
            )

        sanitized_text = text
        patterns_found = set()
        total_replacements = 0

        # Apply built-in patterns
        for category, patterns in self.compiled_patterns.items():
            for pattern, replacement in patterns:
                matches = pattern.findall(sanitized_text)
                if matches:
                    patterns_found.add(category)
                    # Count replacements
                    count = len(matches)
                    total_replacements += count
                    # Replace all occurrences
                    sanitized_text = pattern.sub(replacement, sanitized_text)

        # Apply custom patterns
        for pattern_str, replacement in self.custom_patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                matches = pattern.findall(sanitized_text)
                if matches:
                    patterns_found.add("custom")
                    total_replacements += len(matches)
                    sanitized_text = pattern.sub(replacement, sanitized_text)
            except re.error as e:
                logger.error(f"Invalid custom regex pattern: {pattern_str} - {e}")

        return ModelSanitizationResult(
            original_length=original_length,
            sanitized_length=len(sanitized_text),
            sensitive_patterns_found=list(patterns_found),
            replacements_made=total_replacements,
            sanitized_text=sanitized_text,
        )

    def contains_sensitive_data(self, text: str) -> bool:
        """
        Quick check if text contains any sensitive data.

        Args:
            text: The text to check

        Returns:
            True if sensitive data is found
        """
        if not text:
            return False

        # Check built-in patterns
        for patterns in self.compiled_patterns.values():
            for pattern, _ in patterns:
                if pattern.search(text):
                    return True

        # Check custom patterns
        for pattern_str, _ in self.custom_patterns:
            try:
                if re.search(pattern_str, text, re.IGNORECASE):
                    return True
            except re.error:
                continue

        return False

    def get_safe_preview(self, text: str, max_length: int = 100) -> str:
        """
        Get a safe preview of text for logging.

        Args:
            text: The text to preview
            max_length: Maximum preview length

        Returns:
            Safe preview text
        """
        if not text:
            return ""

        # First sanitize
        result = self.sanitize(
            text[: max_length * 2]
        )  # Get more to account for replacements
        preview = result.sanitized_text[:max_length]

        if len(result.sanitized_text) > max_length:
            preview += "..."

        return preview


# Global instance for convenience
_default_sanitizer = SensitiveDataSanitizer()


def sanitize_text(text: str, max_length: int = 10000) -> ModelSanitizationResult:
    """Convenience function to sanitize text using default sanitizer."""
    return _default_sanitizer.sanitize(text, max_length)


def contains_sensitive_data(text: str) -> bool:
    """Convenience function to check for sensitive data."""
    return _default_sanitizer.contains_sensitive_data(text)


def get_safe_preview(text: str, max_length: int = 100) -> str:
    """Convenience function to get safe preview."""
    return _default_sanitizer.get_safe_preview(text, max_length)
