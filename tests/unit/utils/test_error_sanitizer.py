#!/usr/bin/env python3
"""
Unit tests for ErrorSanitizer.

Tests error message sanitization, performance optimizations, and pattern matching
for sensitive information masking.
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.utils.error_sanitizer import (
    ErrorSanitizer,
    default_sanitizer,
    sanitize_error_message,
    sanitize_exception,
    sanitize_onex_error,
)


class TestErrorSanitizer:
    """Test suite for ErrorSanitizer."""

    def test_basic_initialization(self):
        """Test basic sanitizer initialization."""
        sanitizer = ErrorSanitizer()

        assert sanitizer.mask_character == "*"
        assert sanitizer.mask_length == 8
        assert sanitizer.preserve_prefixes is True
        assert len(sanitizer.patterns) > 0
        assert len(sanitizer._sensitive_keywords) > 0

    def test_custom_initialization(self):
        """Test sanitizer with custom configuration."""
        custom_patterns = {"custom_pattern": re.compile(r"(CUSTOM)([A-Z]+)")}

        sanitizer = ErrorSanitizer(
            mask_character="X",
            mask_length=12,
            preserve_prefixes=False,
            custom_patterns=custom_patterns,
            skip_patterns={"ip_address"},
        )

        assert sanitizer.mask_character == "X"
        assert sanitizer.mask_length == 12
        assert sanitizer.preserve_prefixes is False
        assert "custom_pattern" in sanitizer.patterns
        assert "ip_address" not in sanitizer.patterns

    def test_password_sanitization(self):
        """Test password pattern sanitization."""
        sanitizer = ErrorSanitizer()

        test_cases = [
            ("password=secret123", "password=********"),
            ("pwd=mypassword", "pwd=********"),
            ("passwd=topsecret", "passwd=********"),
            ("PASSWORD=UPPERCASE", "password=********"),  # Case insensitive
        ]

        for original, expected in test_cases:
            result = sanitizer.sanitize_message(original)
            assert result == expected

    def test_api_key_sanitization(self):
        """Test API key and token sanitization."""
        sanitizer = ErrorSanitizer()

        test_cases = [
            ("api_key=abc123def456", "api_key=********"),
            ("api-key=secret", "api-key=********"),
            ("token=bearer123", "token=********"),
            ("secret=confidential", "secret=********"),
            ("Authorization: Bearer xyz789", "Authorization: Bearer ********"),
        ]

        for original, expected in test_cases:
            result = sanitizer.sanitize_message(original)
            assert result == expected

    def test_aws_credentials_sanitization(self):
        """Test AWS credentials sanitization."""
        sanitizer = ErrorSanitizer()

        # AWS Access Key (starts with AKIA)
        message = "AWS access key: AKIA1234567890123456"
        result = sanitizer.sanitize_message(message)
        assert "AKIA1234567890123456" not in result
        assert "********" in result

        # AWS Secret Key (more specific pattern now)
        message = "AWS secret: abcd1234EFGH5678ijkl9012MNOP3456qrst7890 end"
        result = sanitizer.sanitize_message(message)
        assert "abcd1234EFGH5678ijkl9012MNOP3456qrst7890" not in result

        # Should NOT match legitimate base64 that's not in AWS context
        message = "This is just base64: dGVzdA=="
        result = sanitizer.sanitize_message(message)
        # Short base64 should not be masked
        assert "dGVzdA==" in result

    def test_database_connection_string_sanitization(self):
        """Test database connection string sanitization."""
        sanitizer = ErrorSanitizer()

        test_cases = [
            (
                "postgresql://user:password@localhost/db",
                "postgresql://user:********@localhost/db",
            ),
            (
                "mysql://admin:secret123@server:3306/database",
                "mysql://admin:********@server:3306/database",
            ),
            (
                "mongodb://user:complex_pass@mongo.example.com/db",
                "mongodb://user:********@mongo.example.com/db",
            ),
        ]

        for original, expected in test_cases:
            result = sanitizer.sanitize_message(original)
            assert result == expected

    def test_file_path_sanitization(self):
        """Test file path sanitization."""
        sanitizer = ErrorSanitizer()

        test_cases = [
            (
                "File not found: /home/user/secret.txt",
                "File not found: /home/******/secret.txt",
            ),
            (
                "Path: /Users/john/documents/file.pdf",
                "Path: /home/******/documents/file.pdf",
            ),
        ]

        for original, expected in test_cases:
            result = sanitizer.sanitize_message(original)
            assert result == expected

    def test_ip_address_sanitization(self):
        """Test IP address sanitization (when enabled)."""
        # Default sanitizer includes IP sanitization
        sanitizer = ErrorSanitizer()

        message = "Connection failed to 192.168.1.100"
        result = sanitizer.sanitize_message(message)
        assert "192.168.1.100" not in result
        assert "********" in result

        # Lenient sanitizer skips IP addresses
        lenient_sanitizer = ErrorSanitizer.create_lenient()
        result = lenient_sanitizer.sanitize_message(message)
        assert "192.168.1.100" in result

    def test_performance_fast_path(self):
        """Test performance optimization fast path."""
        sanitizer = ErrorSanitizer()

        # Message without sensitive keywords should return quickly
        clean_message = "This is a completely clean error message with no secrets"
        result = sanitizer.sanitize_message(clean_message)
        assert result == clean_message

        # Verify _contains_sensitive_keywords works correctly
        assert not sanitizer._contains_sensitive_keywords(clean_message)
        assert sanitizer._contains_sensitive_keywords("password=secret")
        assert sanitizer._contains_sensitive_keywords("AKIA123456789")

    def test_caching_behavior(self):
        """Test that caching improves performance for repeated messages."""
        sanitizer = ErrorSanitizer()

        message = "password=secret123"

        # First call should cache the result
        result1 = sanitizer.sanitize_message(message)

        # Second call should use cache
        result2 = sanitizer.sanitize_message(message)

        assert result1 == result2
        assert result1 == "password=********"

        # Verify cache is being used by checking cache info
        cache_info = sanitizer.get_cache_info()
        assert cache_info["currsize"] > 0

    def test_sanitize_exception(self):
        """Test exception sanitization."""
        sanitizer = ErrorSanitizer()

        # Test with regular exception
        original_exception = ValueError("Connection failed with password=secret123")
        sanitized_exception = sanitizer.sanitize_exception(original_exception)

        assert isinstance(sanitized_exception, ValueError)
        assert "password=********" in str(sanitized_exception)
        assert "secret123" not in str(sanitized_exception)

    def test_sanitize_onex_error(self):
        """Test OnexError sanitization."""
        sanitizer = ErrorSanitizer()

        original_error = OnexError(
            message="Database connection failed with password=secret123",
            error_code=CoreErrorCode.OPERATION_FAILED,
            context={
                "connection_string": "postgresql://user:password@localhost/db",
                "retry_count": 3,
            },
        )

        sanitized_error = sanitizer.sanitize_onex_error(original_error)

        assert isinstance(sanitized_error, OnexError)
        assert sanitized_error.error_code == CoreErrorCode.OPERATION_FAILED
        assert "password=********" in sanitized_error.message
        assert "secret123" not in sanitized_error.message
        assert "postgresql://user:********@localhost/db" in str(
            sanitized_error.context["connection_string"]
        )
        assert (
            sanitized_error.context["retry_count"] == 3
        )  # Non-string values preserved

    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        sanitizer = ErrorSanitizer()

        test_dict = {
            "clean_key": "clean_value",
            "sensitive_key": "password=secret123",
            "nested": {"connection": "mysql://user:password@server/db", "timeout": 30},
            "list_data": ["clean", "api_key=sensitive", "also_clean"],
        }

        sanitized = sanitizer.sanitize_dict(test_dict)

        assert sanitized["clean_key"] == "clean_value"
        assert "password=********" in sanitized["sensitive_key"]
        assert "mysql://user:********@server/db" in sanitized["nested"]["connection"]
        assert sanitized["nested"]["timeout"] == 30  # Numbers preserved
        assert "api_key=********" in sanitized["list_data"][1]

    def test_sanitize_list(self):
        """Test list sanitization."""
        sanitizer = ErrorSanitizer()

        test_list = [
            "clean message",
            "password=secret123",
            {"nested_key": "token=sensitive"},
            ["nested_list", "api_key=secret"],
            42,  # Non-string value
        ]

        sanitized = sanitizer.sanitize_list(test_list)

        assert sanitized[0] == "clean message"
        assert "password=********" in sanitized[1]
        assert "token=********" in sanitized[2]["nested_key"]
        assert "api_key=********" in sanitized[3][1]
        assert sanitized[4] == 42

    def test_sanitize_file_path_method(self):
        """Test dedicated file path sanitization method."""
        sanitizer = ErrorSanitizer()

        test_cases = [
            ("/home/user/secret.txt", "/home/******/secret.txt"),
            ("/Users/john/document.pdf", "/home/******/document.pdf"),
            (Path("/home/alice/file.log"), "/home/******/file.log"),
        ]

        for original, expected in test_cases:
            result = sanitizer.sanitize_file_path(original)
            assert result == expected

    def test_factory_methods(self):
        """Test factory method configurations."""
        # Default sanitizer
        default = ErrorSanitizer.create_default()
        assert "ip_address" in default.patterns

        # Strict sanitizer (includes all patterns)
        strict = ErrorSanitizer.create_strict()
        assert "ip_address" in strict.patterns

        # Lenient sanitizer (skips IP addresses)
        lenient = ErrorSanitizer.create_lenient()
        assert "ip_address" not in lenient.patterns

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        # Test sanitize_error_message
        result = sanitize_error_message("password=secret123")
        assert result == "password=********"

        # Test sanitize_exception
        exception = ValueError("token=secret123")
        sanitized = sanitize_exception(exception)
        assert "token=********" in str(sanitized)

        # Test sanitize_onex_error
        error = OnexError(
            message="api_key=secret123", error_code=CoreErrorCode.INVALID_PARAMETER
        )
        sanitized = sanitize_onex_error(error)
        assert "api_key=********" in sanitized.message

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        sanitizer = ErrorSanitizer()

        # Non-string input
        result = sanitizer.sanitize_message(123)
        assert result == "123"

        # Empty string
        result = sanitizer.sanitize_message("")
        assert result == ""

        # None input
        result = sanitizer.sanitize_message(None)
        assert result == "None"

        # String with only whitespace
        result = sanitizer.sanitize_message("   ")
        assert result == "   "

    def test_pattern_specificity(self):
        """Test that patterns are specific enough to avoid false positives."""
        sanitizer = ErrorSanitizer()

        # These should NOT be sanitized (legitimate content)
        legitimate_cases = [
            "This is a test message",
            "Error code: 404",
            "Processing user data",
            "Configuration loaded successfully",
        ]

        for message in legitimate_cases:
            result = sanitizer.sanitize_message(message)
            assert result == message  # Should be unchanged

    def test_multiple_patterns_in_single_message(self):
        """Test sanitization when multiple sensitive patterns exist in one message."""
        sanitizer = ErrorSanitizer()

        message = "Login failed: password=secret123, api_key=abc456, token=xyz789"
        result = sanitizer.sanitize_message(message)

        # All sensitive values should be masked
        assert "secret123" not in result
        assert "abc456" not in result
        assert "xyz789" not in result
        assert "password=********" in result
        assert "api_key=********" in result
        assert "token=********" in result
