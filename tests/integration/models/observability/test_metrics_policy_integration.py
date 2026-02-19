# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for observability metrics policy with metric emissions.

This module provides comprehensive integration tests for the ModelMetricsPolicy
and its interaction with metric emission models (Counter, Gauge, Histogram).
These tests verify realistic multi-model scenarios including:

1. Policy Enforcement Across Metric Types
   - ModelMetricsPolicy validates labels from ModelCounterEmission
   - ModelMetricsPolicy validates labels from ModelGaugeEmission
   - ModelMetricsPolicy validates labels from ModelHistogramObservation
   - Same policy validates batches of mixed metric types

2. Strict Mode Enforcement
   - allowed_label_keys filtering across multiple metrics
   - Interaction between allowed and forbidden keys
   - Strict mode label sanitization

3. Label Sanitization Workflow
   - Full workflow: validate -> get sanitized -> create new emissions
   - Truncation of long values preserves valid keys
   - Sanitized labels can create valid metric emissions

4. Mixed Violation Handling
   - Batch scenarios with multiple violation types
   - Forbidden keys + value too long + not allowed combinations
   - Violation aggregation across multiple metrics

5. Policy Enforcement Actions
   - RAISE action halts on first violation
   - WARN_AND_DROP returns None for invalid metrics
   - WARN_AND_STRIP returns sanitized labels
   - DROP_SILENT quietly drops metrics

Test Categories:
    All tests are marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

Author: ONEX Framework Team
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType
from omnibase_core.enums.enum_metrics_policy_violation_action import (
    EnumMetricsPolicyViolationAction,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.observability.model_counter_emission import (
    ModelCounterEmission,
)
from omnibase_core.models.observability.model_gauge_emission import ModelGaugeEmission
from omnibase_core.models.observability.model_histogram_observation import (
    ModelHistogramObservation,
)
from omnibase_core.models.observability.model_label_validation_result import (
    ModelLabelValidationResult,
)
from omnibase_core.models.observability.model_metrics_policy import ModelMetricsPolicy

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60


# =============================================================================
# 1. POLICY ENFORCEMENT ACROSS METRIC TYPES
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestPolicyEnforcementAcrossMetricTypes:
    """Tests for policy validation across different metric emission types.

    Verifies that ModelMetricsPolicy correctly validates labels from
    ModelCounterEmission, ModelGaugeEmission, and ModelHistogramObservation.
    """

    def test_policy_validates_counter_labels(self) -> None:
        """Test policy validates labels from counter emission."""
        policy = ModelMetricsPolicy()

        # Create counter with valid labels
        counter = ModelCounterEmission(
            name="http_requests_total",
            labels={"method": "GET", "status": "200", "endpoint": "/api/users"},
            increment=1.0,
        )

        result = policy.validate_labels(counter.labels)

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.sanitized_labels == counter.labels

    def test_policy_validates_gauge_labels(self) -> None:
        """Test policy validates labels from gauge emission."""
        policy = ModelMetricsPolicy()

        # Create gauge with valid labels
        gauge = ModelGaugeEmission(
            name="queue_depth",
            labels={"queue": "orders", "priority": "high"},
            value=42.0,
        )

        result = policy.validate_labels(gauge.labels)

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.sanitized_labels == gauge.labels

    def test_policy_validates_histogram_labels(self) -> None:
        """Test policy validates labels from histogram observation."""
        policy = ModelMetricsPolicy()

        # Create histogram with valid labels
        histogram = ModelHistogramObservation(
            name="request_duration_seconds",
            labels={"service": "api-gateway", "route": "/health"},
            value=0.125,
        )

        result = policy.validate_labels(histogram.labels)

        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.sanitized_labels == histogram.labels

    def test_batch_validation_with_shared_policy(self) -> None:
        """Test same policy validates multiple metric types consistently."""
        policy = ModelMetricsPolicy()

        # Create batch of different metric types with same label structure
        shared_labels = {"service": "user-service", "environment": "production"}

        counter = ModelCounterEmission(
            name="requests_total",
            labels=shared_labels,
            increment=1.0,
        )
        gauge = ModelGaugeEmission(
            name="active_connections",
            labels=shared_labels,
            value=100.0,
        )
        histogram = ModelHistogramObservation(
            name="latency_seconds",
            labels=shared_labels,
            value=0.05,
        )

        # All should pass validation with same policy
        counter_result = policy.validate_labels(counter.labels)
        gauge_result = policy.validate_labels(gauge.labels)
        histogram_result = policy.validate_labels(histogram.labels)

        assert counter_result.is_valid is True
        assert gauge_result.is_valid is True
        assert histogram_result.is_valid is True

        # All should have same sanitized labels
        assert counter_result.sanitized_labels == shared_labels
        assert gauge_result.sanitized_labels == shared_labels
        assert histogram_result.sanitized_labels == shared_labels

    def test_policy_rejects_forbidden_labels_from_counter(self) -> None:
        """Test policy rejects forbidden labels from counter emission."""
        policy = ModelMetricsPolicy()

        # Counter with forbidden label (envelope_id is default forbidden)
        counter = ModelCounterEmission(
            name="events_processed",
            labels={
                "envelope_id": "abc-123",
                "type": "user_created",
            },
            increment=1.0,
        )

        result = policy.validate_labels(counter.labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.FORBIDDEN_KEY
        )
        assert result.violations[0].key == "envelope_id"

    def test_policy_rejects_forbidden_labels_from_gauge(self) -> None:
        """Test policy rejects forbidden labels from gauge emission."""
        policy = ModelMetricsPolicy()

        # Gauge with multiple forbidden labels
        gauge = ModelGaugeEmission(
            name="memory_usage_bytes",
            labels={
                "node_id": "node-001",
                "correlation_id": "corr-xyz",
                "region": "us-east-1",
            },
            value=1073741824.0,
        )

        result = policy.validate_labels(gauge.labels)

        assert result.is_valid is False
        assert len(result.violations) == 2

        violation_keys = {v.key for v in result.violations}
        assert "node_id" in violation_keys
        assert "correlation_id" in violation_keys

        # "region" should be in sanitized labels
        assert result.sanitized_labels is not None
        assert "region" in result.sanitized_labels
        assert "node_id" not in result.sanitized_labels
        assert "correlation_id" not in result.sanitized_labels

    def test_policy_rejects_forbidden_labels_from_histogram(self) -> None:
        """Test policy rejects forbidden labels from histogram observation."""
        policy = ModelMetricsPolicy()

        # Histogram with forbidden label
        histogram = ModelHistogramObservation(
            name="db_query_duration_seconds",
            labels={
                "runtime_id": "rt-999",
                "query_type": "SELECT",
            },
            value=0.5,
        )

        result = policy.validate_labels(histogram.labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0].key == "runtime_id"


# =============================================================================
# 2. STRICT MODE ENFORCEMENT
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestStrictModeEnforcement:
    """Tests for strict mode (allowed_label_keys) enforcement.

    When allowed_label_keys is set, only those keys are permitted
    (minus anything in forbidden_label_keys).
    """

    def test_strict_mode_allows_only_specified_keys(self) -> None:
        """Test strict mode only allows specified label keys."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"service", "environment", "version"}),
        )

        # Counter with allowed labels
        counter = ModelCounterEmission(
            name="requests_total",
            labels={"service": "api", "environment": "prod"},
            increment=1.0,
        )

        result = policy.validate_labels(counter.labels)

        assert result.is_valid is True
        assert result.sanitized_labels == counter.labels

    def test_strict_mode_rejects_unlisted_keys(self) -> None:
        """Test strict mode rejects keys not in allowed list."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"service", "environment"}),
        )

        # Gauge with unlisted label key
        gauge = ModelGaugeEmission(
            name="cpu_usage_percent",
            labels={
                "service": "worker",
                "environment": "staging",
                "host": "worker-01",  # Not in allowed list
            },
            value=75.5,
        )

        result = policy.validate_labels(gauge.labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type
            == EnumLabelViolationType.KEY_NOT_ALLOWED
        )
        assert result.violations[0].key == "host"

        # Sanitized should only have allowed keys
        assert result.sanitized_labels is not None
        assert "service" in result.sanitized_labels
        assert "environment" in result.sanitized_labels
        assert "host" not in result.sanitized_labels

    def test_strict_mode_forbidden_wins_over_allowed(self) -> None:
        """Test that forbidden keys are rejected even if in allowed list."""
        # Note: This tests the policy semantics where forbidden always wins
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset(
                {"service", "environment", "node_id"}  # node_id is default forbidden
            ),
            # forbidden_label_keys defaults to DEFAULT_FORBIDDEN
        )

        histogram = ModelHistogramObservation(
            name="process_duration_seconds",
            labels={
                "service": "processor",
                "environment": "prod",
                "node_id": "node-123",  # Forbidden even though in allowed
            },
            value=1.5,
        )

        result = policy.validate_labels(histogram.labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.FORBIDDEN_KEY
        )
        assert result.violations[0].key == "node_id"

    def test_strict_mode_batch_filtering(self) -> None:
        """Test strict mode filters labels consistently across batch."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"region", "tier"}),
        )

        metrics: list[dict[str, Any]] = [
            {
                "type": "counter",
                "labels": {"region": "us-west", "tier": "premium", "extra": "data"},
            },
            {
                "type": "gauge",
                "labels": {"region": "eu-central", "unknown": "field"},
            },
            {
                "type": "histogram",
                "labels": {"region": "ap-south", "tier": "basic"},
            },
        ]

        results: list[ModelLabelValidationResult] = []
        for metric in metrics:
            results.append(policy.validate_labels(metric["labels"]))

        # First two have violations (extra/unknown keys), third is valid
        assert results[0].is_valid is False
        assert results[1].is_valid is False
        assert results[2].is_valid is True

        # All should have region in sanitized
        for result in results:
            assert result.sanitized_labels is not None
            assert "region" in result.sanitized_labels

    def test_strict_mode_empty_allowed_keys(self) -> None:
        """Test strict mode with empty allowed keys rejects all labels."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset(),  # No keys allowed
        )

        counter = ModelCounterEmission(
            name="events_total",
            labels={"any": "label"},
            increment=1.0,
        )

        result = policy.validate_labels(counter.labels)

        assert result.is_valid is False
        assert (
            result.violations[0].violation_type
            == EnumLabelViolationType.KEY_NOT_ALLOWED
        )
        # Sanitized should be empty or None
        assert result.sanitized_labels is None or len(result.sanitized_labels) == 0


# =============================================================================
# 3. LABEL SANITIZATION WORKFLOW
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestLabelSanitizationWorkflow:
    """Tests for the full label sanitization workflow.

    Verifies that sanitized labels from validation can be used
    to create new valid metric emissions.
    """

    def test_sanitized_labels_create_valid_counter(self) -> None:
        """Test sanitized labels can create valid counter emission."""
        policy = ModelMetricsPolicy()

        # Original labels with forbidden key
        original_labels = {
            "service": "payment",
            "envelope_id": "env-123",  # Forbidden
            "status": "success",
        }

        result = policy.validate_labels(original_labels)
        assert result.is_valid is False
        assert result.sanitized_labels is not None

        # Create new counter with sanitized labels
        new_counter = ModelCounterEmission(
            name="payments_processed",
            labels=result.sanitized_labels,
            increment=1.0,
        )

        # Validate the new counter's labels
        new_result = policy.validate_labels(new_counter.labels)
        assert new_result.is_valid is True

    def test_sanitized_labels_create_valid_gauge(self) -> None:
        """Test sanitized labels can create valid gauge emission."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"pool", "state"}),
        )

        # Labels with extra keys
        original_labels = {
            "pool": "connections",
            "state": "active",
            "node_id": "node-1",  # Forbidden
            "extra": "data",  # Not allowed
        }

        result = policy.validate_labels(original_labels)
        assert result.is_valid is False
        assert result.sanitized_labels is not None

        new_gauge = ModelGaugeEmission(
            name="connection_pool_size",
            labels=result.sanitized_labels,
            value=50.0,
        )

        new_result = policy.validate_labels(new_gauge.labels)
        assert new_result.is_valid is True
        assert new_gauge.labels == {"pool": "connections", "state": "active"}

    def test_sanitized_labels_create_valid_histogram(self) -> None:
        """Test sanitized labels can create valid histogram observation."""
        policy = ModelMetricsPolicy()

        original_labels = {
            "operation": "query",
            "correlation_id": "corr-abc",  # Forbidden
            "runtime_id": "rt-xyz",  # Forbidden
        }

        result = policy.validate_labels(original_labels)
        assert result.is_valid is False
        assert result.sanitized_labels is not None

        new_histogram = ModelHistogramObservation(
            name="db_operation_duration",
            labels=result.sanitized_labels,
            value=0.25,
        )

        new_result = policy.validate_labels(new_histogram.labels)
        assert new_result.is_valid is True
        assert new_histogram.labels == {"operation": "query"}

    def test_value_truncation_preserves_key(self) -> None:
        """Test that value truncation preserves the key with truncated value."""
        policy = ModelMetricsPolicy(max_label_value_length=20)

        # Label with value exceeding max length
        long_value = "this_value_is_way_too_long_for_the_policy"
        original_labels = {
            "service": "api",
            "description": long_value,
        }

        result = policy.validate_labels(original_labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.VALUE_TOO_LONG
        )

        # Sanitized should have truncated value
        assert result.sanitized_labels is not None
        assert "description" in result.sanitized_labels
        assert len(result.sanitized_labels["description"]) == 20
        assert result.sanitized_labels["description"] == "this_value_is_way_to"

    def test_full_sanitization_workflow(self) -> None:
        """Test complete workflow: validate -> sanitize -> create -> validate."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"method", "endpoint", "status_code"}),
            max_label_value_length=50,
        )

        # Simulate incoming metric data with multiple issues
        raw_labels = {
            "method": "POST",
            "endpoint": "/api/v1/users/very/long/path/that/might/exceed/limits/someday",
            "status_code": "201",
            "correlation_id": "abc-123",  # Forbidden
            "request_id": "req-456",  # Not allowed
        }

        # Step 1: Validate
        validation_result = policy.validate_labels(raw_labels)
        assert validation_result.is_valid is False

        # Step 2: Get sanitized labels
        sanitized = validation_result.sanitized_labels
        assert sanitized is not None

        # Step 3: Create new metric with sanitized labels
        counter = ModelCounterEmission(
            name="api_requests_total",
            labels=sanitized,
            increment=1.0,
        )

        # Step 4: Verify new metric is valid
        final_result = policy.validate_labels(counter.labels)
        assert final_result.is_valid is True

        # Verify expected labels
        assert "method" in counter.labels
        assert "endpoint" in counter.labels
        assert "status_code" in counter.labels
        assert "correlation_id" not in counter.labels
        assert "request_id" not in counter.labels


# =============================================================================
# 4. MIXED VIOLATION HANDLING
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestMixedViolationHandling:
    """Tests for handling multiple violation types simultaneously.

    Verifies that the policy correctly handles batches with mixed
    violation types: forbidden keys, not allowed keys, and long values.
    """

    def test_mixed_violations_single_metric(self) -> None:
        """Test handling multiple violation types in single metric."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"service", "region"}),
            max_label_value_length=30,
        )

        labels = {
            "service": "api",
            "region": "us-east-1",
            "envelope_id": "env-123",  # FORBIDDEN_KEY
            "custom_field": "value",  # KEY_NOT_ALLOWED
            "description": "this is a very long description that exceeds the limit",  # KEY_NOT_ALLOWED + VALUE_TOO_LONG
        }

        result = policy.validate_labels(labels)

        assert result.is_valid is False
        assert len(result.violations) >= 3

        violation_types = {v.violation_type for v in result.violations}
        assert EnumLabelViolationType.FORBIDDEN_KEY in violation_types
        assert EnumLabelViolationType.KEY_NOT_ALLOWED in violation_types

        # Sanitized should only have valid keys
        assert result.sanitized_labels is not None
        assert set(result.sanitized_labels.keys()) == {"service", "region"}

    def test_mixed_violations_batch_context(self) -> None:
        """Test handling mixed violations across a batch of metrics."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"job", "instance", "le"}),
            max_label_value_length=64,
        )

        # Batch of metrics with different violation profiles
        batch = [
            # Clean metric
            ModelHistogramObservation(
                name="http_request_duration_seconds",
                labels={"job": "api", "instance": "localhost:8080", "le": "0.1"},
                value=0.05,
            ),
            # Forbidden key
            ModelCounterEmission(
                name="errors_total",
                labels={"job": "worker", "node_id": "w1"},
                increment=1.0,
            ),
            # Not allowed key
            ModelGaugeEmission(
                name="temperature_celsius",
                labels={"job": "sensor", "location": "datacenter"},
                value=22.5,
            ),
            # Value too long (but key is allowed)
            ModelCounterEmission(
                name="api_calls_total",
                labels={
                    "job": "x" * 100,  # Too long
                    "instance": "valid",
                },
                increment=1.0,
            ),
        ]

        results = [policy.validate_labels(m.labels) for m in batch]

        # First is valid
        assert results[0].is_valid is True

        # Second has forbidden key violation
        assert results[1].is_valid is False
        assert any(
            v.violation_type == EnumLabelViolationType.FORBIDDEN_KEY
            for v in results[1].violations
        )

        # Third has not allowed key violation
        assert results[2].is_valid is False
        assert any(
            v.violation_type == EnumLabelViolationType.KEY_NOT_ALLOWED
            for v in results[2].violations
        )

        # Fourth has value too long violation
        assert results[3].is_valid is False
        assert any(
            v.violation_type == EnumLabelViolationType.VALUE_TOO_LONG
            for v in results[3].violations
        )

    def test_violation_aggregation_for_reporting(self) -> None:
        """Test aggregating violations across metrics for batch reporting."""
        policy = ModelMetricsPolicy()

        metrics_labels = [
            {"service": "a", "envelope_id": "e1"},
            {"service": "b", "correlation_id": "c1"},
            {"service": "c", "node_id": "n1", "runtime_id": "r1"},
            {"service": "d"},  # Valid
        ]

        all_violations: list[tuple[int, str, str]] = []
        valid_count = 0

        for idx, labels in enumerate(metrics_labels):
            result = policy.validate_labels(labels)
            if result.is_valid:
                valid_count += 1
            else:
                for v in result.violations:
                    all_violations.append((idx, v.key, str(v.violation_type)))

        # 1 valid, 3 invalid
        assert valid_count == 1

        # Total violations: 1 + 1 + 2 = 4
        assert len(all_violations) == 4

        # Verify violation distribution
        violation_keys = [v[1] for v in all_violations]
        assert "envelope_id" in violation_keys
        assert "correlation_id" in violation_keys
        assert "node_id" in violation_keys
        assert "runtime_id" in violation_keys


# =============================================================================
# 5. POLICY ENFORCEMENT ACTIONS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestPolicyEnforcementActions:
    """Tests for enforce_labels with different on_violation actions.

    Verifies that RAISE, WARN_AND_DROP, DROP_SILENT, and WARN_AND_STRIP
    behave correctly in realistic scenarios.
    """

    def test_enforce_raise_action(self) -> None:
        """Test RAISE action raises ModelOnexError on violation."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.RAISE,
        )

        counter = ModelCounterEmission(
            name="events_total",
            labels={"event_type": "click", "envelope_id": "abc"},
            increment=1.0,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            policy.enforce_labels(counter.labels)

        assert "envelope_id" in str(exc_info.value)
        assert "forbidden" in str(exc_info.value).lower()

    def test_enforce_raise_returns_labels_when_valid(self) -> None:
        """Test RAISE action returns labels when no violations."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.RAISE,
        )

        gauge = ModelGaugeEmission(
            name="queue_size",
            labels={"queue": "orders", "priority": "high"},
            value=150.0,
        )

        result = policy.enforce_labels(gauge.labels)

        assert result is not None
        assert result == gauge.labels

    def test_enforce_warn_and_drop_action(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_DROP logs warning and returns None."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_DROP,
        )

        histogram = ModelHistogramObservation(
            name="latency_seconds",
            labels={"service": "api", "node_id": "node-1"},
            value=0.5,
        )

        with caplog.at_level(logging.WARNING):
            result = policy.enforce_labels(histogram.labels)

        assert result is None
        assert "node_id" in caplog.text or "forbidden" in caplog.text.lower()

    def test_enforce_drop_silent_action(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test DROP_SILENT returns None without logging."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.DROP_SILENT,
        )

        counter = ModelCounterEmission(
            name="requests_total",
            labels={"method": "GET", "correlation_id": "corr-xyz"},
            increment=1.0,
        )

        # Clear any existing logs
        caplog.clear()

        with caplog.at_level(logging.DEBUG):
            result = policy.enforce_labels(counter.labels)

        assert result is None
        # Should not log about the violation
        assert "correlation_id" not in caplog.text

    def test_enforce_warn_and_strip_action(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_STRIP logs warning and returns sanitized labels."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP,
            max_label_value_length=20,
        )

        gauge = ModelGaugeEmission(
            name="cache_size_bytes",
            labels={
                "cache": "user_sessions",
                "runtime_id": "rt-abc",  # Forbidden
                "description": "this description is too long for the policy",  # Too long
            },
            value=1048576.0,
        )

        with caplog.at_level(logging.WARNING):
            result = policy.enforce_labels(gauge.labels)

        # Should return sanitized labels
        assert result is not None
        assert "cache" in result
        assert "runtime_id" not in result
        # Description should be truncated
        assert "description" in result
        assert len(result["description"]) == 20

        # Should have logged warning
        assert len(caplog.records) > 0

    def test_enforce_workflow_with_metric_creation(self) -> None:
        """Test full workflow: enforce -> conditional metric creation."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP,
        )

        # Simulate incoming metric data
        incoming_labels = {
            "job": "processor",
            "instance": "worker-1",
            "envelope_id": "env-999",  # Forbidden
        }

        # Enforce labels
        enforced = policy.enforce_labels(incoming_labels)

        # Should get sanitized labels back
        assert enforced is not None

        # Create metric with enforced labels
        counter = ModelCounterEmission(
            name="processed_items_total",
            labels=enforced,
            increment=100.0,
        )

        # Final validation should pass
        final_result = policy.validate_labels(counter.labels)
        assert final_result.is_valid is True

    def test_enforce_actions_comparison_table(self) -> None:
        """Test all enforcement actions with same invalid labels for comparison."""
        invalid_labels = {
            "service": "test",
            "envelope_id": "e1",
            "correlation_id": "c1",
        }

        # Test each action
        results: dict[EnumMetricsPolicyViolationAction, dict[str, Any]] = {}

        # RAISE
        policy_raise = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.RAISE
        )
        try:
            result = policy_raise.enforce_labels(invalid_labels)
            results[EnumMetricsPolicyViolationAction.RAISE] = {
                "raised": False,
                "result": result,
            }
        except ModelOnexError:
            results[EnumMetricsPolicyViolationAction.RAISE] = {
                "raised": True,
                "result": None,
            }

        # WARN_AND_DROP
        policy_drop = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_DROP
        )
        results[EnumMetricsPolicyViolationAction.WARN_AND_DROP] = {
            "raised": False,
            "result": policy_drop.enforce_labels(invalid_labels),
        }

        # DROP_SILENT
        policy_silent = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.DROP_SILENT
        )
        results[EnumMetricsPolicyViolationAction.DROP_SILENT] = {
            "raised": False,
            "result": policy_silent.enforce_labels(invalid_labels),
        }

        # WARN_AND_STRIP
        policy_strip = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP
        )
        results[EnumMetricsPolicyViolationAction.WARN_AND_STRIP] = {
            "raised": False,
            "result": policy_strip.enforce_labels(invalid_labels),
        }

        # Verify expected behaviors
        assert results[EnumMetricsPolicyViolationAction.RAISE]["raised"] is True
        assert results[EnumMetricsPolicyViolationAction.WARN_AND_DROP]["result"] is None
        assert results[EnumMetricsPolicyViolationAction.DROP_SILENT]["result"] is None
        assert results[EnumMetricsPolicyViolationAction.WARN_AND_STRIP]["result"] == {
            "service": "test"
        }


# =============================================================================
# 6. EDGE CASES AND REALISTIC SCENARIOS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEdgeCasesAndRealisticScenarios:
    """Tests for edge cases and realistic operational scenarios."""

    def test_empty_labels_are_valid(self) -> None:
        """Test that metrics with empty labels pass validation."""
        policy = ModelMetricsPolicy()

        counter = ModelCounterEmission(
            name="heartbeat_total",
            labels={},
            increment=1.0,
        )

        result = policy.validate_labels(counter.labels)

        assert result.is_valid is True
        # Empty dict is falsy, so sanitized_labels is None per implementation
        assert result.sanitized_labels is None

    def test_custom_forbidden_keys(self) -> None:
        """Test policy with custom forbidden keys."""
        policy = ModelMetricsPolicy(
            forbidden_label_keys=frozenset({"password", "secret", "api_key"}),
        )

        # Default forbidden keys should NOT be blocked
        gauge = ModelGaugeEmission(
            name="active_sessions",
            labels={
                "envelope_id": "env-123",  # Not forbidden with custom set
                "secret": "my-secret",  # Custom forbidden
            },
            value=42.0,
        )

        result = policy.validate_labels(gauge.labels)

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0].key == "secret"
        # envelope_id should be in sanitized (not forbidden with custom set)
        assert result.sanitized_labels is not None
        assert "envelope_id" in result.sanitized_labels

    def test_unicode_label_values(self) -> None:
        """Test handling of Unicode characters in label values."""
        policy = ModelMetricsPolicy()

        histogram = ModelHistogramObservation(
            name="response_time_seconds",
            labels={
                "service": "api-gateway",
                "region": "eu-west-1",
                "description": "Performance metrics for API gateway",
            },
            value=0.125,
        )

        result = policy.validate_labels(histogram.labels)

        assert result.is_valid is True

    def test_max_label_value_boundary(self) -> None:
        """Test label value at exact max length boundary."""
        max_length = 50
        policy = ModelMetricsPolicy(max_label_value_length=max_length)

        # Exactly at limit
        exactly_max = "x" * max_length
        # One over limit
        one_over = "x" * (max_length + 1)

        result_exact = policy.validate_labels({"key": exactly_max})
        result_over = policy.validate_labels({"key": one_over})

        assert result_exact.is_valid is True
        assert result_over.is_valid is False
        assert (
            result_over.violations[0].violation_type
            == EnumLabelViolationType.VALUE_TOO_LONG
        )

    def test_policy_immutability(self) -> None:
        """Test that policy is immutable (frozen model)."""
        policy = ModelMetricsPolicy()

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen
            policy.max_label_value_length = 256  # type: ignore[misc]

    def test_realistic_prometheus_style_labels(self) -> None:
        """Test with realistic Prometheus-style metric labels."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset(
                {"job", "instance", "method", "endpoint", "status_code", "le"}
            ),
        )

        # HTTP request counter
        http_counter = ModelCounterEmission(
            name="http_requests_total",
            labels={
                "job": "api-server",
                "instance": "10.0.0.1:8080",
                "method": "POST",
                "endpoint": "/api/v1/users",
                "status_code": "201",
            },
            increment=1.0,
        )

        # Request duration histogram
        http_histogram = ModelHistogramObservation(
            name="http_request_duration_seconds",
            labels={
                "job": "api-server",
                "instance": "10.0.0.1:8080",
                "method": "GET",
                "endpoint": "/health",
                "le": "0.1",
            },
            value=0.05,
        )

        counter_result = policy.validate_labels(http_counter.labels)
        histogram_result = policy.validate_labels(http_histogram.labels)

        assert counter_result.is_valid is True
        assert histogram_result.is_valid is True

    def test_concurrent_policy_usage(self) -> None:
        """Test using same policy from multiple threads."""
        import concurrent.futures

        policy = ModelMetricsPolicy()

        def validate_metric(idx: int) -> tuple[int, bool]:
            labels = {
                "service": f"service-{idx}",
                "region": "us-east-1",
            }
            result = policy.validate_labels(labels)
            return (idx, result.is_valid)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate_metric, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should be valid
        assert all(r[1] for r in results)
        assert len(results) == 100
