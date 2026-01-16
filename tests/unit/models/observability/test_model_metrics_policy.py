"""Unit tests for ModelMetricsPolicy."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType
from omnibase_core.enums.enum_metrics_policy_violation_action import (
    EnumMetricsPolicyViolationAction,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.observability.model_metrics_policy import ModelMetricsPolicy


class TestModelMetricsPolicyDefaults:
    """Tests for ModelMetricsPolicy default values."""

    def test_default_forbidden_labels(self) -> None:
        """Test default forbidden labels are set correctly."""
        policy = ModelMetricsPolicy()
        expected = frozenset({"envelope_id", "correlation_id", "node_id", "runtime_id"})
        assert policy.forbidden_label_keys == expected

    def test_default_violation_action(self) -> None:
        """Test default violation action is WARN_AND_DROP."""
        policy = ModelMetricsPolicy()
        assert policy.on_violation == EnumMetricsPolicyViolationAction.WARN_AND_DROP

    def test_default_max_label_value_length(self) -> None:
        """Test default max label value length."""
        policy = ModelMetricsPolicy()
        assert policy.max_label_value_length == 128

    def test_default_allowed_label_keys_is_none(self) -> None:
        """Test allowed_label_keys defaults to None (permissive mode)."""
        policy = ModelMetricsPolicy()
        assert policy.allowed_label_keys is None


class TestModelMetricsPolicyCustomization:
    """Tests for ModelMetricsPolicy customization."""

    def test_custom_forbidden_labels(self) -> None:
        """Test custom forbidden labels."""
        custom_forbidden = frozenset({"user_id", "session_id", "email"})
        policy = ModelMetricsPolicy(forbidden_label_keys=custom_forbidden)
        assert policy.forbidden_label_keys == custom_forbidden

    def test_extend_default_forbidden_labels(self) -> None:
        """Test extending default forbidden labels."""
        extended = ModelMetricsPolicy.DEFAULT_FORBIDDEN | frozenset({"user_id"})
        policy = ModelMetricsPolicy(forbidden_label_keys=extended)
        assert "user_id" in policy.forbidden_label_keys
        assert "envelope_id" in policy.forbidden_label_keys

    def test_allowed_label_keys_strict_mode(self) -> None:
        """Test strict mode with allowed label keys."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"method", "status", "endpoint"})
        )
        assert policy.allowed_label_keys is not None
        assert len(policy.allowed_label_keys) == 3

    def test_custom_max_label_value_length(self) -> None:
        """Test custom max label value length."""
        policy = ModelMetricsPolicy(max_label_value_length=64)
        assert policy.max_label_value_length == 64

    def test_max_label_value_length_bounds(self) -> None:
        """Test max_label_value_length bounds validation."""
        # Valid minimum
        policy = ModelMetricsPolicy(max_label_value_length=1)
        assert policy.max_label_value_length == 1

        # Valid maximum
        policy = ModelMetricsPolicy(max_label_value_length=1024)
        assert policy.max_label_value_length == 1024

        # Below minimum
        with pytest.raises(ValidationError):
            ModelMetricsPolicy(max_label_value_length=0)

        # Above maximum
        with pytest.raises(ValidationError):
            ModelMetricsPolicy(max_label_value_length=1025)


class TestModelMetricsPolicyValidateLabels:
    """Tests for ModelMetricsPolicy.validate_labels method."""

    def test_valid_labels_permissive_mode(self) -> None:
        """Test valid labels pass in permissive mode."""
        policy = ModelMetricsPolicy()
        result = policy.validate_labels({"method": "GET", "status": "200"})

        assert result.is_valid is True
        assert result.violations == []
        assert result.sanitized_labels == {"method": "GET", "status": "200"}

    def test_forbidden_label_detected(self) -> None:
        """Test forbidden labels are detected."""
        policy = ModelMetricsPolicy()
        result = policy.validate_labels(
            {"method": "GET", "envelope_id": "abc123", "status": "200"}
        )

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.FORBIDDEN_KEY
        )
        assert result.violations[0].key == "envelope_id"
        # Sanitized should not include forbidden key
        assert "envelope_id" not in (result.sanitized_labels or {})
        assert result.sanitized_labels == {"method": "GET", "status": "200"}

    def test_multiple_forbidden_labels(self) -> None:
        """Test multiple forbidden labels are all detected."""
        policy = ModelMetricsPolicy()
        result = policy.validate_labels(
            {
                "envelope_id": "a",
                "correlation_id": "b",
                "node_id": "c",
                "runtime_id": "d",
            }
        )

        assert result.is_valid is False
        assert len(result.violations) == 4
        forbidden_keys = {v.key for v in result.violations}
        assert forbidden_keys == {
            "envelope_id",
            "correlation_id",
            "node_id",
            "runtime_id",
        }
        # All labels were invalid
        assert result.sanitized_labels is None

    def test_strict_mode_allowed_only(self) -> None:
        """Test strict mode only allows specified keys."""
        policy = ModelMetricsPolicy(allowed_label_keys=frozenset({"method", "status"}))
        result = policy.validate_labels(
            {"method": "GET", "status": "200", "endpoint": "/api"}
        )

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type
            == EnumLabelViolationType.KEY_NOT_ALLOWED
        )
        assert result.violations[0].key == "endpoint"

    def test_strict_mode_forbidden_wins_over_allowed(self) -> None:
        """Test that forbidden labels are rejected even if in allowed list."""
        # This is a policy configuration error but the behavior should be safe
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"method", "envelope_id"}),
            forbidden_label_keys=frozenset({"envelope_id"}),
        )
        result = policy.validate_labels({"method": "GET", "envelope_id": "abc"})

        assert result.is_valid is False
        # envelope_id should be FORBIDDEN_KEY, not KEY_NOT_ALLOWED
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.FORBIDDEN_KEY
        )

    def test_value_too_long(self) -> None:
        """Test label value length validation."""
        policy = ModelMetricsPolicy(max_label_value_length=10)
        result = policy.validate_labels({"short": "ok", "long_value": "x" * 15})

        assert result.is_valid is False
        assert len(result.violations) == 1
        assert (
            result.violations[0].violation_type == EnumLabelViolationType.VALUE_TOO_LONG
        )
        assert result.violations[0].key == "long_value"
        # Sanitized should have truncated value
        assert result.sanitized_labels is not None
        assert result.sanitized_labels["short"] == "ok"
        assert result.sanitized_labels["long_value"] == "x" * 10

    def test_value_at_max_length_is_valid(self) -> None:
        """Test that value exactly at max length is valid."""
        policy = ModelMetricsPolicy(max_label_value_length=10)
        result = policy.validate_labels({"exact": "x" * 10})

        assert result.is_valid is True
        assert result.sanitized_labels == {"exact": "x" * 10}

    def test_empty_labels(self) -> None:
        """Test empty labels dict is valid."""
        policy = ModelMetricsPolicy()
        result = policy.validate_labels({})

        assert result.is_valid is True
        assert result.violations == []
        assert result.sanitized_labels is None  # No labels to sanitize

    def test_combined_violations(self) -> None:
        """Test multiple types of violations in same validation."""
        policy = ModelMetricsPolicy(
            max_label_value_length=5,
            allowed_label_keys=frozenset({"method", "status"}),
        )
        result = policy.validate_labels(
            {
                "method": "GET",
                "envelope_id": "abc",  # forbidden
                "unknown": "x",  # not allowed
                "status": "long_value",  # too long
            }
        )

        assert result.is_valid is False
        violation_types = {v.violation_type for v in result.violations}
        assert EnumLabelViolationType.FORBIDDEN_KEY in violation_types
        assert EnumLabelViolationType.KEY_NOT_ALLOWED in violation_types
        assert EnumLabelViolationType.VALUE_TOO_LONG in violation_types


class TestModelMetricsPolicyModel:
    """Tests for ModelMetricsPolicy as a Pydantic model."""

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        policy = ModelMetricsPolicy()
        with pytest.raises(ValidationError):
            policy.max_label_value_length = 256  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsPolicy(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_class_constant_available(self) -> None:
        """Test DEFAULT_FORBIDDEN class constant is accessible."""
        assert (
            frozenset({"envelope_id", "correlation_id", "node_id", "runtime_id"})
            == ModelMetricsPolicy.DEFAULT_FORBIDDEN
        )


class TestModelMetricsPolicyEnforceLabels:
    """Tests for ModelMetricsPolicy.enforce_labels method."""

    def test_enforce_valid_labels_returns_original(self) -> None:
        """Test that valid labels are returned unchanged."""
        policy = ModelMetricsPolicy()
        labels = {"method": "GET", "status": "200"}
        result = policy.enforce_labels(labels)
        assert result == labels

    def test_enforce_raise_on_violation(self) -> None:
        """Test RAISE action raises ModelOnexError on violation."""
        policy = ModelMetricsPolicy(on_violation=EnumMetricsPolicyViolationAction.RAISE)
        with pytest.raises(ModelOnexError) as exc_info:
            policy.enforce_labels({"envelope_id": "abc", "method": "GET"})
        assert "Metrics policy violation" in str(exc_info.value)
        assert "envelope_id" in str(exc_info.value)

    def test_enforce_raise_with_multiple_violations(self) -> None:
        """Test RAISE action includes all violations in error message."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.RAISE,
            max_label_value_length=5,
        )
        with pytest.raises(ModelOnexError) as exc_info:
            policy.enforce_labels({"envelope_id": "abc", "status": "toolong"})
        error_msg = str(exc_info.value)
        assert "envelope_id" in error_msg
        assert "status" in error_msg

    def test_enforce_warn_and_drop_returns_none(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_DROP action logs warning and returns None."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_DROP
        )
        result = policy.enforce_labels({"envelope_id": "abc"})
        assert result is None
        assert "Dropping metric due to policy violation" in caplog.text
        assert "envelope_id" in caplog.text

    def test_enforce_drop_silent_returns_none_no_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test DROP_SILENT action returns None without logging."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.DROP_SILENT
        )
        result = policy.enforce_labels({"envelope_id": "abc"})
        assert result is None
        # Should not log anything
        assert "Dropping" not in caplog.text
        assert "Stripping" not in caplog.text

    def test_enforce_warn_and_strip_returns_sanitized(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_STRIP action logs warning and returns sanitized labels."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP
        )
        result = policy.enforce_labels(
            {"envelope_id": "abc", "method": "GET", "status": "200"}
        )
        # Should return sanitized (without forbidden key)
        assert result == {"method": "GET", "status": "200"}
        assert "Stripping invalid labels" in caplog.text
        assert "envelope_id" in caplog.text

    def test_enforce_warn_and_strip_with_truncation(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_STRIP truncates long values."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP,
            max_label_value_length=5,
        )
        result = policy.enforce_labels({"status": "toolongvalue"})
        assert result is not None
        assert result["status"] == "toolo"  # Truncated to 5 chars
        assert "Stripping" in caplog.text

    def test_enforce_warn_and_strip_all_invalid_returns_none(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test WARN_AND_STRIP returns None when all labels are invalid."""
        policy = ModelMetricsPolicy(
            on_violation=EnumMetricsPolicyViolationAction.WARN_AND_STRIP
        )
        # All labels are forbidden
        result = policy.enforce_labels({"envelope_id": "a", "correlation_id": "b"})
        # sanitized_labels would be None, so enforce_labels returns None
        assert result is None

    def test_enforce_empty_labels_returns_empty(self) -> None:
        """Test that empty labels pass enforcement."""
        policy = ModelMetricsPolicy(on_violation=EnumMetricsPolicyViolationAction.RAISE)
        result = policy.enforce_labels({})
        # Empty dict is valid, returns original
        assert result == {}

    def test_enforce_with_strict_mode(self) -> None:
        """Test enforce_labels works with strict mode (allowed_label_keys)."""
        policy = ModelMetricsPolicy(
            allowed_label_keys=frozenset({"method", "status"}),
            on_violation=EnumMetricsPolicyViolationAction.RAISE,
        )
        # Valid labels in strict mode
        result = policy.enforce_labels({"method": "GET", "status": "200"})
        assert result == {"method": "GET", "status": "200"}

        # Invalid label in strict mode
        with pytest.raises(ModelOnexError) as exc_info:
            policy.enforce_labels({"method": "GET", "endpoint": "/api"})
        assert "endpoint" in str(exc_info.value)
