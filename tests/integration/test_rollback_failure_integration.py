"""
Integration tests for rollback failure handling.

Tests the complete workflow of rollback failure detection, logging,
metrics tracking, and callback invocation in realistic scenarios.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.enum_effect_types import EnumEffectType
from omnibase_core.nodes.model_effect_input import ModelEffectInput
from omnibase_core.nodes.node_effect import NodeEffect


class TestRollbackFailureIntegration:
    """Integration tests for rollback failure scenarios."""

    @pytest.fixture
    def container(self):
        """Create container for testing."""
        return ModelONEXContainer()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("original content")
        return test_file

    @pytest.mark.asyncio
    async def test_file_operation_rollback_failure_workflow(self, container, temp_file):
        """Test complete workflow when file operation rollback fails."""

        # Track all callback invocations
        rollback_failures = []

        def track_rollback_failures(transaction, errors):
            rollback_failures.append(
                {
                    "transaction_id": str(transaction.transaction_id),
                    "error_count": len(errors),
                    "errors": [str(e) for e in errors],
                }
            )

        # Create node with callback
        node_effect = NodeEffect(container, on_rollback_failure=track_rollback_failures)

        # Create a custom handler that will fail during rollback
        async def failing_write_handler(operation_data, transaction):
            # Simulate file write
            file_path = Path(operation_data["file_path"])
            new_content = operation_data.get("data", "")

            # Back up original content
            original_content = file_path.read_text()

            # Write new content
            file_path.write_text(new_content)

            # Register rollback that will fail
            def failing_rollback():
                # Simulate rollback failure (e.g., permissions error, disk full, etc.)
                raise PermissionError("Cannot restore file - permission denied")

            if transaction:
                transaction.add_operation(
                    "file_write", {"file_path": str(file_path)}, failing_rollback
                )

            # Simulate operation failure after write
            raise RuntimeError("Operation failed after write")

        # Replace handler
        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = (
            failing_write_handler
        )

        # Execute file write operation
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"file_path": str(temp_file), "data": "new content"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute and expect rollback failure
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Verify error context
        error = exc_info.value
        assert "rollback failed" in error.message.lower()
        assert "data may be inconsistent" in error.message.lower()
        assert "rollback_errors" in error.context
        assert len(error.context["rollback_errors"]) > 0

        # Verify callback was invoked
        assert len(rollback_failures) == 1
        assert rollback_failures[0]["error_count"] == 1
        assert "permission denied" in rollback_failures[0]["errors"][0].lower()

        # Verify metrics were updated
        metrics = await node_effect.get_effect_metrics()
        assert "transaction_management" in metrics
        assert metrics["transaction_management"]["rollback_failures_total"] == 1.0

    @pytest.mark.asyncio
    async def test_multiple_rollback_failures_tracked_correctly(self, container):
        """Test that multiple rollback failures are tracked and reported correctly."""

        rollback_failure_count = 0

        def count_rollback_failures(transaction, errors):
            nonlocal rollback_failure_count
            rollback_failure_count += 1

        node_effect = NodeEffect(container, on_rollback_failure=count_rollback_failures)

        # Register handler that will fail rollback
        async def failing_handler(operation_data, transaction):
            def failing_rollback():
                raise ValueError("Rollback failed")

            if transaction:
                transaction.add_operation("test_op", operation_data, failing_rollback)

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        # Execute multiple operations that will fail rollback
        for _ in range(3):
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={"test": "data"},
                transaction_enabled=True,
                retry_enabled=False,
            )

            with pytest.raises(ModelOnexError):
                await node_effect.process(effect_input)

        # Verify all failures tracked
        assert rollback_failure_count == 3

        # Verify metrics show all failures
        metrics = await node_effect.get_effect_metrics()
        assert metrics["transaction_management"]["rollback_failures_total"] == 3.0

    @pytest.mark.asyncio
    async def test_partial_rollback_failure_with_multiple_operations(self, container):
        """Test scenario where some rollback operations succeed and some fail."""

        node_effect = NodeEffect(container)

        # Register handler with multiple operations
        async def multi_operation_handler(operation_data, transaction):
            success_count = {"count": 0}

            def rollback_success_1():
                success_count["count"] += 1

            def rollback_fail():
                raise ValueError("Middle operation rollback failed")

            def rollback_success_2():
                success_count["count"] += 1

            if transaction:
                transaction.add_operation("op1", {"data": "1"}, rollback_success_1)
                transaction.add_operation("op2", {"data": "2"}, rollback_fail)
                transaction.add_operation("op3", {"data": "3"}, rollback_success_2)

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = (
            multi_operation_handler
        )

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute and expect rollback failure
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Verify partial failure reported
        error = exc_info.value
        assert "rollback failed" in error.message.lower()
        assert len(error.context["rollback_errors"]) == 1  # Only one failed

    @pytest.mark.asyncio
    async def test_cleanup_handles_rollback_failures(self, container):
        """Test that node cleanup handles rollback failures gracefully."""

        node_effect = NodeEffect(container)

        # Get baseline metrics before triggering rollback failure
        baseline_metrics = await node_effect.get_effect_metrics()
        baseline_rollback_failures = baseline_metrics["transaction_management"].get(
            "rollback_failures_total", 0.0
        )

        # Use transaction_context with failing rollback
        # Raise exception to trigger rollback which will fail
        try:
            async with node_effect.transaction_context() as tx:

                def failing_rollback():
                    raise ValueError("Cleanup rollback failed")

                tx.add_operation("test", {"data": "test"}, failing_rollback)

                # Raise exception to trigger rollback
                raise RuntimeError("Trigger rollback")
        except ModelOnexError:
            # Expected - rollback failed
            pass

        # Call cleanup to ensure any remaining state is cleaned up
        await node_effect.cleanup()

        # Verify metrics tracked the rollback failure
        metrics = await node_effect.get_effect_metrics()
        tx_metrics = metrics["transaction_management"]

        # Assert rollback failures increased by 1
        assert tx_metrics["rollback_failures_total"] == baseline_rollback_failures + 1.0
        # Verify at least one operation failed during rollback
        assert tx_metrics["failed_operation_count_min"] >= 1.0

    @pytest.mark.asyncio
    async def test_async_rollback_failure_handling(self, container):
        """Test that async rollback functions that fail are handled correctly."""

        node_effect = NodeEffect(container)

        async def handler_with_async_rollback(operation_data, transaction):
            async def async_failing_rollback():
                await asyncio.sleep(0)  # Yield to event loop
                raise ValueError("Async rollback failed")

            if transaction:
                transaction.add_operation(
                    "async_op", operation_data, async_failing_rollback
                )

            raise ValueError("Operation failed")

        node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = (
            handler_with_async_rollback
        )

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Execute and expect rollback failure
        with pytest.raises(ModelOnexError) as exc_info:
            await node_effect.process(effect_input)

        # Verify async rollback failure captured
        error = exc_info.value
        assert "rollback failed" in error.message.lower()
        assert len(error.context["rollback_errors"]) == 1

    @pytest.mark.asyncio
    async def test_rollback_failure_metrics_accumulation(self, container):
        """Test that rollback failure metrics accumulate correctly over time."""

        node_effect = NodeEffect(container)

        # Create handler with varying numbers of failing operations
        async def make_failing_handler(num_failures):
            async def handler(operation_data, transaction):
                for i in range(num_failures):

                    def make_failing_rollback(idx=i):
                        def failing_rollback():
                            raise ValueError(f"Rollback {idx} failed")

                        return failing_rollback

                    if transaction:
                        transaction.add_operation(
                            f"op{i}", {"idx": i}, make_failing_rollback()
                        )

                raise ValueError("Operation failed")

            return handler

        # Execute operations with 1, 2, and 3 failing rollback operations
        for num_failures in [1, 2, 3]:
            node_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = (
                await make_failing_handler(num_failures)
            )

            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={"test": "data"},
                transaction_enabled=True,
                retry_enabled=False,
            )

            with pytest.raises(ModelOnexError):
                await node_effect.process(effect_input)

        # Verify metrics show accumulation
        metrics = await node_effect.get_effect_metrics()
        tx_metrics = metrics["transaction_management"]

        assert tx_metrics["rollback_failures_total"] == 3.0  # 3 transactions failed
        assert tx_metrics["failed_operation_count_min"] == 1.0  # Minimum 1 failure
        assert tx_metrics["failed_operation_count_max"] == 3.0  # Maximum 3 failures
        assert tx_metrics["failed_operation_count_avg"] == 2.0  # Average (1+2+3)/3 = 2
