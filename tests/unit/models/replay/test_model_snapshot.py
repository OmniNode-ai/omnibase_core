"""Tests for ModelInputSnapshot and ModelOutputSnapshot models.

Tests the snapshot models used to capture execution input/output data
with truncation support and size tracking.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import ModelInputSnapshot, ModelOutputSnapshot

# ==============================================================================
# ModelInputSnapshot Tests
# ==============================================================================


@pytest.mark.unit
class TestModelInputSnapshotCreation:
    """Test ModelInputSnapshot creation and initialization."""

    def test_creation_with_valid_non_truncated_data_succeeds(self) -> None:
        """Model can be created with valid non-truncated data."""
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.raw == {"key": "value"}
        assert snapshot.truncated is False
        assert snapshot.original_size_bytes == 100
        assert snapshot.display_size_bytes == 100

    def test_creation_with_valid_truncated_data_succeeds(self) -> None:
        """Model can be created with valid truncated data."""
        snapshot = ModelInputSnapshot(
            raw={"key": "truncated_value"},
            truncated=True,
            original_size_bytes=1000,
            display_size_bytes=500,
        )
        assert snapshot.raw == {"key": "truncated_value"}
        assert snapshot.truncated is True
        assert snapshot.original_size_bytes == 1000
        assert snapshot.display_size_bytes == 500

    def test_creation_defaults_truncated_to_false(self) -> None:
        """Model defaults truncated to False when not provided."""
        snapshot = ModelInputSnapshot(
            raw={},
            original_size_bytes=50,
            display_size_bytes=50,
        )
        assert snapshot.truncated is False

    def test_creation_with_empty_raw_dict_succeeds(self) -> None:
        """Model can be created with empty raw dictionary."""
        snapshot = ModelInputSnapshot(
            raw={},
            truncated=False,
            original_size_bytes=2,
            display_size_bytes=2,
        )
        assert snapshot.raw == {}


@pytest.mark.unit
class TestModelInputSnapshotSizeValidation:
    """Test non-negative size validation for ModelInputSnapshot."""

    def test_validation_fails_when_original_size_bytes_is_negative(self) -> None:
        """Validation fails if original_size_bytes is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-1,
                display_size_bytes=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_display_size_bytes_is_negative(self) -> None:
        """Validation fails if display_size_bytes is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=-1,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("display_size_bytes",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_both_size_bytes_are_negative(self) -> None:
        """Validation fails if both size fields are negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-10,
                display_size_bytes=-5,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)
        assert any(e["loc"] == ("display_size_bytes",) for e in errors)

    def test_validation_fails_when_original_size_bytes_is_large_negative(self) -> None:
        """Validation fails if original_size_bytes is a large negative number."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-999999,
                display_size_bytes=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)

    def test_validation_succeeds_when_size_bytes_are_zero(self) -> None:
        """Validation succeeds when both size fields are zero (edge case)."""
        snapshot = ModelInputSnapshot(
            raw={},
            truncated=False,
            original_size_bytes=0,
            display_size_bytes=0,
        )
        assert snapshot.original_size_bytes == 0
        assert snapshot.display_size_bytes == 0

    def test_validation_succeeds_when_size_bytes_are_positive(self) -> None:
        """Validation succeeds when both size fields are positive."""
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.original_size_bytes == 100
        assert snapshot.display_size_bytes == 100


@pytest.mark.unit
class TestModelInputSnapshotTruncationValidation:
    """Test truncation constraint validation for ModelInputSnapshot."""

    def test_validation_fails_when_display_exceeds_original(self) -> None:
        """Validation fails if display_size_bytes > original_size_bytes."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=150,
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg
        assert "original_size_bytes (100)" in error_msg

    def test_validation_fails_when_truncated_but_sizes_equal(self) -> None:
        """Validation fails if truncated=True but sizes are equal."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=100,
            )
        error_msg = str(exc_info.value)
        assert "When truncated=True" in error_msg
        assert "must be less than" in error_msg

    def test_validation_fails_when_truncated_but_display_exceeds_original(self) -> None:
        """Validation fails if truncated=True but display > original."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=150,
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg

    def test_validation_fails_when_not_truncated_but_sizes_differ(self) -> None:
        """Validation fails if truncated=False but sizes differ."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=80,
            )
        error_msg = str(exc_info.value)
        assert "When truncated=False" in error_msg
        assert "must equal original_size_bytes" in error_msg

    def test_validation_succeeds_with_edge_case_truncation(self) -> None:
        """Validation succeeds with minimal truncation (1 byte less)."""
        snapshot = ModelInputSnapshot(
            raw={"key": "val"},
            truncated=True,
            original_size_bytes=100,
            display_size_bytes=99,
        )
        assert snapshot.truncated is True
        assert snapshot.display_size_bytes == 99

    def test_validation_succeeds_with_zero_sizes(self) -> None:
        """Validation succeeds with zero byte sizes (empty content)."""
        snapshot = ModelInputSnapshot(
            raw={},
            truncated=False,
            original_size_bytes=0,
            display_size_bytes=0,
        )
        assert snapshot.original_size_bytes == 0
        assert snapshot.display_size_bytes == 0


@pytest.mark.unit
class TestModelInputSnapshotImmutability:
    """Test immutability of ModelInputSnapshot model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        with pytest.raises(ValidationError):
            snapshot.truncated = True  # type: ignore[misc]
        with pytest.raises(ValidationError):
            snapshot.original_size_bytes = 200  # type: ignore[misc]

    def test_equality_with_identical_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        snapshot1 = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        snapshot2 = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot1 == snapshot2


@pytest.mark.unit
class TestModelInputSnapshotSerialization:
    """Test serialization of ModelInputSnapshot model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict."""
        snapshot = ModelInputSnapshot(
            raw={"key": "value"},
            truncated=True,
            original_size_bytes=1000,
            display_size_bytes=500,
        )
        data = snapshot.model_dump()
        assert isinstance(data, dict)
        assert data["raw"] == {"key": "value"}
        assert data["truncated"] is True
        assert data["original_size_bytes"] == 1000
        assert data["display_size_bytes"] == 500

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data: dict[str, Any] = {
            "raw": {"test": "data"},
            "truncated": True,
            "original_size_bytes": 200,
            "display_size_bytes": 100,
        }
        snapshot = ModelInputSnapshot(**data)
        assert snapshot.raw == {"test": "data"}
        assert snapshot.truncated is True


# ==============================================================================
# ModelOutputSnapshot Tests
# ==============================================================================


@pytest.mark.unit
class TestModelOutputSnapshotCreation:
    """Test ModelOutputSnapshot creation and initialization."""

    def test_creation_with_valid_non_truncated_data_succeeds(self) -> None:
        """Model can be created with valid non-truncated data."""
        snapshot = ModelOutputSnapshot(
            raw={"result": "success"},
            truncated=False,
            original_size_bytes=150,
            display_size_bytes=150,
            output_hash="sha256:abc123",
        )
        assert snapshot.raw == {"result": "success"}
        assert snapshot.truncated is False
        assert snapshot.original_size_bytes == 150
        assert snapshot.display_size_bytes == 150
        assert snapshot.output_hash == "sha256:abc123"

    def test_creation_with_valid_truncated_data_succeeds(self) -> None:
        """Model can be created with valid truncated data."""
        snapshot = ModelOutputSnapshot(
            raw={"result": "truncated_output"},
            truncated=True,
            original_size_bytes=2000,
            display_size_bytes=800,
            output_hash="sha256:def789",
        )
        assert snapshot.raw == {"result": "truncated_output"}
        assert snapshot.truncated is True
        assert snapshot.original_size_bytes == 2000
        assert snapshot.display_size_bytes == 800

    def test_creation_defaults_truncated_to_false(self) -> None:
        """Model defaults truncated to False when not provided."""
        snapshot = ModelOutputSnapshot(
            raw={},
            original_size_bytes=50,
            display_size_bytes=50,
            output_hash="sha256:aaa111",
        )
        assert snapshot.truncated is False

    def test_creation_requires_output_hash(self) -> None:
        """Model requires output_hash field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(  # type: ignore[call-arg]
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)

    def test_creation_rejects_empty_output_hash(self) -> None:
        """Model rejects empty output_hash."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="",  # Empty string should be rejected
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("output_hash",) for e in errors)
        assert any("at least 1 character" in str(e["msg"]).lower() for e in errors)


@pytest.mark.unit
class TestModelOutputSnapshotSizeValidation:
    """Test non-negative size validation for ModelOutputSnapshot."""

    def test_validation_fails_when_original_size_bytes_is_negative(self) -> None:
        """Validation fails if original_size_bytes is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-1,
                display_size_bytes=100,
                output_hash="sha256:bbb222",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_display_size_bytes_is_negative(self) -> None:
        """Validation fails if display_size_bytes is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=-1,
                output_hash="sha256:bbb222",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("display_size_bytes",) for e in errors)
        assert any("greater than or equal to 0" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_both_size_bytes_are_negative(self) -> None:
        """Validation fails if both size fields are negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-10,
                display_size_bytes=-5,
                output_hash="sha256:bbb222",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)
        assert any(e["loc"] == ("display_size_bytes",) for e in errors)

    def test_validation_fails_when_original_size_bytes_is_large_negative(self) -> None:
        """Validation fails if original_size_bytes is a large negative number."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=-999999,
                display_size_bytes=100,
                output_hash="sha256:bbb222",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("original_size_bytes",) for e in errors)

    def test_validation_succeeds_when_size_bytes_are_zero(self) -> None:
        """Validation succeeds when both size fields are zero (edge case)."""
        snapshot = ModelOutputSnapshot(
            raw={},
            truncated=False,
            original_size_bytes=0,
            display_size_bytes=0,
            output_hash="sha256:aaa111",
        )
        assert snapshot.original_size_bytes == 0
        assert snapshot.display_size_bytes == 0

    def test_validation_succeeds_when_size_bytes_are_positive(self) -> None:
        """Validation succeeds when both size fields are positive."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:bbb222",
        )
        assert snapshot.original_size_bytes == 100
        assert snapshot.display_size_bytes == 100


@pytest.mark.unit
class TestModelOutputSnapshotTruncationValidation:
    """Test truncation constraint validation for ModelOutputSnapshot."""

    def test_validation_fails_when_display_exceeds_original(self) -> None:
        """Validation fails if display_size_bytes > original_size_bytes."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=150,
                output_hash="sha256:bbb222",
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg
        assert "original_size_bytes (100)" in error_msg

    def test_validation_fails_when_truncated_but_sizes_equal(self) -> None:
        """Validation fails if truncated=True but sizes are equal."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=100,
                output_hash="sha256:bbb222",
            )
        error_msg = str(exc_info.value)
        assert "When truncated=True" in error_msg
        assert "must be less than" in error_msg

    def test_validation_fails_when_truncated_but_display_exceeds_original(self) -> None:
        """Validation fails if truncated=True but display > original."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=True,
                original_size_bytes=100,
                display_size_bytes=150,
                output_hash="sha256:bbb222",
            )
        error_msg = str(exc_info.value)
        assert "display_size_bytes (150) cannot exceed" in error_msg

    def test_validation_fails_when_not_truncated_but_sizes_differ(self) -> None:
        """Validation fails if truncated=False but sizes differ."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOutputSnapshot(
                raw={"key": "value"},
                truncated=False,
                original_size_bytes=100,
                display_size_bytes=80,
                output_hash="sha256:bbb222",
            )
        error_msg = str(exc_info.value)
        assert "When truncated=False" in error_msg
        assert "must equal original_size_bytes" in error_msg

    def test_validation_succeeds_with_edge_case_truncation(self) -> None:
        """Validation succeeds with minimal truncation (1 byte less)."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "val"},
            truncated=True,
            original_size_bytes=100,
            display_size_bytes=99,
            output_hash="sha256:ccc333",
        )
        assert snapshot.truncated is True
        assert snapshot.display_size_bytes == 99

    def test_validation_succeeds_with_zero_sizes(self) -> None:
        """Validation succeeds with zero byte sizes (empty content)."""
        snapshot = ModelOutputSnapshot(
            raw={},
            truncated=False,
            original_size_bytes=0,
            display_size_bytes=0,
            output_hash="sha256:aaa111",
        )
        assert snapshot.original_size_bytes == 0
        assert snapshot.display_size_bytes == 0


@pytest.mark.unit
class TestModelOutputSnapshotImmutability:
    """Test immutability of ModelOutputSnapshot model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        snapshot = ModelOutputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:bbb222",
        )
        with pytest.raises(ValidationError):
            snapshot.truncated = True  # type: ignore[misc]
        with pytest.raises(ValidationError):
            snapshot.output_hash = "sha256:ddd444"  # type: ignore[misc]

    def test_equality_with_identical_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        snapshot1 = ModelOutputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:bbb222",
        )
        snapshot2 = ModelOutputSnapshot(
            raw={"key": "value"},
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
            output_hash="sha256:bbb222",
        )
        assert snapshot1 == snapshot2


@pytest.mark.unit
class TestModelOutputSnapshotSerialization:
    """Test serialization of ModelOutputSnapshot model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict."""
        snapshot = ModelOutputSnapshot(
            raw={"result": "data"},
            truncated=True,
            original_size_bytes=1000,
            display_size_bytes=500,
            output_hash="sha256:eee555",
        )
        data = snapshot.model_dump()
        assert isinstance(data, dict)
        assert data["raw"] == {"result": "data"}
        assert data["truncated"] is True
        assert data["original_size_bytes"] == 1000
        assert data["display_size_bytes"] == 500
        assert data["output_hash"] == "sha256:eee555"

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data: dict[str, Any] = {
            "raw": {"test": "output"},
            "truncated": True,
            "original_size_bytes": 300,
            "display_size_bytes": 150,
            "output_hash": "sha256:fff666",
        }
        snapshot = ModelOutputSnapshot(**data)
        assert snapshot.raw == {"test": "output"}
        assert snapshot.truncated is True
        assert snapshot.output_hash == "sha256:fff666"


@pytest.mark.unit
class TestSnapshotEdgeCases:
    """Test edge cases for both snapshot models."""

    def test_input_snapshot_with_large_truncation_ratio_succeeds(self) -> None:
        """Input snapshot with large truncation ratio succeeds."""
        snapshot = ModelInputSnapshot(
            raw={"summary": "..."},
            truncated=True,
            original_size_bytes=1000000,
            display_size_bytes=1000,
        )
        assert snapshot.original_size_bytes == 1000000
        assert snapshot.display_size_bytes == 1000

    def test_output_snapshot_with_large_truncation_ratio_succeeds(self) -> None:
        """Output snapshot with large truncation ratio succeeds."""
        snapshot = ModelOutputSnapshot(
            raw={"summary": "..."},
            truncated=True,
            original_size_bytes=5000000,
            display_size_bytes=5000,
            output_hash="sha256:111777",
        )
        assert snapshot.original_size_bytes == 5000000
        assert snapshot.display_size_bytes == 5000

    def test_input_snapshot_with_nested_raw_data_succeeds(self) -> None:
        """Input snapshot with deeply nested raw data succeeds."""
        nested_data: dict[str, Any] = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": [1, 2, 3],
                    }
                }
            }
        }
        snapshot = ModelInputSnapshot(
            raw=nested_data,
            truncated=False,
            original_size_bytes=100,
            display_size_bytes=100,
        )
        assert snapshot.raw["level1"]["level2"]["level3"]["data"] == [1, 2, 3]

    def test_output_snapshot_with_complex_raw_data_succeeds(self) -> None:
        """Output snapshot with complex raw data types succeeds."""
        complex_data: dict[str, Any] = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, "two", 3.0],
            "nested": {"key": "value"},
        }
        snapshot = ModelOutputSnapshot(
            raw=complex_data,
            truncated=False,
            original_size_bytes=200,
            display_size_bytes=200,
            output_hash="sha256:222888",
        )
        assert snapshot.raw["string"] == "text"
        assert snapshot.raw["null"] is None
        assert snapshot.raw["list"] == [1, "two", 3.0]
