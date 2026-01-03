# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Property-based tests for ServiceInvariantEvaluator.

Uses hypothesis to test invariant properties with generated data,
ensuring the evaluator behaves correctly across a wide range of inputs.

Thread Safety:
    These tests create separate evaluator instances per test, matching
    the thread-safety requirements of ServiceInvariantEvaluator.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
from omnibase_core.models.invariant import ModelInvariant, ModelInvariantResult
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


def _create_evaluator() -> ServiceInvariantEvaluator:
    """Create a fresh evaluator instance.

    Note: We use a factory function instead of a pytest fixture because
    hypothesis @given decorators don't reset fixtures between generated inputs.
    Since ServiceInvariantEvaluator is stateless, creating new instances is fast.
    """
    return ServiceInvariantEvaluator()


@pytest.mark.unit
class TestInvariantPropertyBased:
    """Property-based tests for invariant evaluation.

    Uses hypothesis to generate test data and verify that key properties
    hold across all generated inputs.
    """

    @given(
        max_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        actual_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_threshold_max_value_property(
        self, max_value: float, actual_value: float
    ) -> None:
        """If actual <= max_value, threshold should pass.

        Property: For any valid numeric values, if the actual value is at
        or below the maximum threshold, the invariant must pass.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Threshold Property",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.WARNING,
            config={"metric_name": "value", "max_value": max_value},
        )

        result = evaluator.evaluate(invariant, {"value": actual_value})

        if actual_value <= max_value:
            assert result.passed is True, (
                f"Expected pass when actual ({actual_value}) <= max ({max_value})"
            )
        else:
            assert result.passed is False, (
                f"Expected fail when actual ({actual_value}) > max ({max_value})"
            )
            # Verify violation details are populated
            assert result.actual_value is not None, (
                "Expected actual_value to be set for failing invariant"
            )
            assert result.message, "Expected non-empty message for failing invariant"

    @given(
        min_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        actual_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_threshold_min_value_property(
        self, min_value: float, actual_value: float
    ) -> None:
        """If actual >= min_value, threshold should pass.

        Property: For any valid numeric values, if the actual value is at
        or above the minimum threshold, the invariant must pass.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Threshold Min Property",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.WARNING,
            config={"metric_name": "value", "min_value": min_value},
        )

        result = evaluator.evaluate(invariant, {"value": actual_value})

        if actual_value >= min_value:
            assert result.passed is True, (
                f"Expected pass when actual ({actual_value}) >= min ({min_value})"
            )
        else:
            assert result.passed is False, (
                f"Expected fail when actual ({actual_value}) < min ({min_value})"
            )
            # Verify violation details are populated
            assert result.actual_value is not None, (
                "Expected actual_value to be set for failing invariant"
            )
            assert result.message, "Expected non-empty message for failing invariant"

    @given(
        max_ms=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        actual_ms=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_latency_constraint_property(self, max_ms: float, actual_ms: float) -> None:
        """If actual_ms <= max_ms, latency check should pass.

        Property: For any valid latency values, if the actual latency is at
        or below the maximum allowed latency, the invariant must pass.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Latency Property",
            type=EnumInvariantType.LATENCY,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_ms": max_ms},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": actual_ms})

        if actual_ms <= max_ms:
            assert result.passed is True, (
                f"Expected pass when actual ({actual_ms}ms) <= max ({max_ms}ms)"
            )
        else:
            assert result.passed is False, (
                f"Expected fail when actual ({actual_ms}ms) > max ({max_ms}ms)"
            )
            # Verify violation details are populated
            assert result.actual_value is not None, (
                "Expected actual_value to be set for failing latency invariant"
            )
            assert result.message, (
                "Expected non-empty message for failing latency invariant"
            )

    @given(
        max_cost=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        actual_cost=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_cost_budget_property(self, max_cost: float, actual_cost: float) -> None:
        """If actual_cost <= max_cost, cost check should pass.

        Property: For any valid cost values, if the actual cost is at
        or below the maximum allowed cost, the invariant must pass.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Cost Property",
            type=EnumInvariantType.COST,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_cost": max_cost},
        )

        result = evaluator.evaluate(invariant, {"cost": actual_cost})

        if actual_cost <= max_cost:
            assert result.passed is True, (
                f"Expected pass when actual cost ({actual_cost}) <= max ({max_cost})"
            )
        else:
            assert result.passed is False, (
                f"Expected fail when actual cost ({actual_cost}) > max ({max_cost})"
            )
            # Verify violation details are populated
            assert result.actual_value is not None, (
                "Expected actual_value to be set for failing cost invariant"
            )
            assert result.message, (
                "Expected non-empty message for failing cost invariant"
            )

    @given(
        field_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("L", "N"), whitelist_characters="_"
            ),
        ),
    )
    @settings(max_examples=50)
    def test_field_presence_finds_existing_field(self, field_name: str) -> None:
        """Field presence should find fields that exist in output.

        Property: For any valid field name that exists in the output dict,
        the field presence check must pass.
        """
        # Exclude pure numbers and empty strings (not valid dict keys for our purposes)
        assume(field_name and not field_name.isdigit())
        # Ensure at least one letter in the field name
        assume(any(c.isalpha() for c in field_name))

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Field Property",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumInvariantSeverity.WARNING,
            config={"fields": [field_name]},
        )

        result = evaluator.evaluate(invariant, {field_name: "value"})

        assert result.passed is True, (
            f"Expected pass when field '{field_name}' exists in output"
        )

    @given(
        field_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("L", "N"), whitelist_characters="_"
            ),
        ),
    )
    @settings(max_examples=50)
    def test_field_presence_missing_field_fails(self, field_name: str) -> None:
        """Field presence should fail when field is missing.

        Property: For any valid field name that does NOT exist in the output dict,
        the field presence check must fail.
        """
        assume(field_name and not field_name.isdigit())
        assume(any(c.isalpha() for c in field_name))

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Missing Field Property",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumInvariantSeverity.WARNING,
            config={"fields": [field_name]},
        )

        # Use a different key that won't match
        result = evaluator.evaluate(invariant, {"other_field": "value"})

        # Only assert failure if field_name != "other_field"
        if field_name != "other_field":
            assert result.passed is False, (
                f"Expected fail when field '{field_name}' is missing"
            )
            # Verify violation details are populated
            assert result.message, (
                f"Expected non-empty message for missing field '{field_name}'"
            )

    @given(
        output=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False)),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_evaluate_never_crashes(self, output: dict) -> None:
        """Evaluation should never crash, always return a result.

        Property: For any arbitrary output dictionary, the evaluator must
        return a valid ModelInvariantResult without raising an exception.
        This ensures robustness against unexpected inputs.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Crash Test",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumInvariantSeverity.WARNING,
            config={"fields": ["some_field"]},
        )

        result = evaluator.evaluate(invariant, output)

        assert isinstance(result, ModelInvariantResult)
        assert isinstance(result.passed, bool)
        assert isinstance(result.message, str)

    @given(
        output=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.none(),
                st.lists(st.integers(), max_size=5),
            ),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_threshold_never_crashes_with_arbitrary_output(self, output: dict) -> None:
        """Threshold evaluation should never crash with arbitrary output.

        Property: Even when output contains non-numeric values or missing fields,
        the threshold evaluator returns a valid result (pass or fail) without
        raising an exception.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Threshold Crash Test",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.WARNING,
            config={"metric_name": "arbitrary_metric", "max_value": 100},
        )

        result = evaluator.evaluate(invariant, output)

        assert isinstance(result, ModelInvariantResult)
        assert isinstance(result.passed, bool)

    @given(
        output=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
            ),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_latency_never_crashes_with_arbitrary_output(self, output: dict) -> None:
        """Latency evaluation should never crash with arbitrary output.

        Property: Even when output lacks latency fields or contains unexpected types,
        the latency evaluator returns a valid result without raising an exception.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Latency Crash Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_ms": 1000},
        )

        result = evaluator.evaluate(invariant, output)

        assert isinstance(result, ModelInvariantResult)
        assert isinstance(result.passed, bool)

    @given(
        output=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
            ),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_cost_never_crashes_with_arbitrary_output(self, output: dict) -> None:
        """Cost evaluation should never crash with arbitrary output.

        Property: Even when output lacks cost fields or contains unexpected types,
        the cost evaluator returns a valid result without raising an exception.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Cost Crash Test",
            type=EnumInvariantType.COST,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_cost": 10.0},
        )

        result = evaluator.evaluate(invariant, output)

        assert isinstance(result, ModelInvariantResult)
        assert isinstance(result.passed, bool)

    @given(
        actual_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        min_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        max_value=st.floats(
            min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_threshold_both_bounds_property(
        self,
        actual_value: float,
        min_value: float,
        max_value: float,
    ) -> None:
        """Threshold with both bounds passes iff min <= actual <= max.

        Property: When both min_value and max_value are specified, the invariant
        passes if and only if the actual value is within the inclusive range.
        """
        # Skip invalid configurations where min > max
        assume(min_value <= max_value)

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Both Bounds Property",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.WARNING,
            config={
                "metric_name": "value",
                "min_value": min_value,
                "max_value": max_value,
            },
        )

        result = evaluator.evaluate(invariant, {"value": actual_value})

        if min_value <= actual_value <= max_value:
            assert result.passed is True, (
                f"Expected pass when {min_value} <= {actual_value} <= {max_value}"
            )
        else:
            assert result.passed is False, (
                f"Expected fail when {actual_value} not in [{min_value}, {max_value}]"
            )
            # Verify violation details are populated
            assert result.actual_value is not None, (
                "Expected actual_value to be set for failing bounds invariant"
            )
            assert result.message, (
                "Expected non-empty message for failing bounds invariant"
            )

    @given(
        severity=st.sampled_from(list(EnumInvariantSeverity)),
    )
    @settings(max_examples=20)
    def test_result_preserves_severity(self, severity: EnumInvariantSeverity) -> None:
        """Result should preserve the severity from the invariant.

        Property: The severity level in the result must match the severity
        specified in the original invariant, regardless of pass/fail status.
        """
        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Severity Test",
            type=EnumInvariantType.FIELD_PRESENCE,
            severity=severity,
            config={"fields": ["test_field"]},
        )

        result = evaluator.evaluate(invariant, {"test_field": "value"})

        assert result.severity == severity, (
            f"Result severity ({result.severity}) should match invariant ({severity})"
        )


__all__ = ["TestInvariantPropertyBased"]
