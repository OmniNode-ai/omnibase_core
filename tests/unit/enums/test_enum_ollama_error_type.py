"""Tests for enum_ollama_error_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_ollama_error_type import EnumOllamaErrorType


@pytest.mark.unit
class TestEnumOllamaErrorType:
    """Test cases for EnumOllamaErrorType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumOllamaErrorType.TIMEOUT == "timeout"
        assert EnumOllamaErrorType.CONNECTION == "connection"
        assert EnumOllamaErrorType.MODEL_NOT_FOUND == "model_not_found"
        assert EnumOllamaErrorType.UNKNOWN == "unknown"
        assert EnumOllamaErrorType.API_ERROR == "api_error"
        assert EnumOllamaErrorType.NETWORK_ERROR == "network_error"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumOllamaErrorType, str)
        assert issubclass(EnumOllamaErrorType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumOllamaErrorType.TIMEOUT == "timeout"
        assert EnumOllamaErrorType.CONNECTION == "connection"
        assert EnumOllamaErrorType.UNKNOWN == "unknown"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumOllamaErrorType)
        assert len(values) == 6
        assert EnumOllamaErrorType.TIMEOUT in values
        assert EnumOllamaErrorType.NETWORK_ERROR in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumOllamaErrorType.TIMEOUT in EnumOllamaErrorType
        assert "timeout" in EnumOllamaErrorType
        assert "invalid_value" not in EnumOllamaErrorType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumOllamaErrorType.TIMEOUT == EnumOllamaErrorType.TIMEOUT
        assert EnumOllamaErrorType.CONNECTION != EnumOllamaErrorType.TIMEOUT
        assert EnumOllamaErrorType.TIMEOUT == "timeout"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumOllamaErrorType.TIMEOUT.value == "timeout"
        assert EnumOllamaErrorType.CONNECTION.value == "connection"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumOllamaErrorType("timeout") == EnumOllamaErrorType.TIMEOUT
        assert EnumOllamaErrorType("connection") == EnumOllamaErrorType.CONNECTION

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumOllamaErrorType("invalid_value")

        with pytest.raises(ValueError):
            EnumOllamaErrorType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "timeout",
            "connection",
            "model_not_found",
            "unknown",
            "api_error",
            "network_error",
        }
        actual_values = {member.value for member in EnumOllamaErrorType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Ollama-specific error types" in EnumOllamaErrorType.__doc__

    def test_enum_error_types(self):
        """Test specific error types"""
        # Timeout error
        assert EnumOllamaErrorType.TIMEOUT.value == "timeout"

        # Connection error
        assert EnumOllamaErrorType.CONNECTION.value == "connection"

        # Model not found error
        assert EnumOllamaErrorType.MODEL_NOT_FOUND.value == "model_not_found"

        # Unknown error
        assert EnumOllamaErrorType.UNKNOWN.value == "unknown"

        # API error
        assert EnumOllamaErrorType.API_ERROR.value == "api_error"

        # Network error
        assert EnumOllamaErrorType.NETWORK_ERROR.value == "network_error"

    def test_enum_error_categories(self):
        """Test error categories"""
        # Network-related errors
        network_errors = {
            EnumOllamaErrorType.TIMEOUT,
            EnumOllamaErrorType.CONNECTION,
            EnumOllamaErrorType.NETWORK_ERROR,
        }

        # API-related errors
        api_errors = {EnumOllamaErrorType.API_ERROR}

        # Model-related errors
        model_errors = {EnumOllamaErrorType.MODEL_NOT_FOUND}

        # Unknown errors
        unknown_errors = {EnumOllamaErrorType.UNKNOWN}

        all_errors = set(EnumOllamaErrorType)
        assert (
            network_errors.union(api_errors).union(model_errors).union(unknown_errors)
            == all_errors
        )

    def test_enum_error_severity(self):
        """Test error severity categories"""
        # Recoverable errors
        recoverable_errors = {
            EnumOllamaErrorType.TIMEOUT,
            EnumOllamaErrorType.CONNECTION,
            EnumOllamaErrorType.NETWORK_ERROR,
        }

        # Model errors
        model_errors = {EnumOllamaErrorType.MODEL_NOT_FOUND}

        # API errors
        api_errors = {EnumOllamaErrorType.API_ERROR}

        # Unknown errors
        unknown_errors = {EnumOllamaErrorType.UNKNOWN}

        all_errors = set(EnumOllamaErrorType)
        assert (
            recoverable_errors.union(model_errors)
            .union(api_errors)
            .union(unknown_errors)
            == all_errors
        )
