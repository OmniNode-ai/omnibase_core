"""
Tests for Runtime Host error hierarchy ().

TDD tests for minimal MVP error classes:
- RuntimeHostError (base)
- HandlerExecutionError
- EventBusError
- InvalidOperationError
- ContractValidationError
"""

from uuid import UUID, uuid4

import pytest


@pytest.mark.timeout(10)
class TestRuntimeHostError:
    """Tests for RuntimeHostError base class."""

    def test_runtime_host_error_creation(self) -> None:
        """Test creating RuntimeHostError with minimal args."""
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        error = RuntimeHostError("Runtime error occurred")

        # ModelOnexError includes error code in string representation
        assert "[ONEX_CORE_094_RUNTIME_ERROR]" in str(error)
        assert "Runtime error occurred" in str(error)
        # Check error-specific attributes before isinstance check to avoid type narrowing
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_runtime_host_error_with_correlation_id(self) -> None:
        """Test RuntimeHostError preserves correlation_id."""
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        corr_id = uuid4()
        error = RuntimeHostError(
            "Runtime error",
            correlation_id=corr_id,
        )

        assert error.correlation_id == corr_id

    def test_runtime_host_error_with_operation(self) -> None:
        """Test RuntimeHostError with operation context."""
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        error = RuntimeHostError(
            "Operation failed",
            operation="node_initialization",
        )

        assert error.operation == "node_initialization"

    def test_runtime_host_error_serialization(self) -> None:
        """Test RuntimeHostError can be serialized."""
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        error = RuntimeHostError(
            "Runtime error",
            operation="test_operation",
        )

        # Should have model_dump method from ModelOnexError
        error_dict = error.model_dump()

        assert error_dict["message"] == "Runtime error"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("operation") == "test_operation"


@pytest.mark.timeout(10)
class TestHandlerExecutionError:
    """Tests for HandlerExecutionError."""

    def test_handler_execution_error_creation(self) -> None:
        """Test creating HandlerExecutionError."""
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        error = HandlerExecutionError(
            "Handler failed",
            handler_type="HTTP",
        )

        assert "[ONEX_CORE_095_HANDLER_EXECUTION_ERROR]" in str(error)
        assert "Handler failed" in str(error)
        assert error.handler_type == "HTTP"

    def test_handler_execution_error_with_operation(self) -> None:
        """Test HandlerExecutionError with handler operation."""
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        error = HandlerExecutionError(
            "Request failed",
            handler_type="Kafka",
            operation="publish_message",
        )

        assert error.handler_type == "Kafka"
        assert error.operation == "publish_message"

    def test_handler_execution_error_correlation_tracking(self) -> None:
        """Test HandlerExecutionError preserves correlation_id for tracking."""
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        corr_id = uuid4()
        error = HandlerExecutionError(
            "Handler timeout",
            handler_type="Database",
            correlation_id=corr_id,
        )

        assert error.correlation_id == corr_id

    def test_handler_execution_error_structured_fields(self) -> None:
        """Test HandlerExecutionError has required structured fields."""
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        error = HandlerExecutionError(
            "Handler error",
            handler_type="Redis",
            operation="cache_get",
        )

        error_dict = error.model_dump()

        # MVP requirement: handler_type, operation, correlation_id
        assert "context" in error_dict
        assert "handler_type" in error_dict["context"]
        assert "operation" in error_dict["context"]
        assert "correlation_id" in error_dict


@pytest.mark.timeout(10)
class TestEventBusError:
    """Tests for EventBusError."""

    def test_event_bus_error_creation(self) -> None:
        """Test creating EventBusError."""
        from omnibase_core.errors.runtime_errors import EventBusError

        error = EventBusError("Event bus connection lost")

        assert "[ONEX_CORE_096_EVENT_BUS_ERROR]" in str(error)
        assert "Event bus connection lost" in str(error)
        assert error.correlation_id is not None

    def test_event_bus_error_with_operation(self) -> None:
        """Test EventBusError with operation context."""
        from omnibase_core.errors.runtime_errors import EventBusError

        error = EventBusError(
            "Failed to publish event",
            operation="publish",
        )

        assert error.operation == "publish"

    def test_event_bus_error_correlation_tracking(self) -> None:
        """Test EventBusError supports correlation tracking."""
        from omnibase_core.errors.runtime_errors import EventBusError

        corr_id = uuid4()
        error = EventBusError(
            "Event delivery failed",
            operation="deliver_event",
            correlation_id=corr_id,
        )

        assert error.correlation_id == corr_id


@pytest.mark.timeout(10)
class TestInvalidOperationError:
    """Tests for InvalidOperationError."""

    def test_invalid_operation_error_creation(self) -> None:
        """Test creating InvalidOperationError."""
        from omnibase_core.errors.runtime_errors import InvalidOperationError

        error = InvalidOperationError("Invalid state transition")

        assert "[ONEX_CORE_008_INVALID_OPERATION]" in str(error)
        assert "Invalid state transition" in str(error)
        assert error.correlation_id is not None

    def test_invalid_operation_error_with_operation(self) -> None:
        """Test InvalidOperationError with operation context."""
        from omnibase_core.errors.runtime_errors import InvalidOperationError

        error = InvalidOperationError(
            "Operation not allowed",
            operation="delete_active_node",
        )

        assert error.operation == "delete_active_node"

    def test_invalid_operation_error_inheritance(self) -> None:
        """Test InvalidOperationError inherits from RuntimeHostError."""
        from omnibase_core.errors.runtime_errors import (
            InvalidOperationError,
            RuntimeHostError,
        )

        error = InvalidOperationError("Invalid operation")

        assert isinstance(error, RuntimeHostError)
        assert isinstance(error, Exception)


@pytest.mark.timeout(10)
class TestContractValidationError:
    """Tests for ContractValidationError."""

    def test_contract_validation_error_creation(self) -> None:
        """Test creating ContractValidationError."""
        from omnibase_core.errors.runtime_errors import ContractValidationError

        error = ContractValidationError("Contract validation failed")

        assert "[ONEX_CORE_097_CONTRACT_VALIDATION_ERROR]" in str(error)
        assert "Contract validation failed" in str(error)
        assert error.correlation_id is not None

    def test_contract_validation_error_with_operation(self) -> None:
        """Test ContractValidationError with operation context."""
        from omnibase_core.errors.runtime_errors import ContractValidationError

        error = ContractValidationError(
            "Invalid contract schema",
            operation="load_contract",
        )

        assert error.operation == "load_contract"

    def test_contract_validation_error_structured_context(self) -> None:
        """Test ContractValidationError supports structured context."""
        from omnibase_core.errors.runtime_errors import ContractValidationError

        error = ContractValidationError(
            "Missing required field",
            operation="validate_schema",
            field="handler_type",
            expected_type="string",
        )

        error_dict = error.model_dump()

        # Context fields are nested in 'context' dict
        assert "context" in error_dict
        assert "field" in error_dict["context"]
        assert "expected_type" in error_dict["context"]


@pytest.mark.timeout(10)
class TestErrorInvariants:
    """Tests for MVP error invariants from ."""

    def test_all_errors_include_correlation_id(self) -> None:
        """Test all MVP errors include correlation_id."""
        from omnibase_core.errors.runtime_errors import (
            ContractValidationError,
            EventBusError,
            HandlerExecutionError,
            InvalidOperationError,
            RuntimeHostError,
        )

        errors = [
            RuntimeHostError("test"),
            HandlerExecutionError("test", handler_type="HTTP"),
            EventBusError("test"),
            InvalidOperationError("test"),
            ContractValidationError("test"),
        ]

        for error in errors:
            assert hasattr(error, "correlation_id")
            assert error.correlation_id is not None
            assert isinstance(error.correlation_id, UUID)

    def test_handler_errors_include_handler_type(self) -> None:
        """Test handler errors include handler_type when applicable."""
        from omnibase_core.errors.runtime_errors import HandlerExecutionError

        error = HandlerExecutionError("test", handler_type="Kafka")

        assert hasattr(error, "handler_type")
        assert error.handler_type == "Kafka"

    def test_errors_include_operation_when_applicable(self) -> None:
        """Test errors include operation when applicable."""
        from omnibase_core.errors.runtime_errors import (
            EventBusError,
            HandlerExecutionError,
            InvalidOperationError,
        )

        error1 = HandlerExecutionError("test", handler_type="HTTP", operation="GET")
        error2 = EventBusError("test", operation="publish")
        error3 = InvalidOperationError("test", operation="delete")

        assert error1.operation == "GET"
        assert error2.operation == "publish"
        assert error3.operation == "delete"

    def test_no_raw_stack_traces_in_serialization(self) -> None:
        """Test error serialization doesn't include raw stack traces."""
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        error = RuntimeHostError("test error")
        error_dict = error.model_dump()

        # Should not have __traceback__ or raw stack trace
        assert "__traceback__" not in error_dict
        assert "traceback" not in error_dict

        # Context fields should be structured, not raw exception data
        for _, value in error_dict.items():
            assert not isinstance(value, type(error))  # No nested exceptions
