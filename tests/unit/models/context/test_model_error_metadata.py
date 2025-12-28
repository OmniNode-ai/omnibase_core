# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelErrorMetadata.

This module provides comprehensive tests for the ModelErrorMetadata model,
covering:
- Basic instantiation with valid data
- Default values work correctly
- Field validation (retry_count >= 0, error_code format)
- Helper methods (should_retry, is_client_error, is_server_error)
- Immutability (frozen=True)
- from_attributes=True (can create from object with attributes)
- extra="forbid" (extra fields raise error)
- Edge cases and boundary conditions
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelErrorMetadata

# Test configuration constants
UNIT_TEST_TIMEOUT_SECONDS: int = 30


# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class ErrorMetadataAttrs:
    """Helper dataclass for testing from_attributes on ModelErrorMetadata."""

    error_code: str | None = None
    error_category: str | None = None
    correlation_id: str | None = None
    stack_trace_id: UUID | None = None
    retry_count: int | None = None
    is_retryable: bool | None = None


# =============================================================================
# ModelErrorMetadata Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataInstantiation:
    """Tests for ModelErrorMetadata instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating error metadata with all fields populated."""
        stack_trace_uuid = uuid4()
        metadata = ModelErrorMetadata(
            error_code="AUTH_001",
            error_category="auth",
            correlation_id="req_abc123",
            stack_trace_id=stack_trace_uuid,
            retry_count=2,
            is_retryable=True,
        )
        assert metadata.error_code == "AUTH_001"
        assert metadata.error_category == "auth"
        assert metadata.correlation_id == "req_abc123"
        assert metadata.stack_trace_id == stack_trace_uuid
        assert metadata.retry_count == 2
        assert metadata.is_retryable is True

    def test_create_with_partial_fields(self) -> None:
        """Test creating error metadata with partial fields."""
        metadata = ModelErrorMetadata(
            error_code="VALIDATION_123",
            error_category="validation",
        )
        assert metadata.error_code == "VALIDATION_123"
        assert metadata.error_category == "validation"
        assert metadata.correlation_id is None
        assert metadata.stack_trace_id is None
        assert metadata.retry_count is None
        assert metadata.is_retryable is None

    def test_create_with_zero_retry_count(self) -> None:
        """Test creating error metadata with retry_count of 0."""
        metadata = ModelErrorMetadata(
            error_code="NETWORK_001",
            retry_count=0,
            is_retryable=True,
        )
        assert metadata.retry_count == 0
        assert metadata.is_retryable is True


# =============================================================================
# ModelErrorMetadata Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataDefaults:
    """Tests for ModelErrorMetadata default values."""

    def test_all_defaults_are_none(self) -> None:
        """Test that all fields default to None."""
        metadata = ModelErrorMetadata()
        assert metadata.error_code is None
        assert metadata.error_category is None
        assert metadata.correlation_id is None
        assert metadata.stack_trace_id is None
        assert metadata.retry_count is None
        assert metadata.is_retryable is None


# =============================================================================
# ModelErrorMetadata Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataValidation:
    """Tests for ModelErrorMetadata field validation."""

    def test_valid_error_code_formats(self) -> None:
        """Test various valid error code formats."""
        valid_codes = [
            "AUTH_001",
            "VALIDATION_123",
            "SYSTEM_01",
            "NETWORK_9999",
            "DB_1",
            "RATE_LIMIT_001",
            "INTERNAL_SERVER_500",
            "A_1",
        ]
        for code in valid_codes:
            metadata = ModelErrorMetadata(error_code=code)
            assert metadata.error_code == code

    def test_invalid_error_code_format_lowercase(self) -> None:
        """Test that lowercase error codes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(error_code="auth_001")
        assert "error_code" in str(exc_info.value).lower()

    def test_invalid_error_code_format_no_number(self) -> None:
        """Test that error codes without numbers are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(error_code="AUTH_")
        assert "error_code" in str(exc_info.value).lower()

    def test_invalid_error_code_format_no_underscore(self) -> None:
        """Test that error codes without underscore are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(error_code="AUTH001")
        assert "error_code" in str(exc_info.value).lower()

    def test_invalid_error_code_format_starts_with_number(self) -> None:
        """Test that error codes starting with number are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(error_code="1AUTH_001")
        assert "error_code" in str(exc_info.value).lower()

    def test_retry_count_non_negative_zero(self) -> None:
        """Test that retry_count of 0 is valid."""
        metadata = ModelErrorMetadata(retry_count=0)
        assert metadata.retry_count == 0

    def test_retry_count_positive(self) -> None:
        """Test that positive retry_count is valid."""
        metadata = ModelErrorMetadata(retry_count=5)
        assert metadata.retry_count == 5

    def test_retry_count_negative_rejected(self) -> None:
        """Test that negative retry_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(retry_count=-1)
        assert "retry_count" in str(exc_info.value).lower()

    def test_retry_count_large_negative_rejected(self) -> None:
        """Test that large negative retry_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(retry_count=-100)
        assert "retry_count" in str(exc_info.value).lower()


# =============================================================================
# ModelErrorMetadata Helper Methods Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataShouldRetry:
    """Tests for ModelErrorMetadata.should_retry() method."""

    def test_should_retry_when_retryable_and_under_limit(self) -> None:
        """Test should_retry returns True when conditions are met."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=1,
        )
        assert metadata.should_retry(max_retries=3) is True

    def test_should_retry_at_zero_count(self) -> None:
        """Test should_retry with retry_count of 0."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=0,
        )
        assert metadata.should_retry(max_retries=3) is True

    def test_should_retry_at_limit(self) -> None:
        """Test should_retry when retry_count equals max_retries."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=3,
        )
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_over_limit(self) -> None:
        """Test should_retry when retry_count exceeds max_retries."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=5,
        )
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_not_retryable_false(self) -> None:
        """Test should_retry returns False when is_retryable is False."""
        metadata = ModelErrorMetadata(
            is_retryable=False,
            retry_count=0,
        )
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_not_retryable_none(self) -> None:
        """Test should_retry returns False when is_retryable is None."""
        metadata = ModelErrorMetadata(
            is_retryable=None,
            retry_count=0,
        )
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_count_none(self) -> None:
        """Test should_retry returns False when retry_count is None."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=None,
        )
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_both_none(self) -> None:
        """Test should_retry returns False when both fields are None."""
        metadata = ModelErrorMetadata()
        assert metadata.should_retry(max_retries=3) is False

    def test_should_retry_custom_max_retries(self) -> None:
        """Test should_retry with custom max_retries value."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=5,
        )
        assert metadata.should_retry(max_retries=5) is False
        assert metadata.should_retry(max_retries=6) is True
        assert metadata.should_retry(max_retries=10) is True

    def test_should_retry_default_max_retries(self) -> None:
        """Test should_retry uses default max_retries of 3."""
        metadata = ModelErrorMetadata(
            is_retryable=True,
            retry_count=2,
        )
        assert metadata.should_retry() is True  # 2 < 3

        metadata2 = ModelErrorMetadata(
            is_retryable=True,
            retry_count=3,
        )
        assert metadata2.should_retry() is False  # 3 >= 3


@pytest.mark.unit
class TestModelErrorMetadataIsClientError:
    """Tests for ModelErrorMetadata.is_client_error() method."""

    def test_is_client_error_validation(self) -> None:
        """Test is_client_error returns True for validation category."""
        metadata = ModelErrorMetadata(error_category="validation")
        assert metadata.is_client_error() is True

    def test_is_client_error_auth(self) -> None:
        """Test is_client_error returns True for auth category."""
        metadata = ModelErrorMetadata(error_category="auth")
        assert metadata.is_client_error() is True

    def test_is_client_error_system(self) -> None:
        """Test is_client_error returns False for system category."""
        metadata = ModelErrorMetadata(error_category="system")
        assert metadata.is_client_error() is False

    def test_is_client_error_network(self) -> None:
        """Test is_client_error returns False for network category."""
        metadata = ModelErrorMetadata(error_category="network")
        assert metadata.is_client_error() is False

    def test_is_client_error_none(self) -> None:
        """Test is_client_error returns False when category is None."""
        metadata = ModelErrorMetadata(error_category=None)
        assert metadata.is_client_error() is False

    def test_is_client_error_unknown_category(self) -> None:
        """Test is_client_error returns False for unknown category."""
        metadata = ModelErrorMetadata(error_category="unknown")
        assert metadata.is_client_error() is False


@pytest.mark.unit
class TestModelErrorMetadataIsServerError:
    """Tests for ModelErrorMetadata.is_server_error() method."""

    def test_is_server_error_system(self) -> None:
        """Test is_server_error returns True for system category."""
        metadata = ModelErrorMetadata(error_category="system")
        assert metadata.is_server_error() is True

    def test_is_server_error_network(self) -> None:
        """Test is_server_error returns True for network category."""
        metadata = ModelErrorMetadata(error_category="network")
        assert metadata.is_server_error() is True

    def test_is_server_error_validation(self) -> None:
        """Test is_server_error returns False for validation category."""
        metadata = ModelErrorMetadata(error_category="validation")
        assert metadata.is_server_error() is False

    def test_is_server_error_auth(self) -> None:
        """Test is_server_error returns False for auth category."""
        metadata = ModelErrorMetadata(error_category="auth")
        assert metadata.is_server_error() is False

    def test_is_server_error_none(self) -> None:
        """Test is_server_error returns False when category is None."""
        metadata = ModelErrorMetadata(error_category=None)
        assert metadata.is_server_error() is False

    def test_is_server_error_unknown_category(self) -> None:
        """Test is_server_error returns False for unknown category."""
        metadata = ModelErrorMetadata(error_category="unknown")
        assert metadata.is_server_error() is False


@pytest.mark.unit
class TestModelErrorMetadataHelperMethodsOrthogonality:
    """Tests for orthogonality of is_client_error and is_server_error."""

    def test_client_and_server_mutually_exclusive_validation(self) -> None:
        """Test validation is client-only, not server."""
        metadata = ModelErrorMetadata(error_category="validation")
        assert metadata.is_client_error() is True
        assert metadata.is_server_error() is False

    def test_client_and_server_mutually_exclusive_auth(self) -> None:
        """Test auth is client-only, not server."""
        metadata = ModelErrorMetadata(error_category="auth")
        assert metadata.is_client_error() is True
        assert metadata.is_server_error() is False

    def test_client_and_server_mutually_exclusive_system(self) -> None:
        """Test system is server-only, not client."""
        metadata = ModelErrorMetadata(error_category="system")
        assert metadata.is_client_error() is False
        assert metadata.is_server_error() is True

    def test_client_and_server_mutually_exclusive_network(self) -> None:
        """Test network is server-only, not client."""
        metadata = ModelErrorMetadata(error_category="network")
        assert metadata.is_client_error() is False
        assert metadata.is_server_error() is True

    def test_neither_client_nor_server_when_none(self) -> None:
        """Test neither client nor server error when category is None."""
        metadata = ModelErrorMetadata()
        assert metadata.is_client_error() is False
        assert metadata.is_server_error() is False


# =============================================================================
# ModelErrorMetadata Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataImmutability:
    """Tests for ModelErrorMetadata immutability (frozen=True)."""

    def test_cannot_modify_error_code(self) -> None:
        """Test that error_code cannot be modified after creation."""
        metadata = ModelErrorMetadata(error_code="AUTH_001")
        with pytest.raises(ValidationError):
            metadata.error_code = "AUTH_002"

    def test_cannot_modify_error_category(self) -> None:
        """Test that error_category cannot be modified after creation."""
        metadata = ModelErrorMetadata(error_category="auth")
        with pytest.raises(ValidationError):
            metadata.error_category = "system"

    def test_cannot_modify_correlation_id(self) -> None:
        """Test that correlation_id cannot be modified after creation."""
        metadata = ModelErrorMetadata(correlation_id="req_123")
        with pytest.raises(ValidationError):
            metadata.correlation_id = "req_456"

    def test_cannot_modify_retry_count(self) -> None:
        """Test that retry_count cannot be modified after creation."""
        metadata = ModelErrorMetadata(retry_count=1)
        with pytest.raises(ValidationError):
            metadata.retry_count = 2

    def test_cannot_modify_is_retryable(self) -> None:
        """Test that is_retryable cannot be modified after creation."""
        metadata = ModelErrorMetadata(is_retryable=True)
        with pytest.raises(ValidationError):
            metadata.is_retryable = False


# =============================================================================
# ModelErrorMetadata from_attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataFromAttributes:
    """Tests for ModelErrorMetadata from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelErrorMetadata from an object with attributes."""
        attrs = ErrorMetadataAttrs(
            error_code="NETWORK_001",
            error_category="network",
            correlation_id="req_from_attrs",
        )
        metadata = ModelErrorMetadata.model_validate(attrs)
        assert metadata.error_code == "NETWORK_001"
        assert metadata.error_category == "network"
        assert metadata.correlation_id == "req_from_attrs"

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        stack_trace_uuid = uuid4()
        attrs = ErrorMetadataAttrs(
            error_code="SYSTEM_500",
            error_category="system",
            correlation_id="req_full",
            stack_trace_id=stack_trace_uuid,
            retry_count=3,
            is_retryable=False,
        )
        metadata = ModelErrorMetadata.model_validate(attrs)
        assert metadata.error_code == "SYSTEM_500"
        assert metadata.error_category == "system"
        assert metadata.correlation_id == "req_full"
        assert metadata.stack_trace_id == stack_trace_uuid
        assert metadata.retry_count == 3
        assert metadata.is_retryable is False

    def test_create_from_empty_object(self) -> None:
        """Test creating from object with all None attributes."""
        attrs = ErrorMetadataAttrs()
        metadata = ModelErrorMetadata.model_validate(attrs)
        assert metadata.error_code is None
        assert metadata.error_category is None
        assert metadata.correlation_id is None
        assert metadata.retry_count is None


# =============================================================================
# ModelErrorMetadata extra="forbid" Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataExtraForbid:
    """Tests for ModelErrorMetadata extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(
                error_code="AUTH_001",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()

    def test_multiple_extra_fields_raise_error(self) -> None:
        """Test that multiple extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelErrorMetadata(
                error_code="AUTH_001",
                unknown_field="should_fail",  # type: ignore[call-arg]
                another_unknown="also_fail",
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# ModelErrorMetadata Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestModelErrorMetadataEdgeCases:
    """Tests for ModelErrorMetadata edge cases."""

    def test_empty_string_error_code_rejected(self) -> None:
        """Test that empty string error_code is rejected."""
        with pytest.raises(ValidationError):
            ModelErrorMetadata(error_code="")

    def test_empty_string_error_category_allowed(self) -> None:
        """Test that empty string error_category is allowed (no validation)."""
        metadata = ModelErrorMetadata(error_category="")
        assert metadata.error_category == ""

    def test_whitespace_correlation_id_allowed(self) -> None:
        """Test that whitespace correlation_id is allowed."""
        metadata = ModelErrorMetadata(correlation_id="   ")
        assert metadata.correlation_id == "   "

    def test_large_retry_count(self) -> None:
        """Test that large retry_count values are accepted."""
        metadata = ModelErrorMetadata(retry_count=999999)
        assert metadata.retry_count == 999999

    def test_model_can_be_hashed(self) -> None:
        """Test that ModelErrorMetadata can be hashed (for use in sets/dicts)."""
        metadata = ModelErrorMetadata(
            error_code="AUTH_001",
            error_category="auth",
            retry_count=1,
        )
        # Should not raise exception
        hash(metadata)

    def test_model_supports_model_dump(self) -> None:
        """Test that model supports model_dump serialization."""
        metadata = ModelErrorMetadata(
            error_code="AUTH_001",
            error_category="auth",
            correlation_id="req_123",
            retry_count=1,
            is_retryable=True,
        )
        data = metadata.model_dump()
        assert isinstance(data, dict)
        assert data["error_code"] == "AUTH_001"
        assert data["error_category"] == "auth"
        assert data["correlation_id"] == "req_123"
        assert data["retry_count"] == 1
        assert data["is_retryable"] is True

    def test_model_supports_model_dump_json(self) -> None:
        """Test that model supports model_dump_json serialization."""
        metadata = ModelErrorMetadata(
            error_code="SYSTEM_001",
            error_category="system",
        )
        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)
        assert "SYSTEM_001" in json_str
        assert "system" in json_str

    def test_model_supports_equality(self) -> None:
        """Test that models with same values are equal."""
        metadata1 = ModelErrorMetadata(
            error_code="AUTH_001",
            error_category="auth",
            retry_count=1,
        )
        metadata2 = ModelErrorMetadata(
            error_code="AUTH_001",
            error_category="auth",
            retry_count=1,
        )
        assert metadata1 == metadata2

    def test_model_supports_copy(self) -> None:
        """Test that models can be copied with model_copy."""
        metadata = ModelErrorMetadata(
            error_code="AUTH_001",
            retry_count=1,
        )
        metadata_copy = metadata.model_copy()
        assert metadata == metadata_copy
        assert metadata is not metadata_copy

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update changes specific fields."""
        metadata = ModelErrorMetadata(
            error_code="AUTH_001",
            retry_count=1,
            is_retryable=True,
        )
        updated = metadata.model_copy(update={"retry_count": 2})
        assert updated.error_code == "AUTH_001"
        assert updated.retry_count == 2
        assert updated.is_retryable is True

    def test_error_code_with_multiple_underscores(self) -> None:
        """Test error code with multiple underscores in category."""
        metadata = ModelErrorMetadata(error_code="RATE_LIMIT_001")
        assert metadata.error_code == "RATE_LIMIT_001"

    def test_error_code_single_char_category(self) -> None:
        """Test error code with single character category."""
        metadata = ModelErrorMetadata(error_code="A_1")
        assert metadata.error_code == "A_1"

    def test_error_code_with_numbers_in_category(self) -> None:
        """Test error code with numbers in category part."""
        metadata = ModelErrorMetadata(error_code="AUTH2_001")
        assert metadata.error_code == "AUTH2_001"
