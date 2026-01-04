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
            # Verify expected_value is set correctly for failure case
            assert result.expected_value is not None, (
                "Expected expected_value to be set for failing invariant"
            )
            # Verify invariant_name is preserved
            assert result.invariant_name == "Threshold Property", (
                f"Expected invariant_name 'Threshold Property', got '{result.invariant_name}'"
            )
            # Verify message contains useful context
            assert (
                str(max_value) in result.message or "maximum" in result.message.lower()
            ), f"Expected message to contain threshold info, got: {result.message}"

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
            # Verify expected_value is set correctly for failure case
            assert result.expected_value is not None, (
                "Expected expected_value to be set for failing invariant"
            )
            # Verify invariant_name is preserved
            assert result.invariant_name == "Threshold Min Property", (
                f"Expected invariant_name 'Threshold Min Property', got '{result.invariant_name}'"
            )
            # Verify message contains useful context
            assert (
                str(min_value) in result.message or "minimum" in result.message.lower()
            ), f"Expected message to contain threshold info, got: {result.message}"

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
            # Verify expected_value is set correctly for failure case
            assert result.expected_value is not None, (
                "Expected expected_value to be set for failing latency invariant"
            )
            assert result.expected_value == max_ms, (
                f"Expected expected_value to be {max_ms}, got {result.expected_value}"
            )
            # Verify invariant_name is preserved
            assert result.invariant_name == "Latency Property", (
                f"Expected invariant_name 'Latency Property', got '{result.invariant_name}'"
            )
            # Verify message contains latency context
            assert (
                "ms" in result.message.lower() or "latency" in result.message.lower()
            ), f"Expected message to contain latency info, got: {result.message}"

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
            # Verify expected_value is set correctly for failure case
            assert result.expected_value is not None, (
                "Expected expected_value to be set for failing cost invariant"
            )
            assert result.expected_value == max_cost, (
                f"Expected expected_value to be {max_cost}, got {result.expected_value}"
            )
            # Verify invariant_name is preserved
            assert result.invariant_name == "Cost Property", (
                f"Expected invariant_name 'Cost Property', got '{result.invariant_name}'"
            )
            # Verify message contains cost context
            assert (
                "cost" in result.message.lower() or "budget" in result.message.lower()
            ), f"Expected message to contain cost info, got: {result.message}"

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

    # ===== Failure-specific property tests =====
    # These tests specifically validate that invalid inputs cause expected failures

    @given(
        metric_name=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(
                whitelist_categories=("L", "N"), whitelist_characters="_"
            ),
        ),
    )
    @settings(max_examples=50)
    def test_threshold_fails_with_missing_metric(self, metric_name: str) -> None:
        """Threshold should fail when the metric is missing from output.

        Property: For any valid metric name that does NOT exist in the output dict,
        the threshold check must fail with appropriate error details.
        """
        assume(metric_name and not metric_name.isdigit())
        assume(any(c.isalpha() for c in metric_name))

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Missing Metric Test",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.CRITICAL,
            config={"metric_name": metric_name, "max_value": 100.0},
        )

        # Output has different field - metric is missing
        result = evaluator.evaluate(invariant, {"other_field": 50.0})

        # Must fail when metric is missing
        assert result.passed is False, (
            f"Expected fail when metric '{metric_name}' is missing from output"
        )
        # Verify failure details
        assert result.message, "Expected non-empty message for missing metric"
        assert metric_name in result.message or "not found" in result.message.lower(), (
            f"Expected message to reference missing metric, got: {result.message}"
        )
        assert result.invariant_name == "Missing Metric Test", (
            f"Expected invariant_name preserved, got '{result.invariant_name}'"
        )
        assert result.severity == EnumInvariantSeverity.CRITICAL, (
            f"Expected CRITICAL severity preserved, got {result.severity}"
        )

    @given(
        non_numeric_value=st.one_of(
            # Use text that cannot be parsed as a number
            st.text(
                min_size=2,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L",)),  # Only letters
            ),
            st.lists(st.integers(), min_size=1, max_size=3),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=5),
                values=st.integers(),
                min_size=1,
                max_size=2,
            ),
        ),
    )
    @settings(max_examples=50)
    def test_threshold_fails_with_non_numeric_value(
        self, non_numeric_value: object
    ) -> None:
        """Threshold should fail when the metric value is non-numeric.

        Property: For any truly non-numeric value (not convertible to float),
        the threshold check must fail with a descriptive error message.
        """
        # Skip values that can be converted to float
        if isinstance(non_numeric_value, str):
            try:
                float(non_numeric_value)
                assume(False)  # Skip numeric strings
            except (TypeError, ValueError):
                pass  # This is a valid non-numeric string

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Non-Numeric Test",
            type=EnumInvariantType.THRESHOLD,
            severity=EnumInvariantSeverity.WARNING,
            config={"metric_name": "value", "max_value": 100.0},
        )

        result = evaluator.evaluate(invariant, {"value": non_numeric_value})

        # Must fail when value is non-numeric
        assert result.passed is False, (
            f"Expected fail when value is non-numeric: {type(non_numeric_value).__name__}"
        )
        # Verify failure details
        assert result.message, "Expected non-empty message for non-numeric value"
        assert "not numeric" in result.message.lower() or "value" in result.message, (
            f"Expected message to indicate non-numeric issue, got: {result.message}"
        )

    @given(
        output_keys=st.lists(
            st.text(
                min_size=1,
                max_size=15,
                alphabet=st.characters(
                    whitelist_categories=("L", "N"), whitelist_characters="_"
                ),
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_latency_fails_with_missing_latency_field(
        self, output_keys: list[str]
    ) -> None:
        """Latency should fail when neither latency_ms nor duration_ms exists.

        Property: When output lacks both latency_ms and duration_ms fields,
        the latency check must fail with appropriate error details.
        """
        # Ensure neither latency_ms nor duration_ms is in the output
        assume("latency_ms" not in output_keys)
        assume("duration_ms" not in output_keys)

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Missing Latency Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_ms": 1000.0},
        )

        # Create output without latency fields
        output = dict.fromkeys(output_keys, 42)
        result = evaluator.evaluate(invariant, output)

        # Must fail when latency field is missing
        assert result.passed is False, (
            "Expected fail when latency_ms and duration_ms are missing"
        )
        # Verify failure details
        assert result.message, "Expected non-empty message for missing latency"
        assert (
            "latency" in result.message.lower() or "not found" in result.message.lower()
        ), f"Expected message to reference missing latency, got: {result.message}"
        # Expected value should still be set to max_ms
        assert result.expected_value == 1000.0, (
            f"Expected expected_value to be max_ms (1000.0), got {result.expected_value}"
        )

    @given(
        output_keys=st.lists(
            st.text(
                min_size=1,
                max_size=15,
                alphabet=st.characters(
                    whitelist_categories=("L", "N"), whitelist_characters="_"
                ),
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_cost_fails_with_missing_cost_field(self, output_keys: list[str]) -> None:
        """Cost should fail when cost and usage.total_tokens are missing.

        Property: When output lacks both cost and usage.total_tokens fields,
        the cost check must fail with appropriate error details.
        """
        # Ensure cost and usage.total_tokens are not in the output
        assume("cost" not in output_keys)
        assume("usage" not in output_keys)

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Missing Cost Test",
            type=EnumInvariantType.COST,
            severity=EnumInvariantSeverity.CRITICAL,
            config={"max_cost": 10.0},
        )

        # Create output without cost fields
        output = dict.fromkeys(output_keys, 42)
        result = evaluator.evaluate(invariant, output)

        # Must fail when cost field is missing
        assert result.passed is False, (
            "Expected fail when cost and usage.total_tokens are missing"
        )
        # Verify failure details
        assert result.message, "Expected non-empty message for missing cost"
        assert (
            "cost" in result.message.lower() or "not found" in result.message.lower()
        ), f"Expected message to reference missing cost, got: {result.message}"
        # Expected value should still be set to max_cost
        assert result.expected_value == 10.0, (
            f"Expected expected_value to be max_cost (10.0), got {result.expected_value}"
        )
        # Severity should be preserved
        assert result.severity == EnumInvariantSeverity.CRITICAL, (
            f"Expected CRITICAL severity, got {result.severity}"
        )

    @given(
        non_numeric_value=st.one_of(
            # Use text that cannot be parsed as a number
            st.text(
                min_size=2,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L",)),  # Only letters
            ),
            st.none(),
            st.lists(st.integers(), min_size=1, max_size=3),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=5),
                values=st.integers(),
                min_size=1,
                max_size=2,
            ),
        ),
    )
    @settings(max_examples=50)
    def test_latency_fails_with_non_numeric_latency(
        self, non_numeric_value: object
    ) -> None:
        """Latency should fail when latency_ms value is non-numeric.

        Property: For any truly non-numeric latency value (not convertible to float),
        the latency check must fail.
        """
        # Skip values that can be converted to float
        if isinstance(non_numeric_value, str):
            try:
                float(non_numeric_value)
                assume(False)  # Skip numeric strings
            except (TypeError, ValueError):
                pass  # This is a valid non-numeric string

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Non-Numeric Latency Test",
            type=EnumInvariantType.LATENCY,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_ms": 1000.0},
        )

        result = evaluator.evaluate(invariant, {"latency_ms": non_numeric_value})

        # Must fail when latency value is non-numeric
        assert result.passed is False, (
            f"Expected fail when latency_ms is non-numeric: {type(non_numeric_value).__name__}"
        )

    @given(
        non_numeric_value=st.one_of(
            # Use text that cannot be parsed as a number
            st.text(
                min_size=2,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("L",)),  # Only letters
            ),
            st.none(),
            st.lists(st.integers(), min_size=1, max_size=3),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=5),
                values=st.integers(),
                min_size=1,
                max_size=2,
            ),
        ),
    )
    @settings(max_examples=50)
    def test_cost_fails_with_non_numeric_cost(self, non_numeric_value: object) -> None:
        """Cost should fail when cost value is non-numeric.

        Property: For any truly non-numeric cost value (not convertible to float),
        the cost check must fail.
        """
        # Skip values that can be converted to float
        if isinstance(non_numeric_value, str):
            try:
                float(non_numeric_value)
                assume(False)  # Skip numeric strings
            except (TypeError, ValueError):
                pass  # This is a valid non-numeric string

        evaluator = _create_evaluator()
        invariant = ModelInvariant(
            name="Non-Numeric Cost Test",
            type=EnumInvariantType.COST,
            severity=EnumInvariantSeverity.WARNING,
            config={"max_cost": 10.0},
        )

        result = evaluator.evaluate(invariant, {"cost": non_numeric_value})

        # Must fail when cost value is non-numeric
        assert result.passed is False, (
            f"Expected fail when cost is non-numeric: {type(non_numeric_value).__name__}"
        )


__all__ = ["TestInvariantPropertyBased"]
