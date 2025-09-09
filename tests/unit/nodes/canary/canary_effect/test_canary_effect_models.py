#!/usr/bin/env python3
"""
Unit tests for Canary Effect Contract-Driven Models.

Tests the contract-driven Pydantic models for canary effect operations,
including validation, field constraints, and helper methods.
"""

import uuid
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from omnibase_core.nodes.canary.canary_effect.v1_0_0.models import (
    EnumCanaryOperationType,
    ModelCanaryEffectInput,
    ModelCanaryEffectOutput,
)


class TestEnumCanaryOperationType:
    """Test EnumCanaryOperationType enum values."""

    def test_enum_values(self):
        """Test all enum values are correctly defined."""
        assert EnumCanaryOperationType.HEALTH_CHECK == "health_check"
        assert EnumCanaryOperationType.EXTERNAL_API_CALL == "external_api_call"
        assert EnumCanaryOperationType.FILE_SYSTEM_OPERATION == "file_system_operation"
        assert EnumCanaryOperationType.DATABASE_OPERATION == "database_operation"
        assert (
            EnumCanaryOperationType.MESSAGE_QUEUE_OPERATION == "message_queue_operation"
        )

    def test_enum_membership(self):
        """Test valid enum membership checks."""
        valid_operations = [
            "health_check",
            "external_api_call",
            "file_system_operation",
            "database_operation",
            "message_queue_operation",
        ]

        for operation in valid_operations:
            assert operation in [op.value for op in EnumCanaryOperationType]

    def test_invalid_enum_value(self):
        """Test that invalid enum values are not accepted."""
        invalid_operations = ["invalid_operation", "unknown_type", ""]

        for operation in invalid_operations:
            assert operation not in [op.value for op in EnumCanaryOperationType]


class TestModelCanaryEffectInput:
    """Test ModelCanaryEffectInput contract-driven model."""

    def test_basic_creation(self):
        """Test basic model creation with required fields."""
        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.HEALTH_CHECK
        )

        assert input_model.operation_type == EnumCanaryOperationType.HEALTH_CHECK
        assert input_model.target_system is None
        assert input_model.parameters == {}
        assert input_model.correlation_id is not None  # Auto-generated
        assert isinstance(input_model.correlation_id, str)

    def test_full_creation(self):
        """Test model creation with all fields."""
        correlation_id = str(uuid.uuid4())
        parameters = {"test_param": "test_value", "timeout": 5000}

        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.EXTERNAL_API_CALL,
            target_system="test_api",
            parameters=parameters,
            correlation_id=correlation_id,
        )

        assert input_model.operation_type == EnumCanaryOperationType.EXTERNAL_API_CALL
        assert input_model.target_system == "test_api"
        assert input_model.parameters == parameters
        assert input_model.correlation_id == correlation_id

    def test_correlation_id_auto_generation(self):
        """Test automatic correlation ID generation."""
        input_model1 = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.HEALTH_CHECK
        )
        input_model2 = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.HEALTH_CHECK
        )

        # Should be auto-generated and unique
        assert input_model1.correlation_id is not None
        assert input_model2.correlation_id is not None
        assert input_model1.correlation_id != input_model2.correlation_id

        # Should be valid UUIDs
        uuid.UUID(input_model1.correlation_id)  # Will raise if invalid
        uuid.UUID(input_model2.correlation_id)  # Will raise if invalid

    def test_invalid_operation_type(self):
        """Test validation failure with invalid operation type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCanaryEffectInput(operation_type="invalid_operation")  # type: ignore

        error = exc_info.value
        assert "operation_type" in str(error)

    def test_missing_required_field(self):
        """Test validation failure when required operation_type is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCanaryEffectInput()  # type: ignore

        error = exc_info.value
        assert "operation_type" in str(error)
        assert "Field required" in str(error)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCanaryEffectInput(
                operation_type=EnumCanaryOperationType.HEALTH_CHECK,
                invalid_field="not_allowed",  # type: ignore
            )

        error = exc_info.value
        assert "Extra inputs are not permitted" in str(error)

    def test_to_operation_data(self):
        """Test backward compatibility conversion method."""
        correlation_id = str(uuid.uuid4())
        parameters = {"test": "value"}

        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.DATABASE_OPERATION,
            target_system="postgres",
            parameters=parameters,
            correlation_id=correlation_id,
        )

        operation_data = input_model.to_operation_data()

        expected_data = {
            "operation_type": "database_operation",
            "target_system": "postgres",
            "parameters": parameters,
            "correlation_id": correlation_id,
        }

        assert operation_data == expected_data

    def test_model_serialization(self):
        """Test model serialization to dict."""
        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.FILE_SYSTEM_OPERATION,
            target_system="local_fs",
            parameters={"operation": "read", "path": "/tmp/test"},
        )

        serialized = input_model.model_dump()

        assert isinstance(serialized, dict)
        assert serialized["operation_type"] == "file_system_operation"
        assert serialized["target_system"] == "local_fs"
        assert "correlation_id" in serialized

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "operation_type": "message_queue_operation",
            "target_system": "rabbitmq",
            "parameters": {"queue": "test_queue"},
            "correlation_id": str(uuid.uuid4()),
        }

        input_model = ModelCanaryEffectInput.model_validate(data)

        assert (
            input_model.operation_type
            == EnumCanaryOperationType.MESSAGE_QUEUE_OPERATION
        )
        assert input_model.target_system == "rabbitmq"
        assert input_model.parameters == {"queue": "test_queue"}
        assert input_model.correlation_id == data["correlation_id"]


class TestModelCanaryEffectOutput:
    """Test ModelCanaryEffectOutput contract-driven model."""

    def test_basic_creation_success(self):
        """Test basic model creation for successful operation."""
        output_model = ModelCanaryEffectOutput()

        assert output_model.operation_result == {}
        assert output_model.success is True  # Default value
        assert output_model.error_message is None
        assert output_model.execution_time_ms is None
        assert output_model.correlation_id is None

    def test_basic_creation_failure(self):
        """Test basic model creation for failed operation."""
        output_model = ModelCanaryEffectOutput(
            success=False, error_message="Operation failed"
        )

        assert output_model.success is False
        assert output_model.error_message == "Operation failed"

    def test_full_creation(self):
        """Test model creation with all fields."""
        correlation_id = str(uuid.uuid4())
        operation_result = {
            "api_response": "success",
            "status_code": 200,
            "data": {"processed": True},
        }

        output_model = ModelCanaryEffectOutput(
            operation_result=operation_result,
            success=True,
            error_message=None,
            execution_time_ms=250,
            correlation_id=correlation_id,
        )

        assert output_model.operation_result == operation_result
        assert output_model.success is True
        assert output_model.error_message is None
        assert output_model.execution_time_ms == 250
        assert output_model.correlation_id == correlation_id

    def test_execution_time_validation_positive(self):
        """Test execution time validation allows positive values."""
        output_model = ModelCanaryEffectOutput(execution_time_ms=100)
        assert output_model.execution_time_ms == 100

    def test_execution_time_validation_zero(self):
        """Test execution time validation allows zero."""
        output_model = ModelCanaryEffectOutput(execution_time_ms=0)
        assert output_model.execution_time_ms == 0

    def test_execution_time_validation_negative(self):
        """Test execution time validation rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCanaryEffectOutput(execution_time_ms=-100)

        error = exc_info.value
        # Pydantic v2 uses built-in constraint validation message
        assert "Input should be greater than or equal to 0" in str(error)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCanaryEffectOutput(
                success=True, invalid_field="not_allowed"  # type: ignore
            )

        error = exc_info.value
        assert "Extra inputs are not permitted" in str(error)

    def test_is_successful_true_no_error(self):
        """Test is_successful returns True when success=True and no error."""
        output_model = ModelCanaryEffectOutput(success=True, error_message=None)
        assert output_model.is_successful() is True

    def test_is_successful_false_with_error(self):
        """Test is_successful returns False when success=False."""
        output_model = ModelCanaryEffectOutput(
            success=False, error_message="Something went wrong"
        )
        assert output_model.is_successful() is False

    def test_is_successful_true_with_error(self):
        """Test is_successful returns False when success=True but has error."""
        output_model = ModelCanaryEffectOutput(
            success=True, error_message="Warning message"
        )
        assert output_model.is_successful() is False

    def test_has_execution_metrics_true(self):
        """Test has_execution_metrics returns True when timing data available."""
        output_model = ModelCanaryEffectOutput(execution_time_ms=150)
        assert output_model.has_execution_metrics() is True

    def test_has_execution_metrics_false(self):
        """Test has_execution_metrics returns False when no timing data."""
        output_model = ModelCanaryEffectOutput(execution_time_ms=None)
        assert output_model.has_execution_metrics() is False

    def test_get_result_summary(self):
        """Test get_result_summary returns correct summary data."""
        correlation_id = str(uuid.uuid4())
        operation_result = {"status": "completed", "data": "test"}

        output_model = ModelCanaryEffectOutput(
            operation_result=operation_result,
            success=True,
            error_message=None,
            execution_time_ms=300,
            correlation_id=correlation_id,
        )

        summary = output_model.get_result_summary()

        expected_summary = {
            "success": True,
            "has_error": False,
            "execution_time_ms": 300,
            "result_present": True,
            "result_size": len(str(operation_result)),
            "correlation_id": correlation_id,
        }

        assert summary == expected_summary

    def test_get_result_summary_with_error(self):
        """Test get_result_summary with error condition."""
        output_model = ModelCanaryEffectOutput(
            success=False, error_message="Test error", execution_time_ms=None
        )

        summary = output_model.get_result_summary()

        assert summary["success"] is False
        assert summary["has_error"] is True
        assert summary["execution_time_ms"] is None
        # Empty dict {} is falsy for bool()
        assert summary["result_present"] is False  # bool({}) is False
        assert summary["result_size"] == 0  # (len(str({})) if {} else 0) returns 0

    def test_model_serialization(self):
        """Test model serialization to dict."""
        output_model = ModelCanaryEffectOutput(
            operation_result={"result": "success"}, success=True, execution_time_ms=200
        )

        serialized = output_model.model_dump()

        assert isinstance(serialized, dict)
        assert serialized["success"] is True
        assert serialized["operation_result"] == {"result": "success"}
        assert serialized["execution_time_ms"] == 200

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        correlation_id = str(uuid.uuid4())
        data = {
            "operation_result": {"api_call": "completed"},
            "success": True,
            "error_message": None,
            "execution_time_ms": 450,
            "correlation_id": correlation_id,
        }

        output_model = ModelCanaryEffectOutput.model_validate(data)

        assert output_model.operation_result == {"api_call": "completed"}
        assert output_model.success is True
        assert output_model.error_message is None
        assert output_model.execution_time_ms == 450
        assert output_model.correlation_id == correlation_id


class TestModelIntegration:
    """Test integration between input and output models."""

    def test_correlation_id_propagation(self):
        """Test correlation ID propagation from input to output."""
        # Create input with auto-generated correlation ID
        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.HEALTH_CHECK
        )

        # Create output with same correlation ID
        output_model = ModelCanaryEffectOutput(
            success=True, correlation_id=input_model.correlation_id
        )

        assert input_model.correlation_id == output_model.correlation_id
        assert output_model.is_successful() is True

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip."""
        # Create input model
        input_data = {
            "operation_type": EnumCanaryOperationType.EXTERNAL_API_CALL,
            "target_system": "test_service",
            "parameters": {"endpoint": "/api/test", "method": "GET"},
        }
        input_model = ModelCanaryEffectInput(**input_data)

        # Serialize and deserialize
        serialized_input = input_model.model_dump()
        deserialized_input = ModelCanaryEffectInput.model_validate(serialized_input)

        assert deserialized_input.operation_type == input_model.operation_type
        assert deserialized_input.target_system == input_model.target_system
        assert deserialized_input.parameters == input_model.parameters
        assert deserialized_input.correlation_id == input_model.correlation_id

    def test_backward_compatibility_workflow(self):
        """Test complete workflow with backward compatibility."""
        # Create new contract-driven input
        input_model = ModelCanaryEffectInput(
            operation_type=EnumCanaryOperationType.DATABASE_OPERATION,
            target_system="postgres_primary",
            parameters={"query": "SELECT 1", "timeout": 5000},
        )

        # Convert to legacy format
        legacy_data = input_model.to_operation_data()
        assert legacy_data["operation_type"] == "database_operation"

        # Process and create contract-driven output
        output_model = ModelCanaryEffectOutput(
            operation_result={"rows": 1, "query_time": "0.001s"},
            success=True,
            execution_time_ms=150,
            correlation_id=input_model.correlation_id,
        )

        assert output_model.is_successful() is True
        assert output_model.has_execution_metrics() is True
        assert output_model.correlation_id == input_model.correlation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
