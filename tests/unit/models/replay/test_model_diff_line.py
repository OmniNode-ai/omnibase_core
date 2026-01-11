"""Tests for ModelDiffLine model.

Tests the diff line model used to represent a single line in side-by-side
comparison output between baseline and replay executions.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay.model_diff_line import ModelDiffLine


@pytest.mark.unit
class TestModelDiffLineCreation:
    """Test ModelDiffLine creation and initialization."""

    def test_creation_with_all_fields_succeeds(self) -> None:
        """Model can be created with all required fields."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="original text",
            replay_content="updated text",
            change_type="modified",
        )
        assert line.line_number == 1
        assert line.baseline_content == "original text"
        assert line.replay_content == "updated text"
        assert line.change_type == "modified"

    def test_creation_with_unchanged_line_succeeds(self) -> None:
        """Model can be created for an unchanged line."""
        line = ModelDiffLine(
            line_number=5,
            baseline_content="same content",
            replay_content="same content",
            change_type="unchanged",
        )
        assert line.change_type == "unchanged"
        assert line.baseline_content == line.replay_content

    def test_creation_with_added_line_succeeds(self) -> None:
        """Model can be created for an added line (no baseline)."""
        line = ModelDiffLine(
            line_number=10,
            baseline_content=None,
            replay_content="new line",
            change_type="added",
        )
        assert line.baseline_content is None
        assert line.replay_content == "new line"
        assert line.change_type == "added"

    def test_creation_with_removed_line_succeeds(self) -> None:
        """Model can be created for a removed line (no replay)."""
        line = ModelDiffLine(
            line_number=3,
            baseline_content="removed line",
            replay_content=None,
            change_type="removed",
        )
        assert line.baseline_content == "removed line"
        assert line.replay_content is None
        assert line.change_type == "removed"


@pytest.mark.unit
class TestModelDiffLineValidation:
    """Test ModelDiffLine field validation."""

    def test_validation_fails_when_line_number_is_zero(self) -> None:
        """Validation fails if line_number is zero (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=0,
                baseline_content="content",
                replay_content="content",
                change_type="unchanged",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("line_number",) for e in errors)
        assert any("greater than or equal to 1" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_line_number_is_negative(self) -> None:
        """Validation fails if line_number is negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=-1,
                baseline_content="content",
                replay_content="content",
                change_type="unchanged",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("line_number",) for e in errors)
        assert any("greater than or equal to 1" in str(e["msg"]) for e in errors)

    def test_validation_fails_when_line_number_is_large_negative(self) -> None:
        """Validation fails if line_number is a large negative number."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=-999999,
                baseline_content="content",
                replay_content="content",
                change_type="unchanged",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("line_number",) for e in errors)

    def test_validation_succeeds_when_line_number_is_one(self) -> None:
        """Validation succeeds when line_number is exactly 1 (minimum valid)."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="first line",
            replay_content="first line",
            change_type="unchanged",
        )
        assert line.line_number == 1

    def test_validation_succeeds_when_line_number_is_large(self) -> None:
        """Validation succeeds for large positive line numbers."""
        line = ModelDiffLine(
            line_number=999999,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        assert line.line_number == 999999

    def test_validation_fails_when_invalid_change_type(self) -> None:
        """Validation fails if change_type is not a valid literal."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="content",
                replay_content="content",
                change_type="invalid_type",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("change_type",) for e in errors)

    def test_validation_fails_when_line_number_missing(self) -> None:
        """Validation fails if line_number is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                baseline_content="content",
                replay_content="content",
                change_type="unchanged",
            )  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("line_number",) for e in errors)


@pytest.mark.unit
class TestModelDiffLineImmutability:
    """Test immutability of ModelDiffLine model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="original",
            replay_content="updated",
            change_type="modified",
        )
        with pytest.raises(ValidationError):
            line.line_number = 2  # type: ignore[misc]
        with pytest.raises(ValidationError):
            line.baseline_content = "modified"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            line.change_type = "added"  # type: ignore[misc]

    def test_hashing_frozen_model_succeeds(self) -> None:
        """Hashing frozen model succeeds for use in sets and dict keys."""
        line1 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        line2 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        # Can be added to set (requires hashability)
        line_set = {line1, line2}
        assert len(line_set) == 1  # Duplicates are removed


@pytest.mark.unit
class TestModelDiffLineSerialization:
    """Test serialization of ModelDiffLine model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict."""
        line = ModelDiffLine(
            line_number=5,
            baseline_content="original",
            replay_content="updated",
            change_type="modified",
        )
        data = line.model_dump()
        assert isinstance(data, dict)
        assert data["line_number"] == 5
        assert data["baseline_content"] == "original"
        assert data["replay_content"] == "updated"
        assert data["change_type"] == "modified"

    def test_serialization_to_json_succeeds(self) -> None:
        """Serialization to JSON returns valid string representation."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        json_str = line.model_dump_json()
        assert isinstance(json_str, str)
        assert '"line_number":1' in json_str
        assert '"change_type":"unchanged"' in json_str

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data: dict[str, Any] = {
            "line_number": 10,
            "baseline_content": "base",
            "replay_content": "replay",
            "change_type": "modified",
        }
        line = ModelDiffLine(**data)
        assert line.line_number == 10
        assert line.baseline_content == "base"
        assert line.replay_content == "replay"


@pytest.mark.unit
class TestModelDiffLineEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        line1 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        line2 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        assert line1 == line2

    def test_equality_when_different_line_number_returns_false(self) -> None:
        """Two instances with different line_number are not equal."""
        line1 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        line2 = ModelDiffLine(
            line_number=2,
            baseline_content="content",
            replay_content="content",
            change_type="unchanged",
        )
        assert line1 != line2

    def test_equality_when_different_change_type_returns_false(self) -> None:
        """Two instances with different change_type are not equal."""
        # Note: With semantic validation, we must use valid combinations
        # for each change_type. Here we compare "added" vs "removed".
        line1 = ModelDiffLine(
            line_number=1,
            baseline_content=None,
            replay_content="content",
            change_type="added",
        )
        line2 = ModelDiffLine(
            line_number=1,
            baseline_content="content",
            replay_content=None,
            change_type="removed",
        )
        assert line1 != line2


@pytest.mark.unit
class TestModelDiffLineEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_creation_with_empty_string_content_succeeds(self) -> None:
        """Creation with empty string content succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="",
            replay_content="",
            change_type="unchanged",
        )
        assert line.baseline_content == ""
        assert line.replay_content == ""

    def test_creation_with_multiline_content_succeeds(self) -> None:
        """Creation with content containing newlines succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="line1\nline2",
            replay_content="line1\nline2\nline3",
            change_type="modified",
        )
        assert "\n" in line.baseline_content  # type: ignore[operator]
        assert "\n" in line.replay_content  # type: ignore[operator]

    def test_creation_with_unicode_content_succeeds(self) -> None:
        """Creation with unicode characters succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="Hello world",
            replay_content="Bonjour monde",
            change_type="modified",
        )
        assert line.baseline_content == "Hello world"
        assert line.replay_content == "Bonjour monde"

    def test_creation_with_both_contents_none_succeeds(self) -> None:
        """Creation with both contents as None succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content=None,
            replay_content=None,
            change_type="unchanged",
        )
        assert line.baseline_content is None
        assert line.replay_content is None


@pytest.mark.unit
class TestModelDiffLineChangeTypeValidation:
    """Test change_type semantic consistency validation.

    These tests verify that the model enforces correct relationships
    between change_type and content field values.
    """

    def test_added_with_baseline_content_raises_error(self) -> None:
        """change_type='added' with non-None baseline_content raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="should be None",
                replay_content="new content",
                change_type="added",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "baseline_content to be None" in str(errors[0]["msg"])

    def test_added_with_none_baseline_succeeds(self) -> None:
        """change_type='added' with None baseline_content succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content=None,
            replay_content="new content",
            change_type="added",
        )
        assert line.change_type == "added"
        assert line.baseline_content is None

    def test_removed_with_replay_content_raises_error(self) -> None:
        """change_type='removed' with non-None replay_content raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="old content",
                replay_content="should be None",
                change_type="removed",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "replay_content to be None" in str(errors[0]["msg"])

    def test_removed_with_none_replay_succeeds(self) -> None:
        """change_type='removed' with None replay_content succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="old content",
            replay_content=None,
            change_type="removed",
        )
        assert line.change_type == "removed"
        assert line.replay_content is None

    def test_unchanged_with_different_contents_raises_error(self) -> None:
        """change_type='unchanged' with different content values raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="content A",
                replay_content="content B",
                change_type="unchanged",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "to be equal" in str(errors[0]["msg"])

    def test_unchanged_with_equal_contents_succeeds(self) -> None:
        """change_type='unchanged' with equal content values succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="same content",
            replay_content="same content",
            change_type="unchanged",
        )
        assert line.change_type == "unchanged"
        assert line.baseline_content == line.replay_content

    def test_unchanged_with_both_none_succeeds(self) -> None:
        """change_type='unchanged' with both contents None succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content=None,
            replay_content=None,
            change_type="unchanged",
        )
        assert line.change_type == "unchanged"

    def test_modified_with_missing_baseline_raises_error(self) -> None:
        """change_type='modified' with None baseline_content raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content=None,
                replay_content="new content",
                change_type="modified",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "baseline_content to be present" in str(errors[0]["msg"])

    def test_modified_with_missing_replay_raises_error(self) -> None:
        """change_type='modified' with None replay_content raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="old content",
                replay_content=None,
                change_type="modified",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "replay_content to be present" in str(errors[0]["msg"])

    def test_modified_with_same_contents_raises_error(self) -> None:
        """change_type='modified' with identical content values raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffLine(
                line_number=1,
                baseline_content="same content",
                replay_content="same content",
                change_type="modified",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "to be different" in str(errors[0]["msg"])

    def test_modified_with_different_contents_succeeds(self) -> None:
        """change_type='modified' with different content values succeeds."""
        line = ModelDiffLine(
            line_number=1,
            baseline_content="old content",
            replay_content="new content",
            change_type="modified",
        )
        assert line.change_type == "modified"
        assert line.baseline_content != line.replay_content
