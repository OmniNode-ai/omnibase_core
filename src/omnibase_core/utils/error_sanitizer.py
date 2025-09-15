"""
Error sanitization utility for preventing sensitive information leakage.

This module provides the ErrorSanitizer class that removes or masks sensitive
information from error messages and stack traces to prevent accidental exposure
of credentials, file paths, and other sensitive data in logs and error reports.

Author: ONEX Framework Team
"""

import contextlib
import re
from pathlib import Path
from typing import Any, ClassVar

from omnibase_core.core.errors.core_errors import OnexError

# Constants for magic numbers
_MIN_GROUPS_FOR_PREFIX_PRESERVATION = 2
_CONNECTION_STRING_GROUPS = 3
_BEARER_PATTERN_GROUPS = 2


class ErrorSanitizer:
    """
    Utility class for sanitizing error messages and stack traces to prevent
    sensitive information leakage in logs and error reports.

    Provides comprehensive sanitization patterns for common sensitive data types
    including credentials, file paths, database connection strings, and API keys.
    """

    # Default sensitive patterns to remove or mask
    DEFAULT_SENSITIVE_PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        # Password patterns
        "password": re.compile(r"(password\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        "pwd": re.compile(r"(pwd\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        "passwd": re.compile(r"(passwd\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        # API keys and tokens
        "api_key": re.compile(r"(api[_-]?key\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        "token": re.compile(r"(token\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        "secret": re.compile(r"(secret\s*[=:]\s*)([^\s&,;]+)", re.IGNORECASE),
        "bearer": re.compile(r"(bearer\s+)([^\s]+)", re.IGNORECASE),
        # Database connection strings
        "connection_string": re.compile(
            r"((?:postgresql|mysql|mongodb)://[^:]+:)([^@]+)(@)",
            re.IGNORECASE,
        ),
        # AWS credentials (more specific patterns)
        "aws_access_key": re.compile(r"(AKIA[0-9A-Z]{16})"),
        # More specific AWS secret pattern
        "aws_secret": re.compile(r"\b([A-Za-z0-9/+=]{40})\b(?=\s|$|[&,;])"),
        # File paths (home directories)
        "home_path": re.compile(r"(/(?:home|Users)/[^/\s]+)"),
        # IP addresses (optionally sensitive)
        "ip_address": re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"),
    }

    def __init__(
        self,
        mask_character: str = "*",
        mask_length: int = 8,
        *,
        preserve_prefixes: bool = True,
        custom_patterns: dict[str, re.Pattern] | None = None,
        skip_patterns: set[str] | None = None,
    ):
        """
        Initialize the ErrorSanitizer with configuration options.

        Args:
            mask_character: Character to use for masking sensitive values
            mask_length: Length of mask to use for replacement
            preserve_prefixes: Whether to preserve prefixes (e.g., "password=***")
            custom_patterns: Additional regex patterns for sanitization
            skip_patterns: Pattern names to skip from default patterns
        """
        self.mask_character = mask_character
        self.mask_length = mask_length
        self.preserve_prefixes = preserve_prefixes

        # Build active patterns
        self.patterns = self.DEFAULT_SENSITIVE_PATTERNS.copy()

        # Add custom patterns if provided
        if custom_patterns:
            self.patterns.update(custom_patterns)

        # Remove skipped patterns
        if skip_patterns:
            for pattern_name in skip_patterns:
                self.patterns.pop(pattern_name, None)

        # Pre-compile combined pattern for faster initial screening
        self._sensitive_keywords = {
            "password",
            "pwd",
            "passwd",
            "api_key",
            "token",
            "secret",
            "bearer",
            "AKIA",
            "postgresql://",
            "mysql://",
            "mongodb://",
            "/home/",
            "/Users/",
        }

        # Cache for message sanitization (simple dict-based cache)
        self._cache_size = 1000  # Reasonable cache size for message patterns
        self._sanitization_cache: dict[str, str] = {}

    def sanitize_message(self, message: str) -> str:
        """
        Sanitize an error message by masking sensitive information.

        Args:
            message: The error message to sanitize

        Returns:
            Sanitized error message with sensitive information masked
        """
        if not isinstance(message, str):
            return str(message)

        # Fast path: check if message contains any sensitive keywords
        if not self._contains_sensitive_keywords(message):
            return message

        # Use cached sanitization for performance
        return self._sanitize_message_cached(message)

    def _sanitize_message_cached(self, message: str) -> str:
        """
        Cached version of message sanitization for better performance.

        Args:
            message: The error message to sanitize

        Returns:
            Sanitized error message with sensitive information masked
        """
        # Check cache first
        if message in self._sanitization_cache:
            return self._sanitization_cache[message]

        sanitized = message

        for pattern_name, pattern in self.patterns.items():
            if pattern_name in {"connection_string", "bearer"}:
                # Special handling for these patterns
                sanitized = self._mask_with_groups(sanitized, pattern)
            else:
                sanitized = self._mask_pattern(sanitized, pattern)

        # Cache the result (with simple size limit)
        if len(self._sanitization_cache) >= self._cache_size:
            # Clear cache when it gets too large
            self._sanitization_cache.clear()
        self._sanitization_cache[message] = sanitized

        return sanitized

    def get_cache_info(self) -> dict[str, int]:
        """
        Get cache information for testing and monitoring.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "hits": len(self._sanitization_cache),
            "misses": 0,  # Simple implementation doesn't track misses
            "maxsize": self._cache_size,
            "currsize": len(self._sanitization_cache),
        }

    def _contains_sensitive_keywords(self, message: str) -> bool:
        """
        Fast check if message contains any sensitive keywords.

        Args:
            message: Message to check

        Returns:
            True if message might contain sensitive information
        """
        message_lower = message.lower()
        return any(
            keyword.lower() in message_lower for keyword in self._sensitive_keywords
        )

    def sanitize_exception(self, exception: Exception) -> Exception:
        """
        Sanitize an exception by creating a new exception with sanitized message.

        Args:
            exception: The exception to sanitize

        Returns:
            New exception instance with sanitized message
        """
        sanitized_message = self.sanitize_message(str(exception))

        # Create new exception of same type with sanitized message
        exception_type = type(exception)

        try:
            # Try to create new exception with sanitized message
            sanitized_exception = exception_type(sanitized_message)

            # Preserve original attributes if possible
            if hasattr(exception, "__dict__"):
                for key, value in exception.__dict__.items():
                    if key not in {
                        "args",
                    }:  # Don't copy args as we're replacing the message
                        with contextlib.suppress(AttributeError, TypeError):
                            setattr(sanitized_exception, key, value)

        except (TypeError, ValueError):
            # If we can't create the same exception type, create a generic Exception
            return Exception(sanitized_message)
        else:
            return sanitized_exception

    def sanitize_onex_error(self, error: OnexError) -> OnexError:
        """
        Sanitize an OnexError by creating a new instance with sanitized message and
        context.

        Args:
            error: The OnexError to sanitize

        Returns:
            New OnexError instance with sanitized data
        """
        # Sanitize the main message
        sanitized_message = self.sanitize_message(error.message)

        # Sanitize context values
        sanitized_context = {}
        for key, value in error.context.items():
            if isinstance(value, str):
                sanitized_context[key] = self.sanitize_message(value)
            else:
                sanitized_context[key] = value

        # Create new sanitized OnexError
        return OnexError(
            message=sanitized_message,
            error_code=error.error_code,
            status=error.status,
            correlation_id=error.correlation_id,
            timestamp=error.timestamp,
            **sanitized_context,
        )

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize a dictionary by recursively sanitizing string values.

        Args:
            data: Dictionary to sanitize

        Returns:
            New dictionary with sanitized values
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_message(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value)
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_list(self, data: list[Any]) -> list[Any]:
        """
        Sanitize a list by recursively sanitizing elements.

        Args:
            data: List to sanitize

        Returns:
            New list with sanitized elements
        """
        sanitized = []

        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_message(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item))
            else:
                sanitized.append(item)

        return sanitized

    def sanitize_file_path(self, file_path: str | Path) -> str:
        """
        Sanitize a file path by masking sensitive directory components.

        Args:
            file_path: File path to sanitize

        Returns:
            Sanitized file path string
        """
        path_str = str(file_path)

        # Mask home directory paths
        home_pattern = re.compile(r"(/(?:home|Users)/[^/\s]+)")
        return home_pattern.sub(f"/home/{self.mask_character * 6}", path_str)

    def _mask_pattern(self, text: str, pattern: re.Pattern) -> str:
        """
        Mask sensitive content using a regex pattern.

        Args:
            text: Text to sanitize
            pattern: Regex pattern to match

        Returns:
            Text with matches masked
        """
        mask = self.mask_character * self.mask_length

        if (
            self.preserve_prefixes
            and pattern.groups >= _MIN_GROUPS_FOR_PREFIX_PRESERVATION
        ):
            # Replace only the sensitive part, preserve prefix
            def replacer(match):
                if len(match.groups()) >= _MIN_GROUPS_FOR_PREFIX_PRESERVATION:
                    return match.group(1) + mask
                return mask

            return pattern.sub(replacer, text)
        return pattern.sub(mask, text)

    def _mask_with_groups(self, text: str, pattern: re.Pattern) -> str:
        """
        Mask sensitive content while preserving specific groups.

        Args:
            text: Text to sanitize
            pattern: Regex pattern with groups

        Returns:
            Text with sensitive groups masked
        """
        mask = self.mask_character * self.mask_length

        def replacer(match):
            groups = match.groups()
            if len(groups) == _CONNECTION_STRING_GROUPS:  # connection_string pattern
                return groups[0] + mask + groups[2]
            if len(groups) == _BEARER_PATTERN_GROUPS:  # bearer pattern
                return groups[0] + mask
            return mask

        return pattern.sub(replacer, text)

    @classmethod
    def create_default(cls) -> "ErrorSanitizer":
        """
        Create an ErrorSanitizer with default configuration.

        Returns:
            ErrorSanitizer instance with default settings
        """
        return cls()

    @classmethod
    def create_strict(cls) -> "ErrorSanitizer":
        """
        Create an ErrorSanitizer with strict sanitization (including IP addresses).

        Returns:
            ErrorSanitizer instance with strict settings
        """
        return cls(skip_patterns=None)  # Include all patterns including IP addresses

    @classmethod
    def create_lenient(cls) -> "ErrorSanitizer":
        """
        Create an ErrorSanitizer that skips IP address masking.

        Returns:
            ErrorSanitizer instance with lenient settings
        """
        return cls(skip_patterns={"ip_address"})


# Global default instance for convenience
default_sanitizer = ErrorSanitizer.create_default()


def sanitize_error_message(message: str) -> str:
    """
    Convenience function to sanitize an error message using default settings.

    Args:
        message: Error message to sanitize

    Returns:
        Sanitized error message
    """
    return default_sanitizer.sanitize_message(message)


def sanitize_exception(exception: Exception) -> Exception:
    """
    Convenience function to sanitize an exception using default settings.

    Args:
        exception: Exception to sanitize

    Returns:
        Sanitized exception
    """
    return default_sanitizer.sanitize_exception(exception)


def sanitize_onex_error(error: OnexError) -> OnexError:
    """
    Convenience function to sanitize an OnexError using default settings.

    Args:
        error: OnexError to sanitize

    Returns:
        Sanitized OnexError
    """
    return default_sanitizer.sanitize_onex_error(error)
