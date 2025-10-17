"""
Tests for EnumDocumentFreshnessErrors enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_document_freshness_errors import (
    EnumDocumentFreshnessErrors,
)


class TestEnumDocumentFreshnessErrors:
    """Test cases for EnumDocumentFreshnessErrors enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        # Test path validation errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_NOT_FOUND
            == "FRESHNESS_PATH_NOT_FOUND"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_INVALID
            == "FRESHNESS_PATH_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_ACCESS_DENIED
            == "FRESHNESS_PATH_ACCESS_DENIED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_TOO_LONG
            == "FRESHNESS_PATH_TOO_LONG"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_FORBIDDEN_PATTERN
            == "FRESHNESS_PATH_FORBIDDEN_PATTERN"
        )

        # Test database errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_INIT_FAILED
            == "FRESHNESS_DATABASE_INIT_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_CONNECTION_FAILED
            == "FRESHNESS_DATABASE_CONNECTION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_QUERY_FAILED
            == "FRESHNESS_DATABASE_QUERY_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_WRITE_FAILED
            == "FRESHNESS_DATABASE_WRITE_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_SCHEMA_INVALID
            == "FRESHNESS_DATABASE_SCHEMA_INVALID"
        )

        # Test analysis errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_FAILED
            == "FRESHNESS_ANALYSIS_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_TIMEOUT
            == "FRESHNESS_ANALYSIS_TIMEOUT"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_MEMORY_EXCEEDED
            == "FRESHNESS_ANALYSIS_MEMORY_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_FILE_TOO_LARGE
            == "FRESHNESS_ANALYSIS_FILE_TOO_LARGE"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_INVALID_CONFIG
            == "FRESHNESS_ANALYSIS_INVALID_CONFIG"
        )

        # Test AI service errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_SERVICE_UNAVAILABLE
            == "FRESHNESS_AI_SERVICE_UNAVAILABLE"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_SERVICE_ERROR
            == "FRESHNESS_AI_SERVICE_ERROR"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_RATE_LIMIT_EXCEEDED
            == "FRESHNESS_AI_RATE_LIMIT_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_CONTENT_TOO_LARGE
            == "FRESHNESS_AI_CONTENT_TOO_LARGE"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET
            == "FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET"
        )

        # Test dependency analysis errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED
            == "FRESHNESS_DEPENDENCY_ANALYSIS_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED
            == "FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED
            == "FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_PARSING_FAILED
            == "FRESHNESS_DEPENDENCY_PARSING_FAILED"
        )

        # Test change detection errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_CHANGE_DETECTION_FAILED
            == "FRESHNESS_CHANGE_DETECTION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_GIT_UNAVAILABLE
            == "FRESHNESS_GIT_UNAVAILABLE"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_GIT_OPERATION_FAILED
            == "FRESHNESS_GIT_OPERATION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_CHANGE_HISTORY_CORRUPTED
            == "FRESHNESS_CHANGE_HISTORY_CORRUPTED"
        )

        # Test validation errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_VALIDATION_FAILED
            == "FRESHNESS_VALIDATION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_CONFIG_INVALID
            == "FRESHNESS_CONFIG_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_INPUT_INVALID
            == "FRESHNESS_INPUT_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_OUTPUT_VALIDATION_FAILED
            == "FRESHNESS_OUTPUT_VALIDATION_FAILED"
        )

        # Test system errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_SYSTEM_ERROR
            == "FRESHNESS_SYSTEM_ERROR"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PERMISSION_DENIED
            == "FRESHNESS_PERMISSION_DENIED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_RESOURCE_EXHAUSTED
            == "FRESHNESS_RESOURCE_EXHAUSTED"
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_OPERATION_CANCELLED
            == "FRESHNESS_OPERATION_CANCELLED"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDocumentFreshnessErrors, str)
        assert issubclass(EnumDocumentFreshnessErrors, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        error_code = EnumDocumentFreshnessErrors.FRESHNESS_PATH_NOT_FOUND
        assert isinstance(error_code, str)
        assert error_code == "FRESHNESS_PATH_NOT_FOUND"
        assert len(error_code) == 24
        assert error_code.startswith("FRESHNESS")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDocumentFreshnessErrors)
        assert len(values) == 36
        assert EnumDocumentFreshnessErrors.FRESHNESS_PATH_NOT_FOUND in values
        assert EnumDocumentFreshnessErrors.FRESHNESS_OPERATION_CANCELLED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "FRESHNESS_PATH_NOT_FOUND" in EnumDocumentFreshnessErrors
        assert "invalid_error" not in EnumDocumentFreshnessErrors

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        error1 = EnumDocumentFreshnessErrors.FRESHNESS_PATH_NOT_FOUND
        error2 = EnumDocumentFreshnessErrors.FRESHNESS_PATH_INVALID

        assert error1 != error2
        assert error1 == "FRESHNESS_PATH_NOT_FOUND"
        assert error2 == "FRESHNESS_PATH_INVALID"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        error_code = EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_FAILED
        serialized = error_code.value
        assert serialized == "FRESHNESS_ANALYSIS_FAILED"

        # Test JSON serialization
        import json

        json_str = json.dumps(error_code)
        assert json_str == '"FRESHNESS_ANALYSIS_FAILED"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        error_code = EnumDocumentFreshnessErrors("FRESHNESS_DATABASE_INIT_FAILED")
        assert error_code == EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_INIT_FAILED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDocumentFreshnessErrors("invalid_error")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "FRESHNESS_PATH_NOT_FOUND",
            "FRESHNESS_PATH_INVALID",
            "FRESHNESS_PATH_ACCESS_DENIED",
            "FRESHNESS_PATH_TOO_LONG",
            "FRESHNESS_PATH_FORBIDDEN_PATTERN",
            "FRESHNESS_DATABASE_INIT_FAILED",
            "FRESHNESS_DATABASE_CONNECTION_FAILED",
            "FRESHNESS_DATABASE_QUERY_FAILED",
            "FRESHNESS_DATABASE_WRITE_FAILED",
            "FRESHNESS_DATABASE_SCHEMA_INVALID",
            "FRESHNESS_ANALYSIS_FAILED",
            "FRESHNESS_ANALYSIS_TIMEOUT",
            "FRESHNESS_ANALYSIS_MEMORY_EXCEEDED",
            "FRESHNESS_ANALYSIS_FILE_TOO_LARGE",
            "FRESHNESS_ANALYSIS_INVALID_CONFIG",
            "FRESHNESS_AI_SERVICE_UNAVAILABLE",
            "FRESHNESS_AI_SERVICE_ERROR",
            "FRESHNESS_AI_RATE_LIMIT_EXCEEDED",
            "FRESHNESS_AI_CONTENT_TOO_LARGE",
            "FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET",
            "FRESHNESS_DEPENDENCY_ANALYSIS_FAILED",
            "FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED",
            "FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED",
            "FRESHNESS_DEPENDENCY_PARSING_FAILED",
            "FRESHNESS_CHANGE_DETECTION_FAILED",
            "FRESHNESS_GIT_UNAVAILABLE",
            "FRESHNESS_GIT_OPERATION_FAILED",
            "FRESHNESS_CHANGE_HISTORY_CORRUPTED",
            "FRESHNESS_VALIDATION_FAILED",
            "FRESHNESS_CONFIG_INVALID",
            "FRESHNESS_INPUT_INVALID",
            "FRESHNESS_OUTPUT_VALIDATION_FAILED",
            "FRESHNESS_SYSTEM_ERROR",
            "FRESHNESS_PERMISSION_DENIED",
            "FRESHNESS_RESOURCE_EXHAUSTED",
            "FRESHNESS_OPERATION_CANCELLED",
        }

        actual_values = {member.value for member in EnumDocumentFreshnessErrors}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Standardized error codes for document freshness monitoring"
            in EnumDocumentFreshnessErrors.__doc__
        )

    def test_enum_error_categories(self):
        """Test that enum covers typical error categories."""
        # Test path validation errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_NOT_FOUND
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PATH_INVALID
            in EnumDocumentFreshnessErrors
        )

        # Test database errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_INIT_FAILED
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DATABASE_CONNECTION_FAILED
            in EnumDocumentFreshnessErrors
        )

        # Test analysis errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_FAILED
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_ANALYSIS_TIMEOUT
            in EnumDocumentFreshnessErrors
        )

        # Test AI service errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_SERVICE_UNAVAILABLE
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_AI_SERVICE_ERROR
            in EnumDocumentFreshnessErrors
        )

        # Test dependency analysis errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED
            in EnumDocumentFreshnessErrors
        )

        # Test change detection errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_CHANGE_DETECTION_FAILED
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_GIT_UNAVAILABLE
            in EnumDocumentFreshnessErrors
        )

        # Test validation errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_VALIDATION_FAILED
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_CONFIG_INVALID
            in EnumDocumentFreshnessErrors
        )

        # Test system errors
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_SYSTEM_ERROR
            in EnumDocumentFreshnessErrors
        )
        assert (
            EnumDocumentFreshnessErrors.FRESHNESS_PERMISSION_DENIED
            in EnumDocumentFreshnessErrors
        )
