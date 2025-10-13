"""
Tests for EnumDocumentFreshnessErrorCodes enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_document_freshness_errors import (
    EnumDocumentFreshnessErrorCodes,
)


class TestEnumDocumentFreshnessErrorCodes:
    """Test cases for EnumDocumentFreshnessErrorCodes enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        # Test path validation errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND
            == "FRESHNESS_PATH_NOT_FOUND"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_INVALID
            == "FRESHNESS_PATH_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_ACCESS_DENIED
            == "FRESHNESS_PATH_ACCESS_DENIED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_TOO_LONG
            == "FRESHNESS_PATH_TOO_LONG"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_FORBIDDEN_PATTERN
            == "FRESHNESS_PATH_FORBIDDEN_PATTERN"
        )

        # Test database errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_INIT_FAILED
            == "FRESHNESS_DATABASE_INIT_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_CONNECTION_FAILED
            == "FRESHNESS_DATABASE_CONNECTION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_QUERY_FAILED
            == "FRESHNESS_DATABASE_QUERY_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_WRITE_FAILED
            == "FRESHNESS_DATABASE_WRITE_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_SCHEMA_INVALID
            == "FRESHNESS_DATABASE_SCHEMA_INVALID"
        )

        # Test analysis errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FAILED
            == "FRESHNESS_ANALYSIS_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_TIMEOUT
            == "FRESHNESS_ANALYSIS_TIMEOUT"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_MEMORY_EXCEEDED
            == "FRESHNESS_ANALYSIS_MEMORY_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FILE_TOO_LARGE
            == "FRESHNESS_ANALYSIS_FILE_TOO_LARGE"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_INVALID_CONFIG
            == "FRESHNESS_ANALYSIS_INVALID_CONFIG"
        )

        # Test AI service errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_UNAVAILABLE
            == "FRESHNESS_AI_SERVICE_UNAVAILABLE"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_ERROR
            == "FRESHNESS_AI_SERVICE_ERROR"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_RATE_LIMIT_EXCEEDED
            == "FRESHNESS_AI_RATE_LIMIT_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_CONTENT_TOO_LARGE
            == "FRESHNESS_AI_CONTENT_TOO_LARGE"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET
            == "FRESHNESS_AI_QUALITY_THRESHOLD_NOT_MET"
        )

        # Test dependency analysis errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED
            == "FRESHNESS_DEPENDENCY_ANALYSIS_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED
            == "FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED
            == "FRESHNESS_DEPENDENCY_DEPTH_EXCEEDED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_PARSING_FAILED
            == "FRESHNESS_DEPENDENCY_PARSING_FAILED"
        )

        # Test change detection errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_DETECTION_FAILED
            == "FRESHNESS_CHANGE_DETECTION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_UNAVAILABLE
            == "FRESHNESS_GIT_UNAVAILABLE"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_OPERATION_FAILED
            == "FRESHNESS_GIT_OPERATION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_HISTORY_CORRUPTED
            == "FRESHNESS_CHANGE_HISTORY_CORRUPTED"
        )

        # Test validation errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_VALIDATION_FAILED
            == "FRESHNESS_VALIDATION_FAILED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID
            == "FRESHNESS_CONFIG_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_INPUT_INVALID
            == "FRESHNESS_INPUT_INVALID"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OUTPUT_VALIDATION_FAILED
            == "FRESHNESS_OUTPUT_VALIDATION_FAILED"
        )

        # Test system errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_SYSTEM_ERROR
            == "FRESHNESS_SYSTEM_ERROR"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PERMISSION_DENIED
            == "FRESHNESS_PERMISSION_DENIED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_RESOURCE_EXHAUSTED
            == "FRESHNESS_RESOURCE_EXHAUSTED"
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_OPERATION_CANCELLED
            == "FRESHNESS_OPERATION_CANCELLED"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDocumentFreshnessErrorCodes, str)
        assert issubclass(EnumDocumentFreshnessErrorCodes, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        error_code = EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND
        assert isinstance(error_code, str)
        assert error_code == "FRESHNESS_PATH_NOT_FOUND"
        assert len(error_code) == 24
        assert error_code.startswith("FRESHNESS")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDocumentFreshnessErrorCodes)
        assert len(values) == 36
        assert EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND in values
        assert EnumDocumentFreshnessErrorCodes.FRESHNESS_OPERATION_CANCELLED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "FRESHNESS_PATH_NOT_FOUND" in EnumDocumentFreshnessErrorCodes
        assert "invalid_error" not in EnumDocumentFreshnessErrorCodes

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        error1 = EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND
        error2 = EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_INVALID

        assert error1 != error2
        assert error1 == "FRESHNESS_PATH_NOT_FOUND"
        assert error2 == "FRESHNESS_PATH_INVALID"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        error_code = EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FAILED
        serialized = error_code.value
        assert serialized == "FRESHNESS_ANALYSIS_FAILED"

        # Test JSON serialization
        import json

        json_str = json.dumps(error_code)
        assert json_str == '"FRESHNESS_ANALYSIS_FAILED"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        error_code = EnumDocumentFreshnessErrorCodes("FRESHNESS_DATABASE_INIT_FAILED")
        assert (
            error_code == EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_INIT_FAILED
        )

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDocumentFreshnessErrorCodes("invalid_error")

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

        actual_values = {member.value for member in EnumDocumentFreshnessErrorCodes}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Standardized error codes for document freshness monitoring"
            in EnumDocumentFreshnessErrorCodes.__doc__
        )

    def test_enum_error_categories(self):
        """Test that enum covers typical error categories."""
        # Test path validation errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_NOT_FOUND
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PATH_INVALID
            in EnumDocumentFreshnessErrorCodes
        )

        # Test database errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_INIT_FAILED
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DATABASE_CONNECTION_FAILED
            in EnumDocumentFreshnessErrorCodes
        )

        # Test analysis errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_FAILED
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_ANALYSIS_TIMEOUT
            in EnumDocumentFreshnessErrorCodes
        )

        # Test AI service errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_UNAVAILABLE
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_AI_SERVICE_ERROR
            in EnumDocumentFreshnessErrorCodes
        )

        # Test dependency analysis errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_ANALYSIS_FAILED
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_DEPENDENCY_CIRCULAR_DETECTED
            in EnumDocumentFreshnessErrorCodes
        )

        # Test change detection errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CHANGE_DETECTION_FAILED
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_GIT_UNAVAILABLE
            in EnumDocumentFreshnessErrorCodes
        )

        # Test validation errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_VALIDATION_FAILED
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID
            in EnumDocumentFreshnessErrorCodes
        )

        # Test system errors
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_SYSTEM_ERROR
            in EnumDocumentFreshnessErrorCodes
        )
        assert (
            EnumDocumentFreshnessErrorCodes.FRESHNESS_PERMISSION_DENIED
            in EnumDocumentFreshnessErrorCodes
        )
