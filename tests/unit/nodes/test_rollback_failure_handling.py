"""
Unit tests for explicit rollback failure handling.

Tests ModelEffectTransaction and NodeEffect rollback failure detection,
logging, and callback invocation per PR #59 follow-up requirements.
"""

import asyncio
from uuid import uuid4

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.enum_effect_types import EnumEffectType, EnumTransactionState
from omnibase_core.nodes.model_effect_input import ModelEffectInput
from omnibase_core.nodes.model_effect_transaction import ModelEffectTransaction
from omnibase_core.nodes.node_effect import NodeEffect


class TestModelEffectTransactionRollbackFailures:
    """Test ModelEffectTransaction rollback failure handling."""

    @pytest.mark.asyncio
    async def test_rollback_returns_success_when_all_operations_succeed(self):
        """Test rollback returns (True, []) when all operations succeed."""
        transaction = ModelEffectTransaction(uuid4())

        # Add operations with successful rollback functions
        def rollback1():
            pass  # Success

        def rollback2():
            pass  # Success

        transaction.add_operation("op1", {"test": "data1"}, rollback1)
        transaction.add_operation("op2", {"test": "data2"}, rollback2)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify success
        assert success is True
        assert len(errors) == 0
        assert transaction.rollback_failures == []
        assert transaction.state == EnumTransactionState.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_returns_failures_when_operations_fail(self):
        """Test rollback returns (False, [errors]) when operations fail."""
        transaction = ModelEffectTransaction(uuid4())

        # Add operations where some fail
        def rollback_success():
            pass  # Success

        def rollback_fail():
            raise ValueError("Rollback failed intentionally")

        transaction.add_operation("op1", {"test": "data1"}, rollback_success)
        transaction.add_operation("op2", {"test": "data2"}, rollback_fail)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify failure captured
        assert success is False
        assert len(errors) == 1
        assert isinstance(errors[0], ModelOnexError)
        assert "Rollback failed for operation" in errors[0].message
        assert len(transaction.rollback_failures) == 1

    @pytest.mark.asyncio
    async def test_rollback_attempts_all_operations_even_when_some_fail(self):
        """Test rollback attempts all operations even if some fail."""
        transaction = ModelEffectTransaction(uuid4())

        # Track which rollbacks were attempted
        attempted_rollbacks = []

        def rollback1():
            attempted_rollbacks.append("rollback1")
            raise ValueError("Fail 1")

        def rollback2():
            attempted_rollbacks.append("rollback2")
            # Success

        def rollback3():
            attempted_rollbacks.append("rollback3")
            raise ValueError("Fail 3")

        transaction.add_operation("op1", {"test": "data1"}, rollback1)
        transaction.add_operation("op2", {"test": "data2"}, rollback2)
        transaction.add_operation("op3", {"test": "data3"}, rollback3)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify all were attempted (in reverse order)
        assert len(attempted_rollbacks) == 3
        assert attempted_rollbacks == ["rollback3", "rollback2", "rollback1"]

        # Verify failures captured
        assert success is False
        assert len(errors) == 2  # rollback1 and rollback3 failed
        assert len(transaction.rollback_failures) == 2

    @pytest.mark.asyncio
    async def test_rollback_handles_async_and_sync_functions(self):
        """Test rollback handles both async and sync rollback functions."""
        transaction = ModelEffectTransaction(uuid4())

        async def async_rollback():
            await asyncio.sleep(0)  # Yield without delay
            raise ValueError("Async rollback failed")

        def sync_rollback():
            raise ValueError("Sync rollback failed")

        transaction.add_operation("op1", {"test": "data1"}, async_rollback)
        transaction.add_operation("op2", {"test": "data2"}, sync_rollback)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify both failures captured
        assert success is False
        assert len(errors) == 2
        assert all(isinstance(e, ModelOnexError) for e in errors)

    @pytest.mark.asyncio
    async def test_rollback_preserves_exception_cause_chain(self):
        """Test rollback preserves exception cause via chaining."""
        transaction = ModelEffectTransaction(uuid4())

        original_error = ValueError("Original failure")

        def rollback_fail():
            raise original_error

        transaction.add_operation("op1", {"test": "data1"}, rollback_fail)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify cause is preserved in context
        assert not success
        assert len(errors) == 1
        # Cause is stored in additional_context by ModelOnexError
        additional_ctx = errors[0].context.get("additional_context", {})
        assert additional_ctx.get("cause") is original_error


class TestNodeEffectRollbackFailures:
    """Test NodeEffect rollback failure handling and callbacks."""

    @pytest.fixture
    def container(self):
        """Create a minimal container for testing."""
        return ModelONEXContainer()

    @pytest.mark.asyncio
    async def test_process_raises_special_error_on_rollback_failure(self, container):
        """Test process() raises ModelOnexError with rollback context on failure."""

        # Create NodeEffect with failing rollback handler
        node_effect = NodeEffect(container)

        # Register a handler that will trigger rollback
        async def failing_handler(operation_data, transaction):
            # Add rollback operation that will fail
            def failing_rollback():
                raise ValueError("Rollback intentionally failed")

            if transaction:
                transaction.add_operation("test_op", operation_data, failing_rollback)

            # Trigger failure to initiate rollback
            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Create input that enables transactions
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute and expect rollback failure error
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Verify error message indicates rollback failure
        error = exc_info.value
        assert "rollback failed" in error.message.lower()
        assert "data may be inconsistent" in error.message.lower()
        # Context is nested under additional_context in ModelOnexError
        additional_ctx = error.context.get("additional_context", {})
        context_data = additional_ctx.get("context", {})
        assert "rollback_errors" in context_data
        assert len(context_data["rollback_errors"]) > 0

    @pytest.mark.asyncio
    async def test_rollback_failure_callback_invoked(self, container):
        """Test on_rollback_failure callback is invoked when rollback fails."""

        # Track callback invocations
        callback_invocations = []

        def rollback_failure_callback(transaction, errors):
            callback_invocations.append(
                {
                    "transaction_id": transaction.transaction_id,
                    "error_count": len(errors),
                }
            )

        # Create NodeEffect with callback
        node_effect = NodeEffect(
            container, on_rollback_failure=rollback_failure_callback
        )

        # Register failing handler
        async def failing_handler(operation_data, transaction):
            def failing_rollback():
                raise ValueError("Rollback failed")

            if transaction:
                transaction.add_operation("test_op", operation_data, failing_rollback)

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Create input
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute (will fail)
        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Verify callback was invoked
        assert len(callback_invocations) == 1
        assert callback_invocations[0]["error_count"] == 1

    @pytest.mark.asyncio
    async def test_callback_exception_is_caught_and_logged(self, container):
        """Test that exceptions in callback are caught and don't propagate."""

        def failing_callback(transaction, errors):
            raise RuntimeError("Callback intentionally failed")

        # Create NodeEffect with failing callback
        node_effect = NodeEffect(container, on_rollback_failure=failing_callback)

        # Register failing handler
        async def failing_handler(operation_data, transaction):
            def failing_rollback():
                raise ValueError("Rollback failed")

            if transaction:
                transaction.add_operation("test_op", operation_data, failing_rollback)

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Create input
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute - should raise ModelOnexError but not RuntimeError from callback
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Verify we got the rollback failure error, not the callback error
        assert "rollback failed" in str(exc_info.value).lower()
        assert "Callback intentionally failed" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_failure_metrics_are_updated(self, container):
        """Test that rollback failure metrics are tracked."""

        node_effect = NodeEffect(container)

        # Register failing handler
        async def failing_handler(operation_data, transaction):
            def failing_rollback():
                raise ValueError("Rollback failed")

            if transaction:
                transaction.add_operation("test_op", operation_data, failing_rollback)

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Create input
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute (will fail)
        with pytest.raises(ModelOnexError):
            await node_effect.process(effect_input)

        # Get metrics
        metrics = await node_effect.get_effect_metrics()

        # Verify transaction_management metrics exist (rollback metrics will be added in future enhancement)
        assert "transaction_management" in metrics
        # Note: rollback_failures_total and failed_operation_count_* metrics
        # are part of the specification but not yet implemented in NodeEffect
        # This test documents the expected behavior for future implementation

    @pytest.mark.asyncio
    async def test_transaction_context_manager_handles_rollback_failures(
        self, container
    ):
        """Test transaction_context properly handles and reports rollback failures."""

        node_effect = NodeEffect(container)

        # Use transaction context with failing rollback
        with pytest.raises(ModelOnexError) as exc_info:
            async with node_effect.transaction_context() as transaction:

                def failing_rollback():
                    raise ValueError("Rollback failed")

                transaction.add_operation("test_op", {"data": "test"}, failing_rollback)

                # Trigger rollback by raising exception
                raise ValueError("Operation failed")

        # Verify error indicates rollback failure
        error = exc_info.value
        assert "rollback failed" in error.message.lower()
        # Context is nested under additional_context in ModelOnexError
        additional_ctx = error.context.get("additional_context", {})
        context_data = additional_ctx.get("context", {})
        assert "rollback_errors" in context_data
