"""
Critical fixes test suite for ModelValidationResult.

Tests all Priority 1 critical issues identified in code review:
1. Complete merge() method implementation
2. Input sanitization for context fields
3. Edge case handling and security validation
"""

from pathlib import Path

import pytest

from omnibase_core.model.common.model_validation_result import (
    ModelValidationIssue,
    ModelValidationMetadata,
    ModelValidationResult,
)
from omnibase_core.model.validation.model_validation_rule import EnumValidationSeverity


class TestModelValidationResultMerge:
    """Test suite for the merge() method implementation."""

    def test_merge_basic_functionality(self):
        """Test basic merge functionality between two validation results."""
        # Create first result
        result1 = ModelValidationResult.create_invalid(
            errors=["Error 1", "Error 2"], summary="First validation failed"
        )

        # Create second result with issues
        issue1 = ModelValidationIssue(
            severity=EnumValidationSeverity.warning,
            message="Warning message",
            code="W001",
        )
        result2 = ModelValidationResult.create_invalid(
            issues=[issue1], errors=["Error 3"], summary="Second validation failed"
        )

        # Merge results
        result1.merge(result2)

        # Verify merge results
        assert not result1.is_valid
        assert len(result1.issues) == 3  # 2 from result1 errors + 1 from result2 issues
        assert len(result1.errors) == 3  # 2 + 1
        assert "3 total issues" in result1.summary

    def test_merge_with_metadata(self):
        """Test merge functionality with metadata handling."""
        metadata1 = ModelValidationMetadata(
            files_processed=10, rules_applied=5, duration_ms=100
        )
        metadata2 = ModelValidationMetadata(
            files_processed=15, rules_applied=8, duration_ms=150
        )

        result1 = ModelValidationResult.create_valid()
        result1.metadata = metadata1

        result2 = ModelValidationResult.create_valid()
        result2.metadata = metadata2

        result1.merge(result2)

        # Verify metadata merging
        assert result1.metadata is not None
        assert result1.metadata.files_processed == 25  # 10 + 15
        assert result1.metadata.rules_applied == 13  # 5 + 8
        assert result1.metadata.duration_ms == 250  # 100 + 150

    def test_merge_valid_with_invalid(self):
        """Test merging valid result with invalid result."""
        valid_result = ModelValidationResult.create_valid(summary="All good")
        invalid_result = ModelValidationResult.create_invalid(
            errors=["Critical error"], summary="Failed validation"
        )

        valid_result.merge(invalid_result)

        # Valid result should become invalid after merge
        assert not valid_result.is_valid
        assert len(valid_result.errors) == 1
        assert "1 total issues" in valid_result.summary

    def test_merge_metadata_copying(self):
        """Test metadata copying when one result has no metadata."""
        metadata = ModelValidationMetadata(
            validation_type="security", files_processed=5
        )

        result1 = ModelValidationResult.create_valid()
        result2 = ModelValidationResult.create_valid()
        result2.metadata = metadata

        result1.merge(result2)

        # Metadata should be copied from result2 to result1
        assert result1.metadata is not None
        assert result1.metadata.validation_type == "security"
        assert result1.metadata.files_processed == 5


class TestModelValidationIssueContextSanitization:
    """Test suite for context field sanitization."""

    def test_sanitize_api_keys(self):
        """Test sanitization of API keys and tokens."""
        sensitive_context = {
            "api_key": "sk-12345abcdef",
            "auth_token": "bearer_xyz789",
            "password": "secret123",
            "secret": "top_secret_value",
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.error,
            message="Test issue",
            context=sensitive_context,
        )

        # All sensitive fields should be redacted
        assert issue.context["api_key"] == "[REDACTED]"
        assert issue.context["auth_token"] == "[REDACTED]"
        assert issue.context["password"] == "[REDACTED]"
        assert issue.context["secret"] == "[REDACTED]"

    def test_sanitize_email_addresses(self):
        """Test sanitization of email addresses."""
        context_with_emails = {
            "user_email": "user@example.com",
            "contact": "admin@company.org",
            "mixed_content": "Contact us at support@test.com for help",
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.warning,
            message="Email test",
            context=context_with_emails,
        )

        assert issue.context["user_email"] == "[EMAIL_REDACTED]"
        assert issue.context["contact"] == "[EMAIL_REDACTED]"
        assert "[EMAIL_REDACTED]" in issue.context["mixed_content"]

    def test_sanitize_user_paths(self):
        """Test sanitization of user file paths."""
        path_context = {
            "macos_path": "/Users/johndoe/Documents/secret.txt",
            "windows_path": "C:\\Users\\janedoe\\Desktop\\data.csv",
            "safe_path": "/usr/local/bin/app",
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.info,
            message="Path test",
            context=path_context,
        )

        assert issue.context["macos_path"] == "/Users/[USERNAME]/Documents/secret.txt"
        assert (
            issue.context["windows_path"] == "C:\\Users\\[USERNAME]\\Desktop\\data.csv"
        )
        assert issue.context["safe_path"] == "/usr/local/bin/app"  # Unchanged

    def test_sanitize_urls_with_params(self):
        """Test sanitization of URLs with query parameters."""
        url_context = {
            "api_url": "https://api.example.com/data?token=secret123&user=admin",
            "safe_url": "https://example.com/public",
            "mixed": "Visit https://app.test.com/login?redirect=admin for access",
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.error,
            message="URL test",
            context=url_context,
        )

        assert issue.context["api_url"] == "[URL_WITH_PARAMS_REDACTED]"
        assert (
            issue.context["safe_url"] == "https://example.com/public"
        )  # No params, unchanged
        assert "[URL_WITH_PARAMS_REDACTED]" in issue.context["mixed"]

    def test_truncate_long_values(self):
        """Test truncation of very long context values to prevent DoS."""
        long_value = "x" * 1000  # 1000 character string

        context = {"long_field": long_value, "short_field": "normal"}

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.warning,
            message="Length test",
            context=context,
        )

        # Long value should be truncated to 500 chars max
        assert len(issue.context["long_field"]) == 500  # 497 + "..."
        assert issue.context["long_field"].endswith("...")
        assert issue.context["short_field"] == "normal"  # Unchanged

    def test_handle_non_string_values(self):
        """Test handling of non-string values in context."""
        mixed_context = {
            "number": 12345,
            "boolean": True,
            "list": [1, 2, 3],
            "very_long_number": "1" * 200,
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.info,
            message="Mixed types test",
            context=mixed_context,
        )

        # Non-string values should be converted and truncated
        assert issue.context["number"] == "12345"
        assert issue.context["boolean"] == "True"
        assert "[1, 2, 3]" in issue.context["list"]
        assert (
            len(issue.context["very_long_number"]) == 100
        )  # Truncated to 100 for non-strings

    def test_empty_and_none_context(self):
        """Test handling of empty and None context."""
        # None context should remain None
        issue1 = ModelValidationIssue(
            severity=EnumValidationSeverity.error, message="No context", context=None
        )
        assert issue1.context is None

        # Empty dict should remain empty
        issue2 = ModelValidationIssue(
            severity=EnumValidationSeverity.error, message="Empty context", context={}
        )
        assert issue2.context == {}


class TestModelValidationResultEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_create_invalid_with_empty_errors(self):
        """Test creating invalid result with empty error list."""
        result = ModelValidationResult.create_invalid(errors=[])

        assert not result.is_valid
        assert len(result.errors) == 0
        assert len(result.issues) == 0
        assert "0 issues" in result.summary

    def test_add_issue_updates_validity(self):
        """Test that adding critical/error issues updates validity."""
        result = ModelValidationResult.create_valid()

        # Initially valid
        assert result.is_valid

        # Add warning - should remain valid
        result.add_issue(EnumValidationSeverity.warning, "Warning message")
        assert result.is_valid

        # Add error - should become invalid
        result.add_issue(EnumValidationSeverity.error, "Error message")
        assert not result.is_valid

    def test_severity_counting_methods(self):
        """Test the severity counting property methods."""
        result = ModelValidationResult.create_valid()

        # Add issues of different severities
        result.add_issue(EnumValidationSeverity.critical, "Critical issue")
        result.add_issue(EnumValidationSeverity.error, "Error issue")
        result.add_issue(EnumValidationSeverity.error, "Another error")
        result.add_issue(EnumValidationSeverity.warning, "Warning issue")

        assert result.critical_count == 1
        assert result.error_count == 2
        assert result.warning_count == 1
        assert result.issues_found == 4

        assert result.has_critical_issues()
        assert result.has_errors()
        assert result.has_warnings()

    def test_get_issues_by_file(self):
        """Test filtering issues by file path."""
        result = ModelValidationResult.create_valid()

        file1 = "file1.py"
        file2 = "file2.py"

        result.add_issue(EnumValidationSeverity.error, "File 1 error", file_path=file1)
        result.add_issue(
            EnumValidationSeverity.warning, "File 2 warning", file_path=file2
        )
        result.add_issue(
            EnumValidationSeverity.error, "Another file 1 error", file_path=file1
        )

        file1_issues = result.get_issues_by_file(file1)
        file2_issues = result.get_issues_by_file(file2)

        assert len(file1_issues) == 2
        assert len(file2_issues) == 1
        assert all(issue.file_path == file1 for issue in file1_issues)
        assert all(issue.file_path == file2 for issue in file2_issues)


class TestSecurityScenarios:
    """Test suite for security-related scenarios."""

    def test_malicious_context_injection(self):
        """Test protection against malicious context data injection."""
        malicious_context = {
            "script": "<script>alert('xss')</script>",
            "sql": "'; DROP TABLE users; --",
            "command": "$(rm -rf /)",
            "api_key": "sk-malicious123",
            "long_attack": "A" * 10000,  # DoS attempt
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.error,
            message="Security test",
            context=malicious_context,
        )

        # Verify security measures
        assert "[REDACTED]" in issue.context["api_key"]
        assert len(issue.context["long_attack"]) <= 500  # Truncated

        # Script and SQL should pass through (they're not in our patterns)
        # but they're truncated if too long
        assert "<script>" in issue.context["script"]
        assert "DROP TABLE" in issue.context["sql"]

    def test_nested_sensitive_data(self):
        """Test detection of sensitive data in nested content."""
        nested_context = {
            "config": "database_password=secret123 and api_key=abc-def-123",
            "log": "User token bearer_xyz logged in successfully",
            "error": "Authentication failed for secret_key sk-1234567890",
        }

        issue = ModelValidationIssue(
            severity=EnumValidationSeverity.warning,
            message="Nested sensitive test",
            context=nested_context,
        )

        # All fields with sensitive patterns should be redacted
        assert "[REDACTED]" in issue.context["config"]
        assert "[REDACTED]" in issue.context["log"]
        assert "[REDACTED]" in issue.context["error"]


if __name__ == "__main__":
    # Run the tests if executed directly
    pytest.main([__file__, "-v"])
