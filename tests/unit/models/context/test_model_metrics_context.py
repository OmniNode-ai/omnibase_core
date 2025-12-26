# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelMetricsContext.

This module provides comprehensive tests for the observability and distributed
tracing context model. Tests cover:
- Basic instantiation with valid data
- Default values work correctly
- Immutability (frozen=True)
- from_attributes=True (can create from object with attributes)
- extra="forbid" (extra fields raise error)
- Field validators (trace_id, span_id, sampling_rate)
- Helper methods (is_sampled, has_parent)
"""

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelMetricsContext


# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class MetricsContextAttrs:
    """Helper dataclass for testing from_attributes on ModelMetricsContext."""

    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    sampling_rate: float | None = None
    service_name: str | None = None
    service_version: str | None = None
    environment: str | None = None


# =============================================================================
# ModelMetricsContext Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextInstantiation:
    """Tests for ModelMetricsContext instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating metrics context with all fields populated."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            parent_span_id="a1b2c3d4e5f67890",
            sampling_rate=0.5,
            service_name="onex-gateway",
            service_version="1.2.3",
            environment="prod",
        )
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert context.span_id == "b7ad6b7169203331"
        assert context.parent_span_id == "a1b2c3d4e5f67890"
        assert context.sampling_rate == 0.5
        assert context.service_name == "onex-gateway"
        assert context.service_version == "1.2.3"
        assert context.environment == "prod"

    def test_create_with_partial_fields(self) -> None:
        """Test creating metrics context with partial fields."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            service_name="compute-service",
        )
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert context.service_name == "compute-service"
        assert context.span_id is None
        assert context.parent_span_id is None
        assert context.sampling_rate is None

    def test_create_root_span(self) -> None:
        """Test creating a root span (no parent)."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
        )
        assert context.parent_span_id is None
        assert not context.has_parent()


# =============================================================================
# ModelMetricsContext Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextDefaults:
    """Tests for ModelMetricsContext default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        context = ModelMetricsContext()
        assert context.trace_id is None
        assert context.span_id is None
        assert context.parent_span_id is None
        assert context.sampling_rate is None
        assert context.service_name is None
        assert context.service_version is None
        assert context.environment is None


# =============================================================================
# ModelMetricsContext Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextImmutability:
    """Tests for ModelMetricsContext immutability (frozen=True)."""

    def test_cannot_modify_trace_id(self) -> None:
        """Test that trace_id cannot be modified after creation."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c"
        )
        with pytest.raises(ValidationError):
            context.trace_id = "1111111111111111111111111111111"

    def test_cannot_modify_span_id(self) -> None:
        """Test that span_id cannot be modified after creation."""
        context = ModelMetricsContext(span_id="b7ad6b7169203331")
        with pytest.raises(ValidationError):
            context.span_id = "0000000000000000"

    def test_cannot_modify_sampling_rate(self) -> None:
        """Test that sampling_rate cannot be modified after creation."""
        context = ModelMetricsContext(sampling_rate=0.5)
        with pytest.raises(ValidationError):
            context.sampling_rate = 1.0

    def test_cannot_modify_service_name(self) -> None:
        """Test that service_name cannot be modified after creation."""
        context = ModelMetricsContext(service_name="original")
        with pytest.raises(ValidationError):
            context.service_name = "modified"


# =============================================================================
# ModelMetricsContext from_attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextFromAttributes:
    """Tests for ModelMetricsContext from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelMetricsContext from an object with attributes."""
        attrs = MetricsContextAttrs(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            service_name="test-service",
        )
        context = ModelMetricsContext.model_validate(attrs)
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert context.span_id == "b7ad6b7169203331"
        assert context.service_name == "test-service"

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        attrs = MetricsContextAttrs(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            parent_span_id="a1b2c3d4e5f67890",
            sampling_rate=0.75,
            service_name="full-service",
            service_version="2.0.0",
            environment="staging",
        )
        context = ModelMetricsContext.model_validate(attrs)
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert context.environment == "staging"
        assert context.sampling_rate == 0.75


# =============================================================================
# ModelMetricsContext extra="forbid" Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextExtraForbid:
    """Tests for ModelMetricsContext extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                unknown_field="should_fail",
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# ModelMetricsContext Field Validator Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextTraceIdValidator:
    """Tests for trace_id field validator."""

    def test_valid_trace_id_32_hex_chars(self) -> None:
        """Test valid trace_id with 32 hex characters."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c"
        )
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"

    def test_trace_id_normalized_to_lowercase(self) -> None:
        """Test that trace_id is normalized to lowercase."""
        context = ModelMetricsContext(
            trace_id="0AF7651916CD43DD8448EB211C80319C"
        )
        assert context.trace_id == "0af7651916cd43dd8448eb211c80319c"

    def test_invalid_trace_id_too_short(self) -> None:
        """Test invalid trace_id with fewer than 32 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(trace_id="0af7651916cd43dd")
        assert "32 lowercase hex characters" in str(exc_info.value)

    def test_invalid_trace_id_too_long(self) -> None:
        """Test invalid trace_id with more than 32 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(
                trace_id="0af7651916cd43dd8448eb211c80319c0000"
            )
        assert "32 lowercase hex characters" in str(exc_info.value)

    def test_invalid_trace_id_non_hex_chars(self) -> None:
        """Test invalid trace_id with non-hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(trace_id="0af7651916cd43dd8448eb211c80319g")
        assert "32 lowercase hex characters" in str(exc_info.value)

    def test_trace_id_none_is_valid(self) -> None:
        """Test that None is valid for trace_id."""
        context = ModelMetricsContext(trace_id=None)
        assert context.trace_id is None


@pytest.mark.unit
class TestModelMetricsContextSpanIdValidator:
    """Tests for span_id and parent_span_id field validators."""

    def test_valid_span_id_16_hex_chars(self) -> None:
        """Test valid span_id with 16 hex characters."""
        context = ModelMetricsContext(span_id="b7ad6b7169203331")
        assert context.span_id == "b7ad6b7169203331"

    def test_span_id_normalized_to_lowercase(self) -> None:
        """Test that span_id is normalized to lowercase."""
        context = ModelMetricsContext(span_id="B7AD6B7169203331")
        assert context.span_id == "b7ad6b7169203331"

    def test_invalid_span_id_too_short(self) -> None:
        """Test invalid span_id with fewer than 16 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(span_id="b7ad6b71")
        assert "16 lowercase hex characters" in str(exc_info.value)

    def test_invalid_span_id_too_long(self) -> None:
        """Test invalid span_id with more than 16 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(span_id="b7ad6b716920333100")
        assert "16 lowercase hex characters" in str(exc_info.value)

    def test_invalid_span_id_non_hex_chars(self) -> None:
        """Test invalid span_id with non-hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(span_id="b7ad6b716920333z")
        assert "16 lowercase hex characters" in str(exc_info.value)

    def test_span_id_none_is_valid(self) -> None:
        """Test that None is valid for span_id."""
        context = ModelMetricsContext(span_id=None)
        assert context.span_id is None

    def test_valid_parent_span_id_16_hex_chars(self) -> None:
        """Test valid parent_span_id with 16 hex characters."""
        context = ModelMetricsContext(parent_span_id="a1b2c3d4e5f67890")
        assert context.parent_span_id == "a1b2c3d4e5f67890"

    def test_parent_span_id_normalized_to_lowercase(self) -> None:
        """Test that parent_span_id is normalized to lowercase."""
        context = ModelMetricsContext(parent_span_id="A1B2C3D4E5F67890")
        assert context.parent_span_id == "a1b2c3d4e5f67890"

    def test_invalid_parent_span_id(self) -> None:
        """Test invalid parent_span_id format."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(parent_span_id="invalid")
        assert "16 lowercase hex characters" in str(exc_info.value)


@pytest.mark.unit
class TestModelMetricsContextSamplingRateValidator:
    """Tests for sampling_rate field validator."""

    def test_valid_sampling_rate_zero(self) -> None:
        """Test valid sampling_rate of 0.0."""
        context = ModelMetricsContext(sampling_rate=0.0)
        assert context.sampling_rate == 0.0

    def test_valid_sampling_rate_one(self) -> None:
        """Test valid sampling_rate of 1.0."""
        context = ModelMetricsContext(sampling_rate=1.0)
        assert context.sampling_rate == 1.0

    def test_valid_sampling_rate_mid_range(self) -> None:
        """Test valid sampling_rate in middle of range."""
        context = ModelMetricsContext(sampling_rate=0.5)
        assert context.sampling_rate == 0.5

    def test_invalid_sampling_rate_negative(self) -> None:
        """Test invalid sampling_rate with negative value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(sampling_rate=-0.1)
        assert "between 0.0 and 1.0" in str(exc_info.value)

    def test_invalid_sampling_rate_above_one(self) -> None:
        """Test invalid sampling_rate above 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMetricsContext(sampling_rate=1.1)
        assert "between 0.0 and 1.0" in str(exc_info.value)

    def test_sampling_rate_none_is_valid(self) -> None:
        """Test that None is valid for sampling_rate."""
        context = ModelMetricsContext(sampling_rate=None)
        assert context.sampling_rate is None


# =============================================================================
# ModelMetricsContext Helper Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextIsSampled:
    """Tests for is_sampled() helper method."""

    def test_is_sampled_when_sampling_rate_none(self) -> None:
        """Test is_sampled returns True when sampling_rate is None."""
        context = ModelMetricsContext(sampling_rate=None)
        assert context.is_sampled() is True

    def test_is_sampled_when_sampling_rate_positive(self) -> None:
        """Test is_sampled returns True when sampling_rate > 0."""
        context = ModelMetricsContext(sampling_rate=0.1)
        assert context.is_sampled() is True

    def test_is_sampled_when_sampling_rate_one(self) -> None:
        """Test is_sampled returns True when sampling_rate is 1.0."""
        context = ModelMetricsContext(sampling_rate=1.0)
        assert context.is_sampled() is True

    def test_is_not_sampled_when_sampling_rate_zero(self) -> None:
        """Test is_sampled returns False when sampling_rate is 0."""
        context = ModelMetricsContext(sampling_rate=0.0)
        assert context.is_sampled() is False


@pytest.mark.unit
class TestModelMetricsContextHasParent:
    """Tests for has_parent() helper method."""

    def test_has_parent_when_parent_span_id_set(self) -> None:
        """Test has_parent returns True when parent_span_id is set."""
        context = ModelMetricsContext(parent_span_id="a1b2c3d4e5f67890")
        assert context.has_parent() is True

    def test_has_no_parent_when_parent_span_id_none(self) -> None:
        """Test has_parent returns False when parent_span_id is None."""
        context = ModelMetricsContext(parent_span_id=None)
        assert context.has_parent() is False

    def test_has_no_parent_for_empty_context(self) -> None:
        """Test has_parent returns False for empty context."""
        context = ModelMetricsContext()
        assert context.has_parent() is False


# =============================================================================
# ModelMetricsContext Common Behavior Tests
# =============================================================================


@pytest.mark.unit
class TestModelMetricsContextCommonBehavior:
    """Tests for common Pydantic model behavior."""

    def test_is_hashable(self) -> None:
        """Test that frozen model can be hashed."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            service_name="test-service",
        )
        # Should not raise - model is hashable
        hash(context)

    def test_supports_model_dump(self) -> None:
        """Test that model supports model_dump serialization."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            sampling_rate=0.5,
            environment="prod",
        )
        data = context.model_dump()
        assert isinstance(data, dict)
        assert data["trace_id"] == "0af7651916cd43dd8448eb211c80319c"
        assert data["sampling_rate"] == 0.5
        assert data["environment"] == "prod"

    def test_supports_model_dump_json(self) -> None:
        """Test that model supports model_dump_json serialization."""
        context = ModelMetricsContext(
            service_name="json-test",
            service_version="1.0.0",
        )
        json_str = context.model_dump_json()
        assert isinstance(json_str, str)
        assert "json-test" in json_str
        assert "1.0.0" in json_str

    def test_equality(self) -> None:
        """Test that models with same values are equal."""
        context1 = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            sampling_rate=0.5,
        )
        context2 = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            sampling_rate=0.5,
        )
        assert context1 == context2

    def test_inequality(self) -> None:
        """Test that models with different values are not equal."""
        context1 = ModelMetricsContext(sampling_rate=0.5)
        context2 = ModelMetricsContext(sampling_rate=0.6)
        assert context1 != context2

    def test_supports_copy(self) -> None:
        """Test that model can be copied with model_copy."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            service_name="original",
        )
        context_copy = context.model_copy()
        assert context == context_copy
        assert context is not context_copy

    def test_supports_copy_with_update(self) -> None:
        """Test that model can be copied with updates."""
        context = ModelMetricsContext(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            service_name="original",
        )
        updated = context.model_copy(update={"environment": "staging"})
        assert updated.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert updated.service_name == "original"
        assert updated.environment == "staging"
