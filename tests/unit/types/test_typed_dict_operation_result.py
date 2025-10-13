"""
Test suite for TypedDictOperationResult.
"""

from datetime import datetime

import pytest

from omnibase_core.types.typed_dict_error_details import TypedDictErrorDetails
from omnibase_core.types.typed_dict_operation_result import TypedDictOperationResult


class TestTypedDictOperationResult:
    """Test TypedDictOperationResult functionality."""

    def test_typed_dict_operation_result_creation(self):
        """Test creating TypedDictOperationResult with required fields."""
        result: TypedDictOperationResult = {
            "success": True,
            "result_type": "test_operation",
            "execution_time_ms": 150,
            "timestamp": datetime.now(),
        }

        assert result["success"] is True
        assert result["result_type"] == "test_operation"
        assert result["execution_time_ms"] == 150
        assert isinstance(result["timestamp"], datetime)

    def test_typed_dict_operation_result_with_error(self):
        """Test TypedDictOperationResult with error details."""
        error_details: TypedDictErrorDetails = {
            "error_code": "E001",
            "error_message": "Test error",
            "error_type": "validation_error",
        }

        result: TypedDictOperationResult = {
            "success": False,
            "result_type": "failed_operation",
            "execution_time_ms": 200,
            "timestamp": datetime.now(),
            "error_details": error_details,
        }

        assert result["success"] is False
        assert result["error_details"] == error_details
        assert result["error_details"]["error_code"] == "E001"

    def test_typed_dict_operation_result_optional_error_details(self):
        """Test that error_details is optional."""
        result: TypedDictOperationResult = {
            "success": True,
            "result_type": "successful_operation",
            "execution_time_ms": 100,
            "timestamp": datetime.now(),
        }

        # Should not have error_details key
        assert "error_details" not in result
        assert result["success"] is True

    def test_typed_dict_operation_result_types(self):
        """Test that all fields have correct types."""
        result: TypedDictOperationResult = {
            "success": True,
            "result_type": "test",
            "execution_time_ms": 50,
            "timestamp": datetime(2024, 1, 1, 12, 0, 0),
        }

        assert isinstance(result["success"], bool)
        assert isinstance(result["result_type"], str)
        assert isinstance(result["execution_time_ms"], int)
        assert isinstance(result["timestamp"], datetime)

    def test_typed_dict_operation_result_execution_time(self):
        """Test execution time field."""
        result: TypedDictOperationResult = {
            "success": True,
            "result_type": "timed_operation",
            "execution_time_ms": 0,  # Very fast operation
            "timestamp": datetime.now(),
        }

        assert result["execution_time_ms"] == 0

    def test_typed_dict_operation_result_timestamp_formats(self):
        """Test different timestamp formats."""
        now = datetime.now()
        iso_timestamp = datetime.fromisoformat("2024-01-01T12:00:00")

        result1: TypedDictOperationResult = {
            "success": True,
            "result_type": "now_operation",
            "execution_time_ms": 100,
            "timestamp": now,
        }

        result2: TypedDictOperationResult = {
            "success": True,
            "result_type": "iso_operation",
            "execution_time_ms": 200,
            "timestamp": iso_timestamp,
        }

        assert result1["timestamp"] == now
        assert result2["timestamp"] == iso_timestamp

    def test_typed_dict_operation_result_result_types(self):
        """Test different result types."""
        result_types = ["success", "failure", "partial", "timeout", "cancelled"]

        for result_type in result_types:
            result: TypedDictOperationResult = {
                "success": result_type == "success",
                "result_type": result_type,
                "execution_time_ms": 100,
                "timestamp": datetime.now(),
            }

            assert result["result_type"] == result_type
            assert result["success"] == (result_type == "success")
