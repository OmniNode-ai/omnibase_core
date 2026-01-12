# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Tests for custom callable invariant evaluation.

This module tests the CUSTOM invariant type which allows users to define
their own validation functions that are dynamically imported and executed.

Test Coverage:
- Custom callable passes when returning True
- Custom callable fails when returning False
- Missing callable fails gracefully with import error
- Exceptions in custom callables are captured in result
- Allow-list blocks unauthorized import paths
"""

import pytest

from omnibase_core.enums import EnumInvariantType
from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.invariant import ModelInvariant
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestCustomEvaluator:
    """Test suite for custom callable invariant type."""

    def test_custom_callable_passes(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Custom callable that returns True passes."""
        invariant = ModelInvariant(
            name="Custom Pass",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.always_pass"
            },
        )

        result = evaluator.evaluate(invariant, {"any": "data"})
        assert result.passed is True

    def test_custom_callable_fails(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Custom callable that returns False fails."""
        invariant = ModelInvariant(
            name="Custom Fail",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.WARNING,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.always_fail"
            },
        )

        result = evaluator.evaluate(invariant, {"any": "data"})
        assert result.passed is False
        assert "Always fails" in result.message

    def test_custom_callable_not_found_fails(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Missing custom callable fails gracefully."""
        invariant = ModelInvariant(
            name="Missing Callable",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={"callable_path": "nonexistent.module.function"},
        )

        result = evaluator.evaluate(invariant, {"any": "data"})

        assert result.passed is False
        assert (
            "import" in result.message.lower() or "not found" in result.message.lower()
        )

    def test_custom_callable_exception_captured(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Exception in custom callable captured in result."""
        invariant = ModelInvariant(
            name="Exception Callable",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.WARNING,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.raise_exception"
            },
        )

        result = evaluator.evaluate(invariant, {"any": "data"})

        assert result.passed is False
        assert (
            "exception" in result.message.lower() or "error" in result.message.lower()
        )

    def test_custom_allow_list_blocks_unauthorized(
        self, evaluator_with_allowlist: ServiceInvariantEvaluator
    ) -> None:
        """Allow-list blocks unauthorized import paths."""
        invariant = ModelInvariant(
            name="Blocked Callable",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={"callable_path": "os.system"},  # Not in allow-list
        )

        result = evaluator_with_allowlist.evaluate(invariant, {"any": "data"})

        assert result.passed is False
        assert (
            "allow" in result.message.lower()
            or "blocked" in result.message.lower()
            or "not permitted" in result.message.lower()
            or "not in" in result.message.lower()
        )

    def test_custom_callable_bool_return_type(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Custom callable returning bool only (alternative signature) works."""
        invariant = ModelInvariant(
            name="Bool Return",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.WARNING,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.return_bool_only"
            },
        )

        # Test with 'valid' key present - should pass
        result = evaluator.evaluate(invariant, {"valid": True})
        assert result.passed is True

        # Test without 'valid' key - should fail
        result = evaluator.evaluate(invariant, {"invalid": True})
        assert result.passed is False

    def test_custom_callable_with_data_check(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Custom callable that checks for specific field works correctly."""
        invariant = ModelInvariant(
            name="Data Check",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.check_has_data"
            },
        )

        # Test with 'data' key present - should pass
        result = evaluator.evaluate(invariant, {"data": {"value": 123}})
        assert result.passed is True
        assert "Data field present" in result.message

        # Test without 'data' key - should fail
        result = evaluator.evaluate(invariant, {"other": "value"})
        assert result.passed is False
        assert "Missing data field" in result.message

    def test_custom_allow_list_allows_authorized_path(
        self, evaluator_with_allowlist: ServiceInvariantEvaluator
    ) -> None:
        """Allow-list permits authorized import paths."""
        invariant = ModelInvariant(
            name="Allowed Callable",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            config={
                "callable_path": "tests.unit.services.invariant.custom_validators.always_pass"
            },
        )

        result = evaluator_with_allowlist.evaluate(invariant, {"any": "data"})

        assert result.passed is True

    def test_custom_callable_invalid_path_format(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Invalid callable path format fails gracefully."""
        invariant = ModelInvariant(
            name="Invalid Path",
            type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.WARNING,
            config={"callable_path": "no_dots_or_colons"},
        )

        result = evaluator.evaluate(invariant, {"any": "data"})

        assert result.passed is False
        # Should indicate invalid format or import error
        assert "invalid" in result.message.lower() or "import" in result.message.lower()
