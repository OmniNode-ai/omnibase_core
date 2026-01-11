"""Tests for MixinTruncationValidation mixin.

Tests the truncation validation logic that is shared between
ModelInputSnapshot and ModelOutputSnapshot.
"""

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.models.replay import MixinTruncationValidation


class ModelTestSnapshot(MixinTruncationValidation, BaseModel):
    """Test model for verifying mixin behavior."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    truncated: bool = False
    original_size_bytes: int
    display_size_bytes: int


# ==============================================================================
# MixinTruncationValidation Tests
# ==============================================================================


@pytest.mark.unit
class TestMixinTruncationValidationNonTruncated:
    """Test validation for non-truncated snapshots."""

    def test_non_truncated_with_equal_sizes_succeeds(self) -> None:
        """Non-truncated snapshot with equal sizes is valid."""
        snapshot = ModelTestSnapshot(
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.truncated is False
        assert snapshot.original_size_bytes == 100
        assert snapshot.display_size_bytes == 100

    def test_non_truncated_with_zero_sizes_succeeds(self) -> None:
        """Non-truncated snapshot with zero sizes is valid."""
        snapshot = ModelTestSnapshot(
            truncated=False,
            original_size_bytes=0,
            display_size_bytes=0,
        )
        assert snapshot.original_size_bytes == 0
        assert snapshot.display_size_bytes == 0

    def test_non_truncated_with_unequal_sizes_fails(self) -> None:
        """Non-truncated snapshot with unequal sizes raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTestSnapshot(
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=80,
            )
        error_msg = str(exc_info.value)
        assert "When truncated=False" in error_msg
        assert "must equal original_size_bytes" in error_msg


@pytest.mark.unit
class TestMixinTruncationValidationTruncated:
    """Test validation for truncated snapshots."""

    def test_truncated_with_smaller_display_size_succeeds(self) -> None:
        """Truncated snapshot with smaller display size is valid."""
        snapshot = ModelTestSnapshot(
            truncated=True,
            original_size_bytes=1000,
            display_size_bytes=500,
        )
        assert snapshot.truncated is True
        assert snapshot.original_size_bytes == 1000
        assert snapshot.display_size_bytes == 500

    def test_truncated_with_minimal_reduction_succeeds(self) -> None:
        """Truncated snapshot with 1-byte reduction is valid."""
        snapshot = ModelTestSnapshot(
            truncated=True,
            original_size_bytes=100,
            display_size_bytes=99,
        )
        assert snapshot.truncated is True
        assert snapshot.display_size_bytes == 99

    def test_truncated_with_large_ratio_succeeds(self) -> None:
        """Truncated snapshot with large truncation ratio is valid."""
        snapshot = ModelTestSnapshot(
            truncated=True,
            original_size_bytes=1000000,
            display_size_bytes=1000,
        )
        assert snapshot.original_size_bytes == 1000000
        assert snapshot.display_size_bytes == 1000

    def test_truncated_with_equal_sizes_fails(self) -> None:
        """Truncated snapshot with equal sizes raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTestSnapshot(
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=100,
            )
        error_msg = str(exc_info.value)
        assert "When truncated=True" in error_msg
        assert "must be less than" in error_msg


@pytest.mark.unit
class TestMixinTruncationValidationDisplayExceedsOriginal:
    """Test validation when display size exceeds original size."""

    def test_non_truncated_display_exceeds_original_fails(self) -> None:
        """Non-truncated with display > original raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTestSnapshot(
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=150,
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg
        assert "original_size_bytes (100)" in error_msg

    def test_truncated_display_exceeds_original_fails(self) -> None:
        """Truncated with display > original raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTestSnapshot(
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=150,
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg
        assert "original_size_bytes (100)" in error_msg


@pytest.mark.unit
class TestMixinTruncationValidationDefaultValue:
    """Test default value for truncated field."""

    def test_truncated_defaults_to_false(self) -> None:
        """Truncated field defaults to False when not provided."""
        snapshot = ModelTestSnapshot(
            original_size_bytes=50,
            display_size_bytes=50,
        )
        assert snapshot.truncated is False


@pytest.mark.unit
class TestMixinTruncationValidationIntegration:
    """Test mixin integration with real snapshot models."""

    def test_input_snapshot_uses_mixin_validation(self) -> None:
        """Verify ModelInputSnapshot inherits mixin validation."""
        from omnibase_core.models.replay import ModelInputSnapshot

        # Valid non-truncated
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.truncated is False

        # Invalid: display exceeds original
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=150,
            )
        assert "display_size_bytes (150) cannot exceed" in str(exc_info.value)

    def test_output_snapshot_uses_mixin_validation(self) -> None:
        """Verify ModelOutputSnapshot inherits mixin validation."""
        from omnibase_core.models.replay import ModelOutputSnapshot

        # Valid truncated
        snapshot = ModelOutputSnapshot(
            raw={"result": "data"},
            truncated=True,
            original_size_bytes=1000,
            display_size_bytes=500,
            output_hash="sha256:abc123",
        )
        assert snapshot.truncated is True

        # Invalid: truncated but sizes equal
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"result": "data"},
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha256:abc123",
            )
        assert "When truncated=True" in str(exc_info.value)

    def test_both_models_have_consistent_validation(self) -> None:
        """Both snapshot models have identical validation behavior."""
        from omnibase_core.models.replay import ModelInputSnapshot, ModelOutputSnapshot

        # Both should reject display > original with same error message
        with pytest.raises(ValidationError) as input_exc:
            ModelInputSnapshot(
                raw={},
                truncated=False,
                original_size_bytes=50,
                display_size_bytes=100,
            )

        with pytest.raises(ValidationError) as output_exc:
            ModelOutputSnapshot(
                raw={},
                truncated=False,
                original_size_bytes=50,
                display_size_bytes=100,
                output_hash="sha256:test",
            )

        # Error messages should contain the same validation text
        assert "display_size_bytes (100) cannot exceed" in str(input_exc.value)
        assert "display_size_bytes (100) cannot exceed" in str(output_exc.value)
