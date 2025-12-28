"""
Unit tests for explicit rollback failure handling.

Tests ModelEffectTransaction rollback failure detection,
logging, and callback invocation per PR #59 follow-up requirements.
"""

import asyncio
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumTransactionState
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_effect_transaction import (
    ModelEffectTransaction,
)


@pytest.mark.timeout(60)
@pytest.mark.unit
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
        """Test rollback preserves exception cause via native exception chaining."""
        transaction = ModelEffectTransaction(uuid4())

        original_error = ValueError("Original failure")

        def rollback_fail():
            raise original_error

        transaction.add_operation("op1", {"test": "data1"}, rollback_fail)

        # Execute rollback
        success, errors = await transaction.rollback()

        # Verify cause is preserved via native exception chaining (__cause__)
        assert not success
        assert len(errors) == 1
        assert isinstance(errors[0], ModelOnexError)
        # Verify the original error is chained as __cause__
        assert errors[0].__cause__ is original_error
