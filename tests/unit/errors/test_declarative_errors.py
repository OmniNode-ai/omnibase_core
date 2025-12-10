"""
TDD Tests for Declarative Node Error Classes (OMN-177).

These tests define the expected behavior for 4 new error classes that will
inherit from RuntimeHostError for declarative node validation:

- AdapterBindingError: Errors during adapter/handler binding to declarative nodes
- PurityViolationError: Errors when declarative nodes violate purity constraints
- NodeExecutionError: Errors during declarative node execution phases
- UnsupportedCapabilityError: Errors when nodes lack required capabilities

TDD Approach:
- Tests written BEFORE implementation
- Tests will FAIL until implementation is complete
- Tests define the contract that implementation must satisfy

Error Code Mapping (from EnumCoreErrorCode):
- ADAPTER_BINDING_ERROR = "ONEX_CORE_271_ADAPTER_BINDING_ERROR"
- PURITY_VIOLATION_ERROR = "ONEX_CORE_272_PURITY_VIOLATION_ERROR"
- NODE_EXECUTION_ERROR = "ONEX_CORE_273_NODE_EXECUTION_ERROR"
- UNSUPPORTED_CAPABILITY_ERROR = "ONEX_CORE_274_UNSUPPORTED_CAPABILITY_ERROR"

Test Timeout Configuration:
    All test classes use @pytest.mark.timeout(10) for defensive testing:

    - CI stability: Prevents test hangs from blocking the CI pipeline. A stuck
      test will fail after 10 seconds rather than hanging indefinitely.
    - Generous threshold: 10 seconds is intentionally generous for unit tests,
      which typically complete in <100ms. This accounts for CI environment
      variability (resource contention, cold starts) while still catching
      infinite loops or deadlocks.
    - pytest-timeout best practice: Using class-level markers ensures all
      methods in a test class inherit the timeout, providing consistent
      defensive coverage without per-test boilerplate.
"""

import json
from uuid import UUID, uuid4

import pytest

# NOTE: These imports will fail until implementation exists - this is expected for TDD
# The implementation should create these classes in omnibase_core/errors/declarative_errors.py


@pytest.mark.timeout(10)
class TestAdapterBindingError:
    """Tests for AdapterBindingError - adapter/handler binding failures."""

    def test_creation_with_basic_message(self) -> None:
        """Test creating AdapterBindingError with minimal args."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError("Failed to bind HTTP adapter")

        assert "Failed to bind HTTP adapter" in str(error)
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_creation_with_all_parameters(self) -> None:
        """Test AdapterBindingError with all optional parameters."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        corr_id = uuid4()
        error = AdapterBindingError(
            "Adapter binding failed",
            error_code=EnumCoreErrorCode.ADAPTER_BINDING_ERROR,
            adapter_type="HTTPHandler",
            contract_path="/path/to/contract.yaml",
            correlation_id=corr_id,
            binding_phase="initialization",
            expected_interface="ProtocolHTTPHandler",
        )

        assert error.correlation_id == corr_id
        assert error.adapter_type == "HTTPHandler"
        assert error.contract_path == "/path/to/contract.yaml"

    def test_model_dump_serialization(self) -> None:
        """Test AdapterBindingError.model_dump() returns correct dict structure."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError(
            "Binding failed",
            adapter_type="KafkaHandler",
            contract_path="/contracts/kafka.yaml",
            binding_phase="validation",
        )

        error_dict = error.model_dump()

        assert error_dict["message"] == "Binding failed"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("adapter_type") == "KafkaHandler"
        assert error_dict["context"].get("contract_path") == "/contracts/kafka.yaml"
        assert error_dict["context"].get("binding_phase") == "validation"

    def test_model_dump_json_serialization(self) -> None:
        """Test AdapterBindingError.model_dump_json() returns valid JSON."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError(
            "JSON serialization test",
            adapter_type="DatabaseAdapter",
        )

        json_str = error.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["message"] == "JSON serialization test"
        assert "context" in parsed
        assert parsed["context"]["adapter_type"] == "DatabaseAdapter"

    def test_default_error_code(self) -> None:
        """Test AdapterBindingError defaults to ADAPTER_BINDING_ERROR code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError("Test error without explicit code")

        assert error.error_code == EnumCoreErrorCode.ADAPTER_BINDING_ERROR

    def test_str_includes_error_code(self) -> None:
        """Test AdapterBindingError __str__ includes error code."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError("Adapter binding failed")

        error_str = str(error)
        assert "[ONEX_CORE_271_ADAPTER_BINDING_ERROR]" in error_str
        assert "Adapter binding failed" in error_str

    def test_inheritance_from_runtime_host_error(self) -> None:
        """Test AdapterBindingError inherits from RuntimeHostError and ModelOnexError."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError
        from omnibase_core.errors.runtime_errors import RuntimeHostError
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = AdapterBindingError("Test inheritance")

        assert isinstance(error, RuntimeHostError)
        assert isinstance(error, ModelOnexError)
        assert isinstance(error, Exception)

    def test_custom_error_code_override(self) -> None:
        """Test AdapterBindingError accepts custom error code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError(
            "Custom code test",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
        )

        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR


@pytest.mark.timeout(10)
class TestPurityViolationError:
    """Tests for PurityViolationError - purity constraint violations."""

    def test_creation_with_basic_message(self) -> None:
        """Test creating PurityViolationError with minimal args."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError("COMPUTE node accessed external state")

        assert "COMPUTE node accessed external state" in str(error)
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_creation_with_all_parameters(self) -> None:
        """Test PurityViolationError with all optional parameters."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import PurityViolationError

        corr_id = uuid4()
        error = PurityViolationError(
            "Purity violation detected",
            error_code=EnumCoreErrorCode.PURITY_VIOLATION_ERROR,
            node_id="node-compute-123",
            violation_type="external_state_access",
            correlation_id=corr_id,
            accessed_resource="database_connection",
            expected_behavior="pure_computation",
        )

        assert error.correlation_id == corr_id
        assert error.node_id == "node-compute-123"
        assert error.violation_type == "external_state_access"

    def test_model_dump_serialization(self) -> None:
        """Test PurityViolationError.model_dump() returns correct dict structure."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError(
            "Side effect detected",
            node_id="node-transform-456",
            violation_type="side_effect",
            detected_at="execute_compute",
        )

        error_dict = error.model_dump()

        assert error_dict["message"] == "Side effect detected"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("node_id") == "node-transform-456"
        assert error_dict["context"].get("violation_type") == "side_effect"
        assert error_dict["context"].get("detected_at") == "execute_compute"

    def test_model_dump_json_serialization(self) -> None:
        """Test PurityViolationError.model_dump_json() returns valid JSON."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError(
            "JSON purity test",
            node_id="node-test-789",
            violation_type="mutation",
        )

        json_str = error.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["message"] == "JSON purity test"
        assert "context" in parsed
        assert parsed["context"]["node_id"] == "node-test-789"
        assert parsed["context"]["violation_type"] == "mutation"

    def test_default_error_code(self) -> None:
        """Test PurityViolationError defaults to PURITY_VIOLATION_ERROR code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError("Test error without explicit code")

        assert error.error_code == EnumCoreErrorCode.PURITY_VIOLATION_ERROR

    def test_str_includes_error_code(self) -> None:
        """Test PurityViolationError __str__ includes error code."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError("Purity constraint violated")

        error_str = str(error)
        assert "[ONEX_CORE_272_PURITY_VIOLATION_ERROR]" in error_str
        assert "Purity constraint violated" in error_str

    def test_inheritance_from_runtime_host_error(self) -> None:
        """Test PurityViolationError inherits from RuntimeHostError and ModelOnexError."""
        from omnibase_core.errors.declarative_errors import PurityViolationError
        from omnibase_core.errors.runtime_errors import RuntimeHostError
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = PurityViolationError("Test inheritance")

        assert isinstance(error, RuntimeHostError)
        assert isinstance(error, ModelOnexError)
        assert isinstance(error, Exception)

    def test_common_violation_types(self) -> None:
        """Test PurityViolationError with common violation type scenarios."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        violation_types = [
            "external_state_access",
            "side_effect",
            "mutation",
            "io_operation",
            "network_call",
            "database_access",
        ]

        for vtype in violation_types:
            error = PurityViolationError(
                f"Violation: {vtype}",
                violation_type=vtype,
            )
            assert error.violation_type == vtype


@pytest.mark.timeout(10)
class TestNodeExecutionError:
    """Tests for NodeExecutionError - node execution phase failures."""

    def test_creation_with_basic_message(self) -> None:
        """Test creating NodeExecutionError with minimal args."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError("Node execution failed during processing")

        assert "Node execution failed during processing" in str(error)
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_creation_with_all_parameters(self) -> None:
        """Test NodeExecutionError with all optional parameters."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        corr_id = uuid4()
        error = NodeExecutionError(
            "Execution error in compute phase",
            error_code=EnumCoreErrorCode.NODE_EXECUTION_ERROR,
            node_id="node-compute-abc",
            execution_phase="compute",
            correlation_id=corr_id,
            input_data="partial_data",
            retry_count=3,
        )

        assert error.correlation_id == corr_id
        assert error.node_id == "node-compute-abc"
        assert error.execution_phase == "compute"

    def test_model_dump_serialization(self) -> None:
        """Test NodeExecutionError.model_dump() returns correct dict structure."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError(
            "Reduce phase failed",
            node_id="node-reducer-xyz",
            execution_phase="reduce",
            error_details="Aggregation timeout",
        )

        error_dict = error.model_dump()

        assert error_dict["message"] == "Reduce phase failed"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("node_id") == "node-reducer-xyz"
        assert error_dict["context"].get("execution_phase") == "reduce"
        assert error_dict["context"].get("error_details") == "Aggregation timeout"

    def test_model_dump_json_serialization(self) -> None:
        """Test NodeExecutionError.model_dump_json() returns valid JSON."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError(
            "JSON execution test",
            node_id="node-effect-123",
            execution_phase="effect",
        )

        json_str = error.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["message"] == "JSON execution test"
        assert "context" in parsed
        assert parsed["context"]["node_id"] == "node-effect-123"
        assert parsed["context"]["execution_phase"] == "effect"

    def test_default_error_code(self) -> None:
        """Test NodeExecutionError defaults to NODE_EXECUTION_ERROR code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError("Test error without explicit code")

        assert error.error_code == EnumCoreErrorCode.NODE_EXECUTION_ERROR

    def test_str_includes_error_code(self) -> None:
        """Test NodeExecutionError __str__ includes error code."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError("Node execution failed")

        error_str = str(error)
        assert "[ONEX_CORE_273_NODE_EXECUTION_ERROR]" in error_str
        assert "Node execution failed" in error_str

    def test_inheritance_from_runtime_host_error(self) -> None:
        """Test NodeExecutionError inherits from RuntimeHostError and ModelOnexError."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError
        from omnibase_core.errors.runtime_errors import RuntimeHostError
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = NodeExecutionError("Test inheritance")

        assert isinstance(error, RuntimeHostError)
        assert isinstance(error, ModelOnexError)
        assert isinstance(error, Exception)

    def test_execution_phases(self) -> None:
        """Test NodeExecutionError with different execution phases."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        phases = [
            "effect",
            "compute",
            "reduce",
            "orchestrate",
            "initialization",
            "validation",
            "cleanup",
        ]

        for phase in phases:
            error = NodeExecutionError(
                f"Error in {phase} phase",
                execution_phase=phase,
            )
            assert error.execution_phase == phase


@pytest.mark.timeout(10)
class TestUnsupportedCapabilityError:
    """Tests for UnsupportedCapabilityError - missing capability errors."""

    def test_creation_with_basic_message(self) -> None:
        """Test creating UnsupportedCapabilityError with minimal args."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError("Node does not support async execution")

        assert "Node does not support async execution" in str(error)
        assert error.correlation_id is not None
        assert isinstance(error.correlation_id, UUID)
        assert isinstance(error, Exception)

    def test_creation_with_all_parameters(self) -> None:
        """Test UnsupportedCapabilityError with all optional parameters."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        corr_id = uuid4()
        error = UnsupportedCapabilityError(
            "Capability not supported",
            error_code=EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR,
            capability="streaming",
            node_type="COMPUTE",
            correlation_id=corr_id,
            required_by="workflow-abc",
            available_capabilities=["sync", "batch"],
        )

        assert error.correlation_id == corr_id
        assert error.capability == "streaming"
        assert error.node_type == "COMPUTE"

    def test_model_dump_serialization(self) -> None:
        """Test UnsupportedCapabilityError.model_dump() returns correct dict structure."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError(
            "Capability missing",
            capability="distributed_execution",
            node_type="ORCHESTRATOR",
            suggested_alternative="local_execution",
        )

        error_dict = error.model_dump()

        assert error_dict["message"] == "Capability missing"
        assert "correlation_id" in error_dict
        assert "context" in error_dict
        assert error_dict["context"].get("capability") == "distributed_execution"
        assert error_dict["context"].get("node_type") == "ORCHESTRATOR"
        assert error_dict["context"].get("suggested_alternative") == "local_execution"

    def test_model_dump_json_serialization(self) -> None:
        """Test UnsupportedCapabilityError.model_dump_json() returns valid JSON."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError(
            "JSON capability test",
            capability="real_time_processing",
            node_type="EFFECT",
        )

        json_str = error.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["message"] == "JSON capability test"
        assert "context" in parsed
        assert parsed["context"]["capability"] == "real_time_processing"
        assert parsed["context"]["node_type"] == "EFFECT"

    def test_default_error_code(self) -> None:
        """Test UnsupportedCapabilityError defaults to UNSUPPORTED_CAPABILITY_ERROR code."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError("Test error without explicit code")

        assert error.error_code == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR

    def test_str_includes_error_code(self) -> None:
        """Test UnsupportedCapabilityError __str__ includes error code."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError("Capability not available")

        error_str = str(error)
        assert "[ONEX_CORE_274_UNSUPPORTED_CAPABILITY_ERROR]" in error_str
        assert "Capability not available" in error_str

    def test_inheritance_from_runtime_host_error(self) -> None:
        """Test UnsupportedCapabilityError inherits from RuntimeHostError and ModelOnexError."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError
        from omnibase_core.errors.runtime_errors import RuntimeHostError
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = UnsupportedCapabilityError("Test inheritance")

        assert isinstance(error, RuntimeHostError)
        assert isinstance(error, ModelOnexError)
        assert isinstance(error, Exception)

    def test_common_capabilities(self) -> None:
        """Test UnsupportedCapabilityError with common capability scenarios."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        capabilities = [
            "async_execution",
            "streaming",
            "distributed",
            "stateful",
            "transactional",
            "idempotent",
            "retryable",
        ]

        for cap in capabilities:
            error = UnsupportedCapabilityError(
                f"Capability {cap} not supported",
                capability=cap,
            )
            assert error.capability == cap


@pytest.mark.timeout(10)
class TestDeclarativeErrorInvariants:
    """Tests for declarative error invariants - consistent behavior across all error types."""

    def test_all_errors_include_correlation_id(self) -> None:
        """Test all declarative errors include auto-generated correlation_id."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        errors = [
            AdapterBindingError("test"),
            PurityViolationError("test"),
            NodeExecutionError("test"),
            UnsupportedCapabilityError("test"),
        ]

        for error in errors:
            assert hasattr(error, "correlation_id")
            assert error.correlation_id is not None
            assert isinstance(error.correlation_id, UUID)

    def test_all_errors_inherit_from_runtime_host_error(self) -> None:
        """Test all declarative errors inherit from RuntimeHostError."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )
        from omnibase_core.errors.runtime_errors import RuntimeHostError

        errors = [
            AdapterBindingError("test"),
            PurityViolationError("test"),
            NodeExecutionError("test"),
            UnsupportedCapabilityError("test"),
        ]

        for error in errors:
            assert isinstance(error, RuntimeHostError)

    def test_all_errors_serializable(self) -> None:
        """Test all declarative errors can be serialized to dict and JSON."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        errors = [
            AdapterBindingError("test", adapter_type="HTTP"),
            PurityViolationError("test", node_id="node-1"),
            NodeExecutionError("test", execution_phase="compute"),
            UnsupportedCapabilityError("test", capability="streaming"),
        ]

        for error in errors:
            # model_dump should work
            error_dict = error.model_dump()
            assert isinstance(error_dict, dict)
            assert "message" in error_dict
            assert "correlation_id" in error_dict

            # model_dump_json should produce valid JSON
            json_str = error.model_dump_json()
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)

    def test_no_raw_stack_traces_in_serialization(self) -> None:
        """Test error serialization doesn't include raw stack traces."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        errors = [
            AdapterBindingError("test"),
            PurityViolationError("test"),
            NodeExecutionError("test"),
            UnsupportedCapabilityError("test"),
        ]

        for error in errors:
            error_dict = error.model_dump()

            # Should not have __traceback__ or raw stack trace
            assert "__traceback__" not in error_dict
            assert "traceback" not in error_dict

    def test_errors_can_be_raised_and_caught(self) -> None:
        """Test all declarative errors can be raised and caught."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        error_classes = [
            AdapterBindingError,
            PurityViolationError,
            NodeExecutionError,
            UnsupportedCapabilityError,
        ]

        for error_class in error_classes:
            with pytest.raises(error_class) as exc_info:
                raise error_class(f"Test {error_class.__name__}")

            assert error_class.__name__ in str(exc_info.value)

    def test_errors_preserve_custom_correlation_id(self) -> None:
        """Test all errors preserve custom correlation_id when provided."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        corr_id = uuid4()

        errors = [
            AdapterBindingError("test", correlation_id=corr_id),
            PurityViolationError("test", correlation_id=corr_id),
            NodeExecutionError("test", correlation_id=corr_id),
            UnsupportedCapabilityError("test", correlation_id=corr_id),
        ]

        for error in errors:
            assert error.correlation_id == corr_id


@pytest.mark.timeout(10)
class TestDeclarativeErrorChaining:
    """Tests for exception chaining with declarative errors."""

    def test_adapter_binding_error_with_cause(self) -> None:
        """Test AdapterBindingError can chain with original cause."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        original = ValueError("Invalid adapter configuration")

        try:
            raise AdapterBindingError(
                "Failed to bind adapter",
                adapter_type="HTTP",
            ) from original
        except AdapterBindingError as error:
            assert error.__cause__ == original
            assert isinstance(error.__cause__, ValueError)

    def test_purity_violation_error_with_cause(self) -> None:
        """Test PurityViolationError can chain with original cause."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        original = RuntimeError("Unexpected state mutation")

        try:
            raise PurityViolationError(
                "Purity violated",
                node_id="node-123",
            ) from original
        except PurityViolationError as error:
            assert error.__cause__ == original

    def test_node_execution_error_with_cause(self) -> None:
        """Test NodeExecutionError can chain with original cause."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        original = TimeoutError("Execution timeout")

        try:
            raise NodeExecutionError(
                "Node execution failed",
                execution_phase="compute",
            ) from original
        except NodeExecutionError as error:
            assert error.__cause__ == original

    def test_unsupported_capability_error_with_cause(self) -> None:
        """Test UnsupportedCapabilityError can chain with original cause."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        original = NotImplementedError("Streaming not implemented")

        try:
            raise UnsupportedCapabilityError(
                "Capability unavailable",
                capability="streaming",
            ) from original
        except UnsupportedCapabilityError as error:
            assert error.__cause__ == original


@pytest.mark.timeout(10)
class TestDeclarativeErrorContextKwargs:
    """Tests for arbitrary context kwargs support in declarative errors."""

    def test_adapter_binding_error_extra_context(self) -> None:
        """Test AdapterBindingError accepts arbitrary context kwargs."""
        from omnibase_core.errors.declarative_errors import AdapterBindingError

        error = AdapterBindingError(
            "Binding failed",
            adapter_type="HTTP",
            retry_count=3,
            timeout_ms=5000,
            endpoint="/api/v1",
        )

        error_dict = error.model_dump()
        context = error_dict["context"]

        assert context.get("retry_count") == 3
        assert context.get("timeout_ms") == 5000
        assert context.get("endpoint") == "/api/v1"

    def test_purity_violation_error_extra_context(self) -> None:
        """Test PurityViolationError accepts arbitrary context kwargs."""
        from omnibase_core.errors.declarative_errors import PurityViolationError

        error = PurityViolationError(
            "Purity violated",
            node_id="node-1",
            violation_type="mutation",
            mutated_field="state.count",
            previous_value=0,
            new_value=1,
        )

        error_dict = error.model_dump()
        context = error_dict["context"]

        assert context.get("mutated_field") == "state.count"
        assert context.get("previous_value") == 0
        assert context.get("new_value") == 1

    def test_node_execution_error_extra_context(self) -> None:
        """Test NodeExecutionError accepts arbitrary context kwargs."""
        from omnibase_core.errors.declarative_errors import NodeExecutionError

        error = NodeExecutionError(
            "Execution failed",
            node_id="node-2",
            execution_phase="reduce",
            input_count=1000,
            processed_count=500,
            failed_at_index=501,
        )

        error_dict = error.model_dump()
        context = error_dict["context"]

        assert context.get("input_count") == 1000
        assert context.get("processed_count") == 500
        assert context.get("failed_at_index") == 501

    def test_unsupported_capability_error_extra_context(self) -> None:
        """Test UnsupportedCapabilityError accepts arbitrary context kwargs."""
        from omnibase_core.errors.declarative_errors import UnsupportedCapabilityError

        error = UnsupportedCapabilityError(
            "Capability not supported",
            capability="streaming",
            node_type="COMPUTE",
            available_modes=["batch", "sync"],
            requested_by="workflow-abc",
            fallback_suggestion="Use EFFECT node instead",
        )

        error_dict = error.model_dump()
        context = error_dict["context"]

        assert context.get("available_modes") == ["batch", "sync"]
        assert context.get("requested_by") == "workflow-abc"
        assert context.get("fallback_suggestion") == "Use EFFECT node instead"


@pytest.mark.timeout(10)
class TestDeclarativeErrorModuleExports:
    """Tests for module-level exports and __all__ definitions."""

    def test_all_errors_importable_from_declarative_errors(self) -> None:
        """Test all error classes can be imported from declarative_errors module."""
        from omnibase_core.errors.declarative_errors import (
            AdapterBindingError,
            NodeExecutionError,
            PurityViolationError,
            UnsupportedCapabilityError,
        )

        # All imports should succeed and be the correct types
        assert AdapterBindingError is not None
        assert PurityViolationError is not None
        assert NodeExecutionError is not None
        assert UnsupportedCapabilityError is not None

    def test_module_has_all_definition(self) -> None:
        """Test declarative_errors module has __all__ with all error classes."""
        from omnibase_core.errors import declarative_errors

        expected_exports = [
            "AdapterBindingError",
            "PurityViolationError",
            "NodeExecutionError",
            "UnsupportedCapabilityError",
        ]

        assert hasattr(declarative_errors, "__all__")
        for export in expected_exports:
            assert export in declarative_errors.__all__
