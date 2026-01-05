# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProjectionResult.

Tests cover:
1. Valid result creation with required fields
2. Default values (skipped=False, rows_affected=0, error=None)
3. Required field validation (success is required)
4. Skipped result behavior
5. Error result behavior
6. Frozen/immutable behavior
7. Extra fields rejected
8. Serialization roundtrip
9. Custom __repr__ output
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectionResultCreation:
    """Tests for ModelProjectionResult creation and validation."""

    def test_valid_result_success_only(self) -> None:
        """Valid result with only success=True."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True)

        assert result.success is True
        assert result.skipped is False  # default
        assert result.rows_affected == 0  # default
        assert result.error is None  # default

    def test_valid_result_success_false(self) -> None:
        """Valid result with success=False."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=False)

        assert result.success is False
        assert result.skipped is False
        assert result.rows_affected == 0
        assert result.error is None

    def test_valid_result_with_all_fields(self) -> None:
        """Valid result with all fields specified."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(
            success=True,
            skipped=False,
            rows_affected=5,
            error=None,
        )

        assert result.success is True
        assert result.skipped is False
        assert result.rows_affected == 5
        assert result.error is None

    def test_default_values(self) -> None:
        """Verify default values are applied correctly."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True)

        # Check defaults
        assert result.skipped is False
        assert result.rows_affected == 0
        assert result.error is None

    def test_success_is_required(self) -> None:
        """Success field is required."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult()  # type: ignore[call-arg]

        assert "success" in str(exc_info.value)

    def test_skipped_result(self) -> None:
        """Create result with skipped=True."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, skipped=True)

        assert result.success is True
        assert result.skipped is True
        assert result.rows_affected == 0

    def test_result_with_error(self) -> None:
        """Create result with error message."""
        from omnibase_core.models.projectors import ModelProjectionResult

        error_msg = "Database connection failed"
        result = ModelProjectionResult(success=False, error=error_msg)

        assert result.success is False
        assert result.error == error_msg

    def test_result_success_with_rows_affected(self) -> None:
        """Create successful result with rows_affected > 0."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=3)

        assert result.success is True
        assert result.rows_affected == 3
        assert result.skipped is False
        assert result.error is None


@pytest.mark.unit
class TestModelProjectionResultImmutability:
    """Tests for frozen/immutable behavior."""

    def test_result_is_frozen(self) -> None:
        """Result should be immutable after creation."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=1)

        with pytest.raises(ValidationError):
            result.success = False  # type: ignore[misc]

    def test_result_is_hashable(self) -> None:
        """Frozen result should be hashable."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=1)

        # Should not raise
        hash_value = hash(result)
        assert isinstance(hash_value, int)

    def test_result_hash_consistency(self) -> None:
        """Same values should produce same hash."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True, rows_affected=5)
        result2 = ModelProjectionResult(success=True, rows_affected=5)

        assert hash(result1) == hash(result2)

    def test_result_can_be_set_member(self) -> None:
        """Frozen result should work in sets."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True, rows_affected=1)
        result2 = ModelProjectionResult(success=True, rows_affected=2)
        result3 = ModelProjectionResult(success=True, rows_affected=1)  # duplicate

        result_set = {result1, result2, result3}

        # result1 and result3 are equal, so set should have 2 elements
        assert len(result_set) == 2


@pytest.mark.unit
class TestModelProjectionResultExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult(
                success=True,
                unknown_field="value",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str


@pytest.mark.unit
class TestModelProjectionResultSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectionResult

        original = ModelProjectionResult(
            success=True,
            skipped=False,
            rows_affected=10,
            error=None,
        )
        data = original.model_dump()
        restored = ModelProjectionResult.model_validate(data)

        assert restored == original

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectionResult

        original = ModelProjectionResult(
            success=False,
            skipped=False,
            rows_affected=0,
            error="Constraint violation",
        )
        json_str = original.model_dump_json()
        restored = ModelProjectionResult.model_validate_json(json_str)

        assert restored == original

    def test_to_dict_with_defaults(self) -> None:
        """Minimal model serializes with all defaults."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True)
        data = result.model_dump()

        assert data["success"] is True
        assert data["skipped"] is False
        assert data["rows_affected"] == 0
        assert data["error"] is None

    def test_to_json_roundtrip_skipped(self) -> None:
        """JSON roundtrip for skipped result."""
        from omnibase_core.models.projectors import ModelProjectionResult

        original = ModelProjectionResult(success=True, skipped=True)
        json_str = original.model_dump_json()
        restored = ModelProjectionResult.model_validate_json(json_str)

        assert restored == original
        assert restored.skipped is True


@pytest.mark.unit
class TestModelProjectionResultRepr:
    """Tests for __repr__ method."""

    def test_repr_success(self) -> None:
        """Check repr contains class name and key info for success."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=1)
        repr_str = repr(result)

        assert "ModelProjectionResult" in repr_str
        assert "success=True" in repr_str
        assert "skipped=False" in repr_str
        assert "rows_affected=1" in repr_str
        # Error should not be in repr when None
        assert "error=" not in repr_str

    def test_repr_with_error(self) -> None:
        """Check repr shows error when present."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=False, error="DB error")
        repr_str = repr(result)

        assert "ModelProjectionResult" in repr_str
        assert "success=False" in repr_str
        assert "error='DB error'" in repr_str

    def test_repr_skipped(self) -> None:
        """Check repr shows skipped status."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, skipped=True)
        repr_str = repr(result)

        assert "ModelProjectionResult" in repr_str
        assert "skipped=True" in repr_str

    def test_repr_default_values(self) -> None:
        """Check repr with default values."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True)
        repr_str = repr(result)

        assert "ModelProjectionResult" in repr_str
        assert "success=True" in repr_str
        assert "skipped=False" in repr_str
        assert "rows_affected=0" in repr_str


@pytest.mark.unit
class TestModelProjectionResultEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_large_rows_affected(self) -> None:
        """Test with large rows_affected value."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=1_000_000)

        assert result.rows_affected == 1_000_000

    def test_zero_rows_affected_explicit(self) -> None:
        """Test with explicitly set zero rows_affected."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=True, rows_affected=0)

        assert result.rows_affected == 0

    def test_empty_error_string(self) -> None:
        """Test with empty error string (still valid)."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result = ModelProjectionResult(success=False, error="")

        assert result.error == ""
        assert result.success is False

    def test_long_error_message(self) -> None:
        """Test with long error message."""
        from omnibase_core.models.projectors import ModelProjectionResult

        long_error = "Error: " + "x" * 1000
        result = ModelProjectionResult(success=False, error=long_error)

        assert result.error == long_error
        assert len(result.error) == 1007

    def test_success_with_error_allowed(self) -> None:
        """Test success=True with error (semantically odd but valid)."""
        from omnibase_core.models.projectors import ModelProjectionResult

        # The model allows this combination even if semantically unusual
        result = ModelProjectionResult(success=True, error="Warning message")

        assert result.success is True
        assert result.error == "Warning message"

    def test_skipped_with_rows_affected(self) -> None:
        """Test skipped=True with rows_affected (semantically odd but valid)."""
        from omnibase_core.models.projectors import ModelProjectionResult

        # The model allows this combination
        result = ModelProjectionResult(success=True, skipped=True, rows_affected=5)

        assert result.skipped is True
        assert result.rows_affected == 5


@pytest.mark.unit
class TestModelProjectionResultTypeValidation:
    """Tests for type validation."""

    def test_success_must_be_bool(self) -> None:
        """Success must be boolean type."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult(success="invalid")  # type: ignore[arg-type]

        assert "success" in str(exc_info.value)

    def test_skipped_must_be_bool(self) -> None:
        """Skipped must be boolean type."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult(success=True, skipped="invalid")  # type: ignore[arg-type]

        assert "skipped" in str(exc_info.value)

    def test_rows_affected_must_be_int(self) -> None:
        """rows_affected must be integer type."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult(
                success=True,
                rows_affected="five",  # type: ignore[arg-type]
            )

        assert "rows_affected" in str(exc_info.value)

    def test_error_must_be_string_or_none(self) -> None:
        """Error must be string or None."""
        from omnibase_core.models.projectors import ModelProjectionResult

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionResult(success=False, error=123)  # type: ignore[arg-type]

        assert "error" in str(exc_info.value)


@pytest.mark.unit
class TestModelProjectionResultEquality:
    """Tests for equality comparisons."""

    def test_equal_results(self) -> None:
        """Two results with same values should be equal."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True, rows_affected=5)
        result2 = ModelProjectionResult(success=True, rows_affected=5)

        assert result1 == result2

    def test_unequal_results_different_success(self) -> None:
        """Results with different success values should not be equal."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True)
        result2 = ModelProjectionResult(success=False)

        assert result1 != result2

    def test_unequal_results_different_rows(self) -> None:
        """Results with different rows_affected should not be equal."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True, rows_affected=1)
        result2 = ModelProjectionResult(success=True, rows_affected=2)

        assert result1 != result2

    def test_unequal_results_different_error(self) -> None:
        """Results with different errors should not be equal."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=False, error="Error A")
        result2 = ModelProjectionResult(success=False, error="Error B")

        assert result1 != result2

    def test_unequal_results_different_skipped(self) -> None:
        """Results with different skipped values should not be equal."""
        from omnibase_core.models.projectors import ModelProjectionResult

        result1 = ModelProjectionResult(success=True, skipped=False)
        result2 = ModelProjectionResult(success=True, skipped=True)

        assert result1 != result2
