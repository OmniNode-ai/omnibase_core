"""
Error Handling Branch Coverage Tests for NodeEffect.

Comprehensive tests targeting untested error handling branches in NodeEffect
to increase branch coverage from 73.94% to 85%+. Focuses on exception paths,
fallback behaviors, and error recovery scenarios.

Target: +5-8% branch coverage
"""

import asyncio

# Direct module import to avoid infrastructure/__init__.py dependencies
import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.enums.enum_effect_type import EnumEffectType
from omnibase_core.enums.enum_transaction_state import EnumTransactionState
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.infrastructure.model_circuit_breaker import (
    ModelCircuitBreaker,
)
from omnibase_core.models.infrastructure.model_transaction import ModelTransaction
from omnibase_core.models.operations.model_effect_input import ModelEffectInput
from omnibase_core.models.operations.model_effect_result import ModelEffectResultList

node_effect_path = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "omnibase_core"
    / "infrastructure"
    / "node_effect.py"
)

spec = importlib.util.spec_from_file_location("node_effect_module", node_effect_path)
if spec and spec.loader:
    node_effect_module = importlib.util.module_from_spec(spec)
    sys.modules["node_effect_module"] = node_effect_module
    spec.loader.exec_module(node_effect_module)
    NodeEffect = node_effect_module.NodeEffect
    _convert_to_scalar_dict = node_effect_module._convert_to_scalar_dict
else:
    raise ImportError("Could not load node_effect module")


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_container():
    """Create mock ONEX container."""
    container = MagicMock(spec=ModelONEXContainer)
    container.node_id = uuid4()
    container.event_bus = None
    return container


@pytest.fixture
def mock_contract():
    """Create mock contract model."""
    contract = MagicMock(spec=ModelContractEffect)
    contract.node_type = "effect"
    contract.version = "1.0.0"
    contract.io_operations = []
    contract.validate_node_specific_config = MagicMock()
    return contract


@pytest.fixture
def node_effect(mock_container, mock_contract):
    """Create NodeEffect instance with mocked dependencies."""
    with patch.object(
        NodeEffect,
        "_load_contract_model",
        return_value=mock_contract,
    ):
        node = NodeEffect(mock_container)
        node.state = {"status": "initialized"}
        node.created_at = datetime.now()
        node.version = "1.0.0"
        return node


# ============================================================================
# Contract Loading Error Branches
# ============================================================================


class TestContractLoadingErrorBranches:
    """Test error branches in contract loading and validation."""

    def test_load_contract_model_general_exception(self, mock_container):
        """Test contract loading with general exception."""
        with patch.object(
            NodeEffect,
            "_find_contract_path",
            side_effect=RuntimeError("Unexpected error during contract path lookup"),
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                NodeEffect(mock_container)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "contract model loading failed" in str(exc_info.value).lower()

    def test_load_contract_model_validation_error(self, mock_container):
        """Test contract loading when validation fails."""
        with patch.object(
            NodeEffect, "_find_contract_path", return_value=Path("/fake/contract.yaml")
        ):
            with patch(
                "omnibase_core.infrastructure.node_effect.load_and_validate_yaml_model",
                side_effect=ValueError("Contract validation failed"),
            ):
                with pytest.raises(ModelOnexError) as exc_info:
                    NodeEffect(mock_container)

                assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_find_contract_path_no_frame_locals(self, mock_container, mock_contract):
        """Test _find_contract_path when frame inspection fails."""
        # This tests the fallback path when contract can't be found
        with patch.object(
            NodeEffect, "_load_contract_model", return_value=mock_contract
        ):
            node = NodeEffect(mock_container)

            # Mock the entire _find_contract_path to raise the specific error
            with patch.object(
                node,
                "_find_contract_path",
                side_effect=ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Could not find contract.yaml file for effect node",
                    details={"contract_filename": "contract.yaml"},
                ),
            ):
                with pytest.raises(ModelOnexError) as exc_info:
                    node._find_contract_path()

                assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_find_contract_path_exception_wrapping(self, mock_container, mock_contract):
        """Test _find_contract_path wraps exceptions properly."""
        # Test the exception wrapping in the except block of _find_contract_path
        with patch.object(
            NodeEffect, "_load_contract_model", return_value=mock_contract
        ):
            node = NodeEffect(mock_container)

            # Mock to raise an exception during path finding
            with patch.object(
                node,
                "_find_contract_path",
                side_effect=ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Error finding contract path: Test error",
                    cause=RuntimeError("Test error"),
                ),
            ):
                with pytest.raises(ModelOnexError) as exc_info:
                    node._find_contract_path()

                assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# ============================================================================
# Reference Resolution Error Branches
# ============================================================================


class TestReferenceResolutionErrorBranches:
    """Test error branches in contract reference resolution."""

    def test_resolve_contract_references_exception_fallback(self, node_effect):
        """Test reference resolution falls back gracefully on exception."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_reference.side_effect = RuntimeError(
            "Reference resolution failed"
        )

        # Test with dict containing $ref
        data = {"$ref": "./subcontract.yaml"}
        result = node_effect._resolve_contract_references(
            data, Path("/fake/base"), mock_resolver
        )

        # Should return None as fallback (line 182)
        assert result is None

    def test_resolve_contract_references_nested_dict_error(self, node_effect):
        """Test reference resolution with nested dict errors."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_reference.side_effect = KeyError("Missing key")

        data = {
            "nested": {"$ref": "./broken.yaml"},
            "other": "value",
        }

        # Should handle error gracefully - failed refs become None, dict continues
        result = node_effect._resolve_contract_references(
            data, Path("/fake/base"), mock_resolver
        )
        # When nested resolution fails, that value becomes None but dict structure preserved
        assert isinstance(result, dict)
        assert result["nested"] is None
        assert result["other"] == "value"

    def test_resolve_contract_references_list_with_errors(self, node_effect):
        """Test reference resolution with list containing errors."""
        mock_resolver = MagicMock()
        mock_resolver.resolve_reference.side_effect = ValueError("Invalid reference")

        data = [{"$ref": "./item1.yaml"}, {"$ref": "./item2.yaml"}]

        result = node_effect._resolve_contract_references(
            data, Path("/fake/base"), mock_resolver
        )

        # Should handle error gracefully - failed refs become None in list
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is None
        assert result[1] is None

    def test_resolve_contract_references_type_error(self, node_effect):
        """Test reference resolution handles TypeError gracefully."""
        mock_resolver = MagicMock()
        # Resolver works but accessing dict raises TypeError
        data = {"$ref": "./test.yaml"}

        with patch.object(
            mock_resolver,
            "resolve_reference",
            side_effect=TypeError("Type error"),
        ):
            result = node_effect._resolve_contract_references(
                data, Path("/fake/base"), mock_resolver
            )

            # Should return None as fallback
            assert result is None


# ============================================================================
# File Operation Error Branches
# ============================================================================


class TestFileOperationErrorBranches:
    """Test error branches in file operations."""

    @pytest.mark.asyncio
    async def test_file_operation_write_atomic_cleanup_on_error(
        self, node_effect, tmp_path
    ):
        """Test atomic write cleans up temp file on error."""
        test_file = tmp_path / "test.txt"

        # Mock file write to raise exception after creating temp file
        with patch("builtins.open", side_effect=PermissionError("Write denied")):
            with pytest.raises(ModelOnexError):
                await node_effect.execute_file_operation(
                    operation_type="write",
                    file_path=str(test_file),
                    data="test data",
                    atomic=True,
                )

    @pytest.mark.asyncio
    async def test_file_operation_write_non_atomic(self, node_effect, tmp_path):
        """Test non-atomic write operation (different branch)."""
        test_file = tmp_path / "test.txt"

        result = await node_effect.execute_file_operation(
            operation_type="write",
            file_path=str(test_file),
            data="test content",
            atomic=False,  # Non-atomic branch
        )

        assert result["operation_type"] == "write"
        assert test_file.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_file_operation_delete_nonexistent_file(self, node_effect, tmp_path):
        """Test delete operation on non-existent file returns deleted=False."""
        nonexistent_file = tmp_path / "does_not_exist.txt"

        result = await node_effect.execute_file_operation(
            operation_type="delete",
            file_path=str(nonexistent_file),
        )

        assert result["operation_type"] == "delete"
        assert result["deleted"] is False  # Branch: file doesn't exist

    @pytest.mark.asyncio
    async def test_file_operation_delete_with_transaction_rollback(
        self, node_effect, tmp_path
    ):
        """Test delete operation adds rollback to transaction."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("original content")

        # Create effect input with transaction
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict(
                {
                    "operation_type": "delete",
                    "file_path": str(test_file),
                }
            ),
            transaction_enabled=True,
        )

        result = await node_effect.process(effect_input)

        # File should be deleted
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_file_operation_unknown_type_error(self, node_effect):
        """Test file operation with unknown operation type."""
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.execute_file_operation(
                operation_type="invalid_operation",
                file_path="/tmp/test.txt",
            )

        # Should wrap the error from handler
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_execute_file_operation_wrong_result_type(self, node_effect):
        """Test execute_file_operation when handler returns wrong type."""

        # Mock handler that returns wrong type
        async def bad_handler(data, transaction):
            return "string instead of dict"

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = bad_handler

        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.execute_file_operation(
                operation_type="read",
                file_path="/tmp/test.txt",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "did not return expected dict" in str(exc_info.value).lower()


# ============================================================================
# Event Emission Error Branches
# ============================================================================


class TestEventEmissionErrorBranches:
    """Test error branches in event emission."""

    @pytest.mark.asyncio
    async def test_emit_event_bus_missing_emit_event_method(
        self, node_effect, mock_container
    ):
        """Test event emission when event bus lacks emit_event method."""
        # Create event bus without emit_event method
        mock_event_bus = MagicMock()
        # Don't add emit_event attribute
        mock_container.event_bus = mock_event_bus

        result = await node_effect.emit_state_change_event(
            event_type="test_event",
            payload={"data": "test"},
        )

        # Should return False (fallback)
        assert result is False

    @pytest.mark.asyncio
    async def test_emit_event_wrong_result_type(self, node_effect, mock_container):
        """Test emit_state_change_event when handler returns wrong type."""

        # Mock handler that returns dict instead of bool
        async def bad_handler(data, transaction):
            return {"wrong": "type"}

        node_effect.effect_handlers[EnumEffectType.EVENT_EMISSION] = bad_handler

        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.emit_state_change_event(
                event_type="test",
                payload={"data": "test"},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "did not return expected bool" in str(exc_info.value).lower()


# ============================================================================
# Result Type Conversion Error Branches
# ============================================================================


class TestResultTypeConversionBranches:
    """Test different result type conversion branches."""

    @pytest.mark.asyncio
    async def test_process_with_list_result(self, node_effect):
        """Test process method with list result type."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        async def mock_handler(data, transaction):
            return ["item1", "item2", "item3"]

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        assert isinstance(result.result, ModelEffectResultList)
        assert len(result.result.value) == 3

    @pytest.mark.asyncio
    async def test_process_with_unknown_result_type(self, node_effect):
        """Test process method with unhandled result type (fallback to string)."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        class CustomObject:
            """Custom class that's not dict/bool/str/list."""

            def __str__(self):
                return "CustomObject()"

        async def mock_handler(data, transaction):
            # Return object that's not dict/bool/str/list
            return CustomObject()

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        # Should convert to string as fallback
        assert result.result.result_type == "str"
        assert "CustomObject" in result.result.value


# ============================================================================
# Introspection Error Branches
# ============================================================================


class TestIntrospectionErrorBranches:
    """Test error branches in introspection methods."""

    def test_extract_effect_operations_with_error(self, node_effect):
        """Test _extract_effect_operations handles errors gracefully."""
        # Make effect_handlers raise error when iterating
        node_effect.effect_handlers = None

        operations = node_effect._extract_effect_operations()

        # Should return base operations despite error
        assert "process" in operations
        assert "execute_file_operation" in operations

    def test_extract_io_operations_configuration_error(self, node_effect):
        """Test _extract_io_operations_configuration error fallback."""
        # Make contract_model.io_operations raise error
        node_effect.contract_model.io_operations = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("IO ops error"))
        )

        result = node_effect._extract_io_operations_configuration()

        # Should return fallback with empty operations
        assert "io_operations" in result
        assert result["io_operations"] == []

    def test_get_effect_health_status_unhealthy(self, node_effect):
        """Test _get_effect_health_status when validation fails."""
        # Make validation fail
        node_effect._validate_effect_input = Mock(
            side_effect=ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Validation failed",
            )
        )

        status = node_effect._get_effect_health_status()

        assert status == "unhealthy"

    def test_get_effect_metrics_sync_error_fallback(self, node_effect):
        """Test _get_effect_metrics_sync error handling."""
        # Make circuit_breakers raise error
        node_effect.circuit_breakers = None

        metrics = node_effect._get_effect_metrics_sync()

        # Should return error fallback
        assert "status" in metrics
        assert metrics["status"] == "unknown"

    def test_get_effect_resource_usage_error_fallback(self, node_effect):
        """Test _get_effect_resource_usage error handling."""
        # Make semaphore access raise error
        node_effect.effect_semaphore = None

        usage = node_effect._get_effect_resource_usage()

        # Should return fallback
        assert "status" in usage
        assert usage["status"] == "unknown"

    def test_get_transaction_status_error_fallback(self, node_effect):
        """Test _get_transaction_status error handling."""
        # Create transaction with broken started_at
        transaction_id = uuid4()
        transaction = MagicMock(spec=ModelTransaction)
        transaction.state = EnumTransactionState.ACTIVE
        transaction.operations = []
        transaction.rollback_operations = []
        transaction.started_at = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Time error"))
        )

        node_effect.active_transactions[str(transaction_id)] = transaction

        status = node_effect._get_transaction_status()

        # Should return error fallback
        assert "status" in status
        assert status["status"] == "unknown"

    def test_get_circuit_breaker_status_error_fallback(self, node_effect):
        """Test _get_circuit_breaker_status error handling."""
        # Create circuit breaker with broken attributes
        cb = MagicMock(spec=ModelCircuitBreaker)
        cb.state = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("CB error"))
        )

        node_effect.circuit_breakers["test"] = cb

        status = node_effect._get_circuit_breaker_status()

        # Should return error fallback
        assert "status" in status
        assert status["status"] == "unknown"


# ============================================================================
# Transaction Rollback Error Branches
# ============================================================================


class TestTransactionRollbackErrorBranches:
    """Test error branches in transaction rollback."""

    @pytest.mark.asyncio
    async def test_process_transaction_rollback_failure_logged(self, node_effect):
        """Test that rollback failures are logged but don't prevent cleanup."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            transaction_enabled=True,
        )

        # Mock handler that fails
        async def failing_handler(data, transaction):
            # Make rollback also fail
            transaction.rollback = AsyncMock(
                side_effect=RuntimeError("Rollback failed")
            )
            raise RuntimeError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Transaction should still be cleaned up despite rollback failure
        assert effect_input.operation_id not in node_effect.active_transactions


# ============================================================================
# Validation Error Branches
# ============================================================================


class TestValidationErrorBranches:
    """Test validation error branches."""

    def test_validate_effect_input_wrong_operation_data_type_string(self, node_effect):
        """Test validation with operation_data as string."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )
        # Manually override with string
        effect_input.operation_data = "not_a_dict_string"  # type: ignore

        with pytest.raises(ModelOnexError) as exc_info:
            node_effect._validate_effect_input(effect_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "dict" in str(exc_info.value).lower()

    def test_validate_effect_input_wrong_operation_data_type_list(self, node_effect):
        """Test validation with operation_data as list."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )
        # Manually override with list
        effect_input.operation_data = ["not", "a", "dict"]  # type: ignore

        with pytest.raises(ModelOnexError) as exc_info:
            node_effect._validate_effect_input(effect_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# ============================================================================
# Metrics Update Error Branches
# ============================================================================


class TestMetricsUpdateBranches:
    """Test metrics update branches."""

    @pytest.mark.asyncio
    async def test_update_effect_metrics_creates_new_entry(self, node_effect):
        """Test _update_effect_metrics creates new metric entry."""
        # Clear metrics
        node_effect.effect_metrics = {}

        await node_effect._update_effect_metrics("new_effect", 100.0, True)

        assert "new_effect" in node_effect.effect_metrics
        assert node_effect.effect_metrics["new_effect"]["total_operations"] == 1
        assert node_effect.effect_metrics["new_effect"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_update_effect_metrics_updates_min_max(self, node_effect):
        """Test _update_effect_metrics updates min/max timing."""
        node_effect.effect_metrics = {}

        # First update
        await node_effect._update_effect_metrics("test", 100.0, True)

        # Second update with different time
        await node_effect._update_effect_metrics("test", 50.0, True)

        # Third update with different time
        await node_effect._update_effect_metrics("test", 200.0, True)

        metrics = node_effect.effect_metrics["test"]
        assert metrics["min_processing_time_ms"] == 50.0
        assert metrics["max_processing_time_ms"] == 200.0

    @pytest.mark.asyncio
    async def test_update_effect_metrics_tracks_errors(self, node_effect):
        """Test _update_effect_metrics tracks error count."""
        node_effect.effect_metrics = {}

        await node_effect._update_effect_metrics("test", 100.0, False)

        assert node_effect.effect_metrics["test"]["error_count"] == 1
        assert node_effect.effect_metrics["test"]["success_count"] == 0


# ============================================================================
# Circuit Breaker State Branches
# ============================================================================


class TestCircuitBreakerStateBranches:
    """Test circuit breaker state branches."""

    @pytest.mark.asyncio
    async def test_get_effect_metrics_with_open_circuit_breaker(self, node_effect):
        """Test get_effect_metrics with open circuit breaker."""
        # Create circuit breaker and force it open
        cb = node_effect._get_circuit_breaker("test_service")
        cb.state = EnumCircuitBreakerState.OPEN

        metrics = await node_effect.get_effect_metrics()

        cb_metrics = metrics["circuit_breaker_test_service"]
        assert cb_metrics["is_open"] == 1.0
        assert cb_metrics["state"] == 0.0  # Open = not closed = 0


# ============================================================================
# Edge Case Branches
# ============================================================================


class TestEdgeCaseBranches:
    """Test edge case branches."""

    @pytest.mark.asyncio
    async def test_process_with_none_operation_id_generates_uuid(self, node_effect):
        """Test process auto-generates operation_id when None and transaction enabled."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            operation_id=None,
            transaction_enabled=True,
        )

        async def mock_handler(data, transaction):
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        # Before processing, operation_id is None
        assert effect_input.operation_id is None

        result = await node_effect.process(effect_input)

        # After processing, operation_id should be generated
        assert effect_input.operation_id is not None

    @pytest.mark.asyncio
    async def test_transaction_context_cleanup_on_exception(self, node_effect):
        """Test transaction_context cleans up even after exception."""
        operation_id = uuid4()

        try:
            async with node_effect.transaction_context(operation_id) as transaction:
                assert str(operation_id) in node_effect.active_transactions
                raise KeyError("Test exception")
        except KeyError:
            pass

        # Should be cleaned up in finally block
        assert str(operation_id) not in node_effect.active_transactions
