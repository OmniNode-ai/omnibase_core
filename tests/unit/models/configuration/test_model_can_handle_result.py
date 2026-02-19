# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelCanHandleResult.

This module tests the ModelCanHandleResult model including:
- Basic creation and field access
- Custom __bool__ behavior for idiomatic checking
- Integration with handler patterns
"""

import pytest

from omnibase_core.models.configuration.model_can_handle_result import (
    ModelCanHandleResult,
)


@pytest.mark.unit
class TestModelCanHandleResultCreation:
    """Test ModelCanHandleResult creation."""

    def test_create_with_can_handle_true(self) -> None:
        """Test creating result with can_handle=True."""
        result = ModelCanHandleResult(can_handle=True)
        assert result.can_handle is True

    def test_create_with_can_handle_false(self) -> None:
        """Test creating result with can_handle=False."""
        result = ModelCanHandleResult(can_handle=False)
        assert result.can_handle is False


@pytest.mark.unit
class TestModelCanHandleResultBoolConversion:
    """Tests for __bool__ behavior in ModelCanHandleResult.

    ModelCanHandleResult overrides the default Pydantic __bool__ behavior
    to return the value of can_handle, enabling idiomatic conditional checks
    like `if result:` instead of `if result.can_handle:`.
    """

    def test_bool_conversion_can_handle_true(self) -> None:
        """Test __bool__ returns True when can_handle=True."""
        result = ModelCanHandleResult(can_handle=True)
        assert bool(result) is True

    def test_bool_conversion_can_handle_false(self) -> None:
        """Test __bool__ returns False when can_handle=False."""
        result = ModelCanHandleResult(can_handle=False)
        assert bool(result) is False

    def test_idiomatic_check_can_handle_true(self) -> None:
        """Test idiomatic if check when can_handle=True."""
        result = ModelCanHandleResult(can_handle=True)
        assert result  # Idiomatic check should pass

    def test_idiomatic_check_can_handle_false(self) -> None:
        """Test idiomatic if check when can_handle=False."""
        result = ModelCanHandleResult(can_handle=False)
        assert not result  # Idiomatic check should pass

    def test_bool_in_if_statement_can_handle_true(self) -> None:
        """Test boolean conversion in if statement when can_handle=True."""
        result = ModelCanHandleResult(can_handle=True)
        executed = False
        if result:
            executed = True
        assert executed is True

    def test_bool_in_if_statement_can_handle_false(self) -> None:
        """Test boolean conversion in if statement when can_handle=False."""
        result = ModelCanHandleResult(can_handle=False)
        executed = False
        if result:
            executed = True
        assert executed is False

    def test_bool_differs_from_standard_pydantic(self) -> None:
        """Test that __bool__ differs from standard Pydantic behavior.

        Standard Pydantic models always return True for bool(model) because
        the instance exists. ModelCanHandleResult overrides this to return
        the value of can_handle, which may be False.
        """
        false_result = ModelCanHandleResult(can_handle=False)
        # Standard Pydantic would return True here, but we return False
        assert bool(false_result) is False

        true_result = ModelCanHandleResult(can_handle=True)
        assert bool(true_result) is True


@pytest.mark.unit
class TestModelCanHandleResultHandlerPattern:
    """Test ModelCanHandleResult in handler pattern scenarios."""

    def test_handler_pattern_can_handle(self) -> None:
        """Test using result in typical handler pattern when can handle."""
        result = ModelCanHandleResult(can_handle=True)

        # Typical pattern: check if handler can process
        handler_name = None
        if result:
            handler_name = "test_handler"

        assert handler_name == "test_handler"

    def test_handler_pattern_cannot_handle(self) -> None:
        """Test using result in typical handler pattern when cannot handle."""
        result = ModelCanHandleResult(can_handle=False)

        # Typical pattern: check if handler can process
        handler_name = None
        if result:
            handler_name = "test_handler"

        assert handler_name is None

    def test_handler_selection_loop(self) -> None:
        """Test selecting handler based on can_handle results."""
        handlers = [
            ("handler_a", ModelCanHandleResult(can_handle=False)),
            ("handler_b", ModelCanHandleResult(can_handle=True)),
            ("handler_c", ModelCanHandleResult(can_handle=False)),
        ]

        selected = None
        for name, result in handlers:
            if result:  # Uses __bool__
                selected = name
                break

        assert selected == "handler_b"

    def test_all_handlers_cannot_handle(self) -> None:
        """Test when no handler can process."""
        handlers = [
            ("handler_a", ModelCanHandleResult(can_handle=False)),
            ("handler_b", ModelCanHandleResult(can_handle=False)),
        ]

        selected = None
        for name, result in handlers:
            if result:
                selected = name
                break

        assert selected is None


@pytest.mark.unit
class TestModelCanHandleResultSerialization:
    """Test ModelCanHandleResult serialization."""

    def test_model_dump_can_handle_true(self) -> None:
        """Test model_dump with can_handle=True."""
        result = ModelCanHandleResult(can_handle=True)
        data = result.model_dump()
        assert data["can_handle"] is True

    def test_model_dump_can_handle_false(self) -> None:
        """Test model_dump with can_handle=False."""
        result = ModelCanHandleResult(can_handle=False)
        data = result.model_dump()
        assert data["can_handle"] is False

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization preserves can_handle value."""
        original_true = ModelCanHandleResult(can_handle=True)
        original_false = ModelCanHandleResult(can_handle=False)

        restored_true = ModelCanHandleResult(**original_true.model_dump())
        restored_false = ModelCanHandleResult(**original_false.model_dump())

        assert bool(restored_true) is True
        assert bool(restored_false) is False
