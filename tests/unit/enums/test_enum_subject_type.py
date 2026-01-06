"""Unit tests for EnumSubjectType.

Tests serialization/deserialization and basic enum behavior
for the memory ownership subject type enum.
"""

import json

import pytest

from omnibase_core.enums.enum_subject_type import EnumSubjectType


@pytest.mark.unit
class TestEnumSubjectType:
    """Tests for EnumSubjectType enum."""

    def test_all_values_defined(self) -> None:
        """Verify all 10 expected subject types are defined."""
        expected_values = {
            "agent",
            "user",
            "workflow",
            "project",
            "service",
            "org",
            "task",
            "corpus",
            "session",
            "custom",
        }
        actual_values = {member.value for member in EnumSubjectType}
        assert actual_values == expected_values
        assert len(EnumSubjectType) == 10

    def test_string_enum_inheritance(self) -> None:
        """Verify enum inherits from str for JSON serialization."""
        assert isinstance(EnumSubjectType.AGENT, str)
        assert EnumSubjectType.AGENT == "agent"

    @pytest.mark.parametrize(
        ("member", "expected_value"),
        [
            (EnumSubjectType.AGENT, "agent"),
            (EnumSubjectType.USER, "user"),
            (EnumSubjectType.WORKFLOW, "workflow"),
            (EnumSubjectType.PROJECT, "project"),
            (EnumSubjectType.SERVICE, "service"),
            (EnumSubjectType.ORG, "org"),
            (EnumSubjectType.TASK, "task"),
            (EnumSubjectType.CORPUS, "corpus"),
            (EnumSubjectType.SESSION, "session"),
            (EnumSubjectType.CUSTOM, "custom"),
        ],
    )
    def test_serialization(self, member: EnumSubjectType, expected_value: str) -> None:
        """Test enum serializes to expected string value."""
        assert member.value == expected_value

    @pytest.mark.parametrize(
        "value",
        [
            "agent",
            "user",
            "workflow",
            "project",
            "service",
            "org",
            "task",
            "corpus",
            "session",
            "custom",
        ],
    )
    def test_deserialization(self, value: str) -> None:
        """Test enum deserializes from string value."""
        result = EnumSubjectType(value)
        assert result.value == value

    def test_invalid_value_raises(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumSubjectType("invalid_subject")

    def test_json_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        data = {"subject_type": EnumSubjectType.AGENT}
        json_str = json.dumps(data)
        assert '"agent"' in json_str

        # Deserialize
        parsed = json.loads(json_str)
        result = EnumSubjectType(parsed["subject_type"])
        assert result == EnumSubjectType.AGENT

    def test_custom_escape_hatch(self) -> None:
        """Test CUSTOM value exists as forward-compatibility escape hatch."""
        assert EnumSubjectType.CUSTOM.value == "custom"
        # Can be used directly
        custom = EnumSubjectType("custom")
        assert custom == EnumSubjectType.CUSTOM

    def test_hashable(self) -> None:
        """Test enum values are hashable for use in sets/dicts."""
        subject_set = {EnumSubjectType.AGENT, EnumSubjectType.USER}
        assert len(subject_set) == 2
        assert EnumSubjectType.AGENT in subject_set

    def test_equality(self) -> None:
        """Test enum equality comparisons."""
        assert EnumSubjectType.AGENT == EnumSubjectType.AGENT
        assert EnumSubjectType.AGENT == "agent"
        assert EnumSubjectType.AGENT != EnumSubjectType.USER
