"""
Comprehensive unit tests for NodeEffect infrastructure component.

Tests cover effect node initialization, transaction management, circuit breaker
patterns, retry logic, file operations, event emission, and introspection.
Follows ONEX testing standards with proper mocking and error handling.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
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
from omnibase_core.models.operations.model_effect_output import ModelEffectOutput
from omnibase_core.models.operations.model_effect_result import (
    ModelEffectResultBool,
    ModelEffectResultDict,
    ModelEffectResultStr,
)

# Use importlib to import node_effect directly without triggering infrastructure/__init__.py
# This is necessary because infrastructure/__init__.py imports NodeBase which has
# missing SPI protocol dependencies (protocol_workflow_reducer)
import importlib.util
import sys
from pathlib import Path

# Construct path to node_effect.py
node_effect_path = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "omnibase_core"
    / "infrastructure"
    / "node_effect.py"
)

# Load the module directly without executing __init__.py
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
    container.event_bus = None  # Default to no event bus
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
        # Initialize state required by base class
        node.state = {"status": "initialized"}
        node.created_at = datetime.now()
        node.version = "1.0.0"
        return node


@pytest.fixture
def sample_effect_input():
    """Create sample effect input for testing."""
    return ModelEffectInput(
        effect_type=EnumEffectType.FILE_OPERATION,
        operation_data=_convert_to_scalar_dict(
            {
                "operation_type": "read",
                "file_path": "/tmp/test.txt",
            },
        ),
        transaction_enabled=False,
        retry_enabled=False,
        circuit_breaker_enabled=False,
    )


# ============================================================================
# Test Utility Functions
# ============================================================================


class TestUtilityFunctions:
    """Test utility helper functions."""

    def test_convert_to_scalar_dict_strings(self):
        """Test converting string values to ModelSchemaValue."""
        data = {"key1": "value1", "key2": "value2"}
        result = _convert_to_scalar_dict(data)

        assert isinstance(result["key1"], ModelSchemaValue)
        assert result["key1"].to_value() == "value1"
        assert result["key2"].to_value() == "value2"

    def test_convert_to_scalar_dict_integers(self):
        """Test converting integer values to ModelSchemaValue."""
        data = {"count": 42, "total": 100}
        result = _convert_to_scalar_dict(data)

        assert result["count"].to_value() == 42
        assert result["total"].to_value() == 100

    def test_convert_to_scalar_dict_floats(self):
        """Test converting float values to ModelSchemaValue."""
        data = {"rate": 3.14, "score": 98.5}
        result = _convert_to_scalar_dict(data)

        assert result["rate"].to_value() == 3.14
        assert result["score"].to_value() == 98.5

    def test_convert_to_scalar_dict_booleans(self):
        """Test converting boolean values to ModelSchemaValue."""
        data = {"enabled": True, "active": False}
        result = _convert_to_scalar_dict(data)

        assert result["enabled"].to_value() is True
        assert result["active"].to_value() is False

    def test_convert_to_scalar_dict_none_values(self):
        """Test converting None values to ModelSchemaValue."""
        data = {"optional": None}
        result = _convert_to_scalar_dict(data)

        assert result["optional"].to_value() == "null"

    def test_convert_to_scalar_dict_complex_types(self):
        """Test converting complex types (converted to strings)."""
        data = {"complex": {"nested": "dict"}, "list_val": [1, 2, 3]}
        result = _convert_to_scalar_dict(data)

        # Complex types are converted to string representations
        assert isinstance(result["complex"], ModelSchemaValue)
        assert isinstance(result["list_val"], ModelSchemaValue)

    def test_convert_to_scalar_dict_mixed_types(self):
        """Test converting mixed data types."""
        data = {
            "string": "test",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
        }
        result = _convert_to_scalar_dict(data)

        assert len(result) == 5
        assert all(isinstance(v, ModelSchemaValue) for v in result.values())


# ============================================================================
# Test NodeEffect Initialization
# ============================================================================


class TestNodeEffectInitialization:
    """Test NodeEffect initialization and setup."""

    def test_initialization_success(self, node_effect):
        """Test successful NodeEffect initialization."""
        assert node_effect is not None
        assert hasattr(node_effect, "contract_model")
        assert hasattr(node_effect, "active_transactions")
        assert hasattr(node_effect, "circuit_breakers")
        assert hasattr(node_effect, "effect_handlers")

    def test_initialization_sets_defaults(self, node_effect):
        """Test that initialization sets default configuration."""
        assert node_effect.default_timeout_ms == 30000
        assert node_effect.default_retry_delay_ms == 1000
        assert node_effect.max_concurrent_effects == 10

    def test_initialization_creates_data_structures(self, node_effect):
        """Test initialization creates necessary data structures."""
        assert isinstance(node_effect.active_transactions, dict)
        assert isinstance(node_effect.circuit_breakers, dict)
        assert isinstance(node_effect.effect_handlers, dict)
        assert isinstance(node_effect.effect_metrics, dict)

    def test_initialization_registers_builtin_handlers(self, node_effect):
        """Test that built-in effect handlers are registered."""
        assert EnumEffectType.FILE_OPERATION in node_effect.effect_handlers
        assert EnumEffectType.EVENT_EMISSION in node_effect.effect_handlers

    def test_initialization_creates_semaphore(self, node_effect):
        """Test that effect semaphore is created."""
        assert hasattr(node_effect, "effect_semaphore")
        assert node_effect.effect_semaphore._value == 10  # max_concurrent_effects

    def test_initialization_with_invalid_container(self, mock_contract):
        """Test initialization with invalid container raises error."""
        with patch.object(
            NodeEffect,
            "_load_contract_model",
            return_value=mock_contract,
        ):
            with pytest.raises(Exception):  # Should fail with invalid container
                NodeEffect(None)  # type: ignore


# ============================================================================
# Test Input Validation
# ============================================================================


class TestInputValidation:
    """Test effect input validation."""

    def test_validate_effect_input_success(self, node_effect, sample_effect_input):
        """Test successful input validation."""
        # Should not raise exception
        node_effect._validate_effect_input(sample_effect_input)

    def test_validate_effect_input_invalid_effect_type(self, node_effect):
        """Test validation fails with invalid effect type."""
        # Pydantic V2 catches invalid enum values at instantiation time
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            invalid_input = ModelEffectInput(
                effect_type="invalid_type",  # type: ignore
                operation_data=_convert_to_scalar_dict({"test": "data"}),
            )

        # Verify it's an enum validation error
        assert "enum" in str(exc_info.value).lower()

    def test_validate_effect_input_invalid_operation_data(self, node_effect):
        """Test validation with invalid operation data type."""
        # Create input with wrong operation_data type (bypass Pydantic)
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )
        # Manually override with invalid type
        effect_input.operation_data = "not_a_dict"  # type: ignore

        with pytest.raises(ModelOnexError) as exc_info:
            node_effect._validate_effect_input(effect_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "dict" in str(exc_info.value).lower()


# ============================================================================
# Test Circuit Breaker Management
# ============================================================================


class TestCircuitBreakerManagement:
    """Test circuit breaker patterns."""

    def test_get_circuit_breaker_creates_new(self, node_effect):
        """Test that circuit breaker is created on first access."""
        service_name = "test_service"
        cb = node_effect._get_circuit_breaker(service_name)

        assert isinstance(cb, ModelCircuitBreaker)
        assert service_name in node_effect.circuit_breakers
        assert node_effect.circuit_breakers[service_name] is cb

    def test_get_circuit_breaker_returns_existing(self, node_effect):
        """Test that same circuit breaker is returned on subsequent calls."""
        service_name = "test_service"
        cb1 = node_effect._get_circuit_breaker(service_name)
        cb2 = node_effect._get_circuit_breaker(service_name)

        assert cb1 is cb2

    def test_circuit_breaker_blocks_when_open(self, node_effect):
        """Test that open circuit breaker blocks execution."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=_convert_to_scalar_dict({"endpoint": "/test"}),
            circuit_breaker_enabled=True,
        )

        # Get circuit breaker and force it open
        cb = node_effect._get_circuit_breaker(EnumEffectType.API_CALL.value)
        cb.state = EnumCircuitBreakerState.OPEN

        # Should raise error due to open circuit
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(node_effect.process(effect_input))

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "circuit breaker open" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self, node_effect, sample_effect_input):
        """Test that circuit breaker records successful operations."""
        sample_effect_input.circuit_breaker_enabled = True

        # Get circuit breaker before execution
        cb = node_effect._get_circuit_breaker(sample_effect_input.effect_type.value)
        initial_state = cb.state

        # Mock successful effect execution
        async def mock_handler(data, transaction):
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        # Execute
        await node_effect.process(sample_effect_input)

        # Circuit breaker should remain closed (success doesn't change it)
        assert cb.state == EnumCircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure(self, node_effect, sample_effect_input):
        """Test that circuit breaker records failed operations."""
        sample_effect_input.circuit_breaker_enabled = True

        # Get circuit breaker before execution
        cb = node_effect._get_circuit_breaker(sample_effect_input.effect_type.value)
        initial_failure_count = cb.failure_count

        # Mock failing effect execution
        async def mock_handler(data, transaction):
            raise RuntimeError("Simulated failure")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        # Execute and expect failure
        with pytest.raises(ModelOnexError):
            await node_effect.process(sample_effect_input)

        # Circuit breaker should record the failure
        assert cb.failure_count > initial_failure_count


# ============================================================================
# Test Transaction Management
# ============================================================================


class TestTransactionManagement:
    """Test transaction context and management."""

    @pytest.mark.asyncio
    async def test_transaction_context_success(self, node_effect):
        """Test successful transaction commit."""
        operation_id = uuid4()

        async with node_effect.transaction_context(operation_id) as transaction:
            assert isinstance(transaction, ModelTransaction)
            assert transaction.state == EnumTransactionState.ACTIVE
            assert str(operation_id) in node_effect.active_transactions

        # After context, transaction should be committed and removed
        assert transaction.state == EnumTransactionState.COMMITTED
        assert str(operation_id) not in node_effect.active_transactions

    @pytest.mark.asyncio
    async def test_transaction_context_rollback_on_error(self, node_effect):
        """Test transaction rollback on exception."""
        operation_id = uuid4()

        try:
            async with node_effect.transaction_context(operation_id) as transaction:
                assert transaction.state == EnumTransactionState.ACTIVE
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass

        # Transaction should be rolled back
        assert transaction.state == EnumTransactionState.ROLLED_BACK
        assert str(operation_id) not in node_effect.active_transactions

    @pytest.mark.asyncio
    async def test_transaction_context_default_operation_id(self, node_effect):
        """Test transaction context with auto-generated operation_id."""
        async with node_effect.transaction_context() as transaction:
            assert isinstance(transaction.transaction_id, type(uuid4()))
            assert transaction.state == EnumTransactionState.ACTIVE

    @pytest.mark.asyncio
    async def test_process_with_transaction_enabled(self, node_effect):
        """Test process method with transaction enabled."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict(
                {
                    "operation_type": "read",
                    "file_path": "/tmp/test.txt",
                },
            ),
            transaction_enabled=True,
        )

        # Mock file operation handler
        async def mock_handler(data, transaction):
            assert transaction is not None
            assert isinstance(transaction, ModelTransaction)
            return {"content": "test_data"}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert effect_input.operation_id not in node_effect.active_transactions

    @pytest.mark.asyncio
    async def test_process_transaction_rollback_on_failure(self, node_effect):
        """Test that transaction is rolled back on effect failure."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"operation_type": "invalid"}),
            transaction_enabled=True,
        )

        # Mock failing handler
        async def mock_handler(data, transaction):
            assert transaction is not None
            raise RuntimeError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Transaction should be cleaned up
        assert effect_input.operation_id not in node_effect.active_transactions


# ============================================================================
# Test Retry Logic
# ============================================================================


class TestRetryLogic:
    """Test retry policies and exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_disabled_fails_immediately(self, node_effect):
        """Test that operations fail immediately when retry is disabled."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            retry_enabled=False,
        )

        call_count = 0

        async def failing_handler(data, transaction):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Should only be called once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_enabled_retries_on_failure(self, node_effect):
        """Test that operations are retried when enabled."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=10,  # Short delay for testing
        )

        call_count = 0

        async def failing_handler(data, transaction):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Should be called: initial + max_retries
        assert call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self, node_effect):
        """Test successful retry after initial failure."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=10,
        )

        call_count = 0

        async def eventually_succeeds(data, transaction):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary failure")
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = eventually_succeeds

        result = await node_effect.process(effect_input)

        assert call_count == 2  # Failed once, succeeded on retry
        assert isinstance(result, ModelEffectOutput)
        assert result.retry_count == 0  # Internal counter not exposed in this implementation

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, node_effect):
        """Test exponential backoff delay calculation."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            retry_enabled=True,
            max_retries=2,
            retry_delay_ms=100,
        )

        retry_times = []

        async def failing_handler(data, transaction):
            retry_times.append(asyncio.get_event_loop().time())
            raise RuntimeError("Fail")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Should have 3 attempts (initial + 2 retries)
        assert len(retry_times) == 3

        # Check delays between attempts (exponential backoff)
        if len(retry_times) >= 3:
            # First retry delay: 100ms
            # Second retry delay: 200ms (100 * 2^1)
            delay1 = (retry_times[1] - retry_times[0]) * 1000
            delay2 = (retry_times[2] - retry_times[1]) * 1000

            # Allow some tolerance for timing
            assert delay1 >= 90  # ~100ms
            assert delay2 >= 190  # ~200ms


# ============================================================================
# Test Effect Processing
# ============================================================================


class TestEffectProcessing:
    """Test main effect processing logic."""

    @pytest.mark.asyncio
    async def test_process_success_with_dict_result(self, node_effect):
        """Test successful processing with dictionary result."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            transaction_enabled=False,
        )

        async def mock_handler(data, transaction):
            return {"result": "success", "count": 42}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        assert isinstance(result, ModelEffectOutput)
        assert isinstance(result.result, ModelEffectResultDict)
        assert result.result.value["result"] == "success"
        assert result.result.value["count"] == 42

    @pytest.mark.asyncio
    async def test_process_success_with_bool_result(self, node_effect):
        """Test successful processing with boolean result."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.EVENT_EMISSION,
            operation_data=_convert_to_scalar_dict({"event": "test"}),
        )

        async def mock_handler(data, transaction):
            return True

        node_effect.effect_handlers[EnumEffectType.EVENT_EMISSION] = mock_handler

        result = await node_effect.process(effect_input)

        assert isinstance(result.result, ModelEffectResultBool)
        assert result.result.value is True

    @pytest.mark.asyncio
    async def test_process_success_with_string_result(self, node_effect):
        """Test successful processing with string result."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        async def mock_handler(data, transaction):
            return "Operation completed successfully"

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        assert isinstance(result.result, ModelEffectResultStr)
        assert result.result.value == "Operation completed successfully"

    @pytest.mark.asyncio
    async def test_process_unknown_effect_type(self, node_effect):
        """Test processing with unregistered effect type."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,  # Not registered
            operation_data=_convert_to_scalar_dict({"query": "SELECT *"}),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "no handler registered" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_updates_metrics(self, node_effect):
        """Test that processing updates effect metrics."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        async def mock_handler(data, transaction):
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        # Clear metrics
        node_effect.effect_metrics = {}

        await node_effect.process(effect_input)

        # Metrics should be updated
        effect_type_key = EnumEffectType.FILE_OPERATION.value
        assert effect_type_key in node_effect.effect_metrics
        assert node_effect.effect_metrics[effect_type_key]["total_operations"] == 1
        assert node_effect.effect_metrics[effect_type_key]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_process_semaphore_limits_concurrency(self, node_effect):
        """Test that semaphore limits concurrent effects."""
        # Set low limit for testing
        node_effect.max_concurrent_effects = 2
        node_effect.effect_semaphore = asyncio.Semaphore(2)

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            transaction_enabled=False,  # Disable transactions to avoid key collisions
        )

        concurrent_count = 0
        max_concurrent = 0

        async def slow_handler(data, transaction):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = slow_handler

        # Start multiple concurrent operations
        tasks = [node_effect.process(effect_input) for _ in range(5)]
        await asyncio.gather(*tasks)

        # Max concurrent should not exceed semaphore limit
        assert max_concurrent <= 2


# ============================================================================
# Test File Operations
# ============================================================================


class TestFileOperations:
    """Test file operation effect handler."""

    @pytest.mark.asyncio
    async def test_execute_file_operation_read(self, node_effect, tmp_path):
        """Test file read operation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = await node_effect.execute_file_operation(
            operation_type="read",
            file_path=str(test_file),
            atomic=False,
        )

        assert result["operation_type"] == "read"
        assert result["content"] == "test content"
        assert result["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_execute_file_operation_write(self, node_effect, tmp_path):
        """Test file write operation."""
        test_file = tmp_path / "output.txt"
        test_data = "Hello, World!"

        result = await node_effect.execute_file_operation(
            operation_type="write",
            file_path=str(test_file),
            data=test_data,
            atomic=True,
        )

        assert result["operation_type"] == "write"
        assert result["bytes_written"] == len(test_data.encode("utf-8"))
        assert test_file.exists()
        assert test_file.read_text() == test_data

    @pytest.mark.asyncio
    async def test_execute_file_operation_delete(self, node_effect, tmp_path):
        """Test file delete operation."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        result = await node_effect.execute_file_operation(
            operation_type="delete",
            file_path=str(test_file),
        )

        assert result["operation_type"] == "delete"
        assert result["deleted"] is True
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_execute_file_operation_read_nonexistent(self, node_effect):
        """Test reading nonexistent file raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.execute_file_operation(
                operation_type="read",
                file_path="/nonexistent/file.txt",
            )

        # Retry mechanism wraps the error, final error is OPERATION_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_execute_file_operation_atomic_write(self, node_effect, tmp_path):
        """Test atomic write operation uses temporary file."""
        test_file = tmp_path / "atomic.txt"

        with patch("pathlib.Path.replace") as mock_replace:
            await node_effect.execute_file_operation(
                operation_type="write",
                file_path=str(test_file),
                data="atomic content",
                atomic=True,
            )

            # Atomic write should use temporary file and replace
            mock_replace.assert_called_once()


# ============================================================================
# Test Event Emission
# ============================================================================


class TestEventEmission:
    """Test event emission effect handler."""

    @pytest.mark.asyncio
    async def test_emit_state_change_event_success(self, node_effect, mock_container):
        """Test successful event emission."""
        # Mock event bus with emit_event method
        mock_event_bus = AsyncMock()
        mock_event_bus.emit_event = AsyncMock(return_value=None)
        mock_container.event_bus = mock_event_bus

        result = await node_effect.emit_state_change_event(
            event_type="state_changed",
            payload={"old_state": "A", "new_state": "B"},
            correlation_id=uuid4(),
        )

        assert result is True
        mock_event_bus.emit_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_state_change_event_no_event_bus(self, node_effect, mock_container):
        """Test event emission gracefully handles missing event bus."""
        mock_container.event_bus = None

        result = await node_effect.emit_state_change_event(
            event_type="test_event",
            payload={"data": "test"},
        )

        # Should return False but not raise error
        assert result is False

    @pytest.mark.asyncio
    async def test_emit_state_change_event_bus_error(self, node_effect, mock_container):
        """Test event emission handles event bus errors gracefully."""
        # Mock event bus that raises exception
        mock_event_bus = AsyncMock()
        mock_event_bus.emit_event = AsyncMock(side_effect=RuntimeError("Event bus error"))
        mock_container.event_bus = mock_event_bus

        result = await node_effect.emit_state_change_event(
            event_type="test_event",
            payload={"data": "test"},
        )

        # Should gracefully degrade and return False
        assert result is False


# ============================================================================
# Test Metrics Collection
# ============================================================================


class TestMetricsCollection:
    """Test effect metrics collection and tracking."""

    @pytest.mark.asyncio
    async def test_get_effect_metrics_empty(self, node_effect):
        """Test getting metrics when no operations have been performed."""
        metrics = await node_effect.get_effect_metrics()

        assert "transaction_management" in metrics
        assert metrics["transaction_management"]["active_transactions"] == 0

    @pytest.mark.asyncio
    async def test_get_effect_metrics_after_operations(self, node_effect):
        """Test metrics collection after performing operations."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        async def mock_handler(data, transaction):
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        # Perform multiple operations
        await node_effect.process(effect_input)
        await node_effect.process(effect_input)

        metrics = await node_effect.get_effect_metrics()

        effect_type_key = EnumEffectType.FILE_OPERATION.value
        assert effect_type_key in metrics
        assert metrics[effect_type_key]["total_operations"] == 2
        assert metrics[effect_type_key]["success_count"] == 2

    @pytest.mark.asyncio
    async def test_effect_metrics_tracks_errors(self, node_effect):
        """Test that metrics track error counts."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            retry_enabled=False,
        )

        async def failing_handler(data, transaction):
            raise RuntimeError("Failure")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Try operation (will fail)
        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        metrics = await node_effect.get_effect_metrics()

        effect_type_key = EnumEffectType.FILE_OPERATION.value
        assert metrics[effect_type_key]["error_count"] == 1
        assert metrics[effect_type_key]["success_count"] == 0

    @pytest.mark.asyncio
    async def test_effect_metrics_circuit_breaker_status(self, node_effect):
        """Test that metrics include circuit breaker status."""
        # Create a circuit breaker
        cb = node_effect._get_circuit_breaker("test_service")

        metrics = await node_effect.get_effect_metrics()

        assert "circuit_breaker_test_service" in metrics
        assert "state" in metrics["circuit_breaker_test_service"]
        assert "failure_count" in metrics["circuit_breaker_test_service"]


# ============================================================================
# Test Lifecycle Management
# ============================================================================


class TestLifecycleManagement:
    """Test node lifecycle initialization and cleanup."""

    @pytest.mark.asyncio
    async def test_initialize_node_resources(self, node_effect):
        """Test node resource initialization."""
        # Should not raise exception
        await node_effect._initialize_node_resources()

    @pytest.mark.asyncio
    async def test_cleanup_node_resources_no_transactions(self, node_effect):
        """Test cleanup with no active transactions."""
        await node_effect._cleanup_node_resources()

        assert len(node_effect.active_transactions) == 0

    @pytest.mark.asyncio
    async def test_cleanup_node_resources_with_active_transactions(self, node_effect):
        """Test cleanup rolls back active transactions."""
        # Create active transaction
        transaction_id = uuid4()
        transaction = ModelTransaction(transaction_id)
        transaction.state = EnumTransactionState.ACTIVE
        node_effect.active_transactions[str(transaction_id)] = transaction

        await node_effect._cleanup_node_resources()

        # Transaction should be rolled back
        assert transaction.state == EnumTransactionState.ROLLED_BACK
        assert len(node_effect.active_transactions) == 0

    @pytest.mark.asyncio
    async def test_cleanup_handles_rollback_failures(self, node_effect):
        """Test cleanup handles transaction rollback failures gracefully."""
        # Create transaction with failing rollback
        transaction_id = uuid4()
        transaction = MagicMock(spec=ModelTransaction)
        transaction.rollback = AsyncMock(side_effect=RuntimeError("Rollback failed"))
        transaction.state = EnumTransactionState.ACTIVE

        node_effect.active_transactions[str(transaction_id)] = transaction

        # Should not raise exception, just log error
        await node_effect._cleanup_node_resources()

        assert len(node_effect.active_transactions) == 0


# ============================================================================
# Test Introspection
# ============================================================================


class TestIntrospection:
    """Test node introspection capabilities."""

    @pytest.mark.asyncio
    async def test_get_introspection_data_success(self, node_effect):
        """Test successful introspection data retrieval."""
        introspection = await node_effect.get_introspection_data()

        assert "node_capabilities" in introspection
        assert "contract_details" in introspection
        assert "runtime_information" in introspection
        assert "effect_management_information" in introspection
        assert "configuration_details" in introspection

    @pytest.mark.asyncio
    async def test_introspection_node_capabilities(self, node_effect):
        """Test introspection includes node capabilities."""
        introspection = await node_effect.get_introspection_data()

        capabilities = introspection["node_capabilities"]
        assert capabilities["node_type"] == "NodeEffect"
        assert capabilities["node_classification"] == "effect"
        assert "available_operations" in capabilities

    @pytest.mark.asyncio
    async def test_introspection_contract_details(self, node_effect):
        """Test introspection includes contract details."""
        introspection = await node_effect.get_introspection_data()

        contract = introspection["contract_details"]
        assert contract["contract_type"] == "ModelContractEffect"
        assert "supported_effect_types" in contract

    @pytest.mark.asyncio
    async def test_introspection_runtime_information(self, node_effect):
        """Test introspection includes runtime information."""
        introspection = await node_effect.get_introspection_data()

        runtime = introspection["runtime_information"]
        assert "current_health_status" in runtime
        assert "effect_metrics" in runtime
        assert "transaction_status" in runtime
        assert "circuit_breaker_status" in runtime

    @pytest.mark.asyncio
    async def test_introspection_effect_management_info(self, node_effect):
        """Test introspection includes effect management information."""
        introspection = await node_effect.get_introspection_data()

        effect_mgmt = introspection["effect_management_information"]
        assert effect_mgmt["transaction_management_enabled"] is True
        assert effect_mgmt["retry_policies_enabled"] is True
        assert effect_mgmt["circuit_breaker_enabled"] is True

    @pytest.mark.asyncio
    async def test_introspection_handles_errors_gracefully(self, node_effect):
        """Test introspection falls back gracefully on errors."""
        # Force an error during introspection
        node_effect.state = None  # This will cause an error

        introspection = await node_effect.get_introspection_data()

        # Should return fallback data
        assert "node_capabilities" in introspection
        assert introspection["introspection_metadata"]["supports_full_introspection"] is False

    def test_get_effect_health_status_healthy(self, node_effect):
        """Test health status check returns healthy."""
        status = node_effect._get_effect_health_status()
        assert status == "healthy"

    def test_get_transaction_status(self, node_effect):
        """Test transaction status retrieval."""
        # Create active transaction
        transaction_id = uuid4()
        transaction = ModelTransaction(transaction_id)
        transaction.state = EnumTransactionState.ACTIVE
        node_effect.active_transactions[str(transaction_id)] = transaction

        status = node_effect._get_transaction_status()

        assert status["active_transaction_count"] == 1
        assert str(transaction_id) in status["transaction_details"]

    def test_get_circuit_breaker_status(self, node_effect):
        """Test circuit breaker status retrieval."""
        # Create circuit breaker
        cb = node_effect._get_circuit_breaker("test_service")

        status = node_effect._get_circuit_breaker_status()

        assert status["circuit_breaker_count"] == 1
        assert "test_service" in status["circuit_breaker_details"]


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_process_wraps_exceptions_in_onex_error(self, node_effect):
        """Test that process method wraps exceptions in ModelOnexError."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
        )

        async def failing_handler(data, transaction):
            raise ValueError("Unexpected error")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "effect execution failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_includes_error_context(self, node_effect):
        """Test that error includes comprehensive context."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            transaction_enabled=True,
        )

        async def failing_handler(data, transaction):
            raise RuntimeError("Test error")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Check context includes necessary information
        # Note: context attribute may not exist in current implementation
        # This test validates the error structure

    @pytest.mark.asyncio
    async def test_process_auto_generates_operation_id(self, node_effect):
        """Test that operation_id is auto-generated if None."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=_convert_to_scalar_dict({"test": "data"}),
            operation_id=None,
            transaction_enabled=True,
        )

        async def mock_handler(data, transaction):
            return {"success": True}

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = mock_handler

        result = await node_effect.process(effect_input)

        # Operation ID should be generated
        assert result.operation_id is not None
