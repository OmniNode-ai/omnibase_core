# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumSubjectType.

Tests serialization/deserialization and basic enum behavior
for the memory ownership subject type enum.
"""

import copy
import json
import pickle

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
        ("member", "value"),
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
    def test_serialization_roundtrip(self, member: EnumSubjectType, value: str) -> None:
        """Test enum serialization/deserialization round-trip."""
        # Serialization: member.value equals expected string
        assert member.value == value
        # Direct string comparison (str subclass)
        assert member == value
        # Deserialization: string value constructs back to member
        assert EnumSubjectType(value) == member

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

    def test_str_method(self) -> None:
        """Test __str__ returns the enum value."""
        # Test representative members
        assert str(EnumSubjectType.AGENT) == "agent"
        assert str(EnumSubjectType.WORKFLOW) == "workflow"
        assert str(EnumSubjectType.CUSTOM) == "custom"
        # Verify str() equals .value for all members
        for member in EnumSubjectType:
            assert str(member) == member.value

    @pytest.mark.parametrize(
        "value",
        ["agent", "workflow", "custom", "user", "session"],
    )
    def test_is_valid_with_valid_values(self, value: str) -> None:
        """Test is_valid returns True for valid enum values."""
        assert EnumSubjectType.is_valid(value) is True

    @pytest.mark.parametrize(
        "value",
        ["invalid_type", "", "AGENT", "Agent", "unknown"],
    )
    def test_is_valid_with_invalid_values(self, value: str) -> None:
        """Test is_valid returns False for invalid values."""
        assert EnumSubjectType.is_valid(value) is False

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (EnumSubjectType.AGENT, True),
            (EnumSubjectType.USER, True),
            (EnumSubjectType.SERVICE, True),
            (EnumSubjectType.WORKFLOW, False),
            (EnumSubjectType.PROJECT, False),
            (EnumSubjectType.ORG, False),
            (EnumSubjectType.TASK, False),
            (EnumSubjectType.CORPUS, False),
            (EnumSubjectType.SESSION, False),
            (EnumSubjectType.CUSTOM, False),
        ],
    )
    def test_is_entity_type(self, member: EnumSubjectType, expected: bool) -> None:
        """Test is_entity_type identifies entity subjects (agent, user, service)."""
        assert member.is_entity_type() is expected

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (EnumSubjectType.WORKFLOW, True),
            (EnumSubjectType.PROJECT, True),
            (EnumSubjectType.ORG, True),
            (EnumSubjectType.TASK, True),
            (EnumSubjectType.SESSION, True),
            (EnumSubjectType.CORPUS, True),
            (EnumSubjectType.AGENT, False),
            (EnumSubjectType.USER, False),
            (EnumSubjectType.SERVICE, False),
            (EnumSubjectType.CUSTOM, False),
        ],
    )
    def test_is_scope_type(self, member: EnumSubjectType, expected: bool) -> None:
        """Test is_scope_type identifies scope subjects (workflow, project, etc.)."""
        assert member.is_scope_type() is expected

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (EnumSubjectType.AGENT, True),
            (EnumSubjectType.USER, True),
            (EnumSubjectType.WORKFLOW, True),
            (EnumSubjectType.PROJECT, True),
            (EnumSubjectType.SERVICE, True),
            (EnumSubjectType.ORG, True),
            (EnumSubjectType.TASK, True),
            (EnumSubjectType.CORPUS, True),
            (EnumSubjectType.CUSTOM, True),
            (EnumSubjectType.SESSION, False),
        ],
    )
    def test_is_persistent(self, member: EnumSubjectType, expected: bool) -> None:
        """Test is_persistent identifies subjects with long-term memory."""
        assert member.is_persistent() is expected

    @pytest.mark.parametrize("member", list(EnumSubjectType))
    def test_pickle_serialization(self, member: EnumSubjectType) -> None:
        """Test enum values can be pickled and unpickled correctly."""
        pickled = pickle.dumps(member)
        unpickled = pickle.loads(pickled)
        # Verify identity and value
        assert unpickled == member
        assert unpickled.value == member.value
        assert type(unpickled) is EnumSubjectType

    @pytest.mark.parametrize("member", list(EnumSubjectType))
    def test_deep_copy(self, member: EnumSubjectType) -> None:
        """Test enum values can be deep copied correctly."""
        copied = copy.deepcopy(member)
        # Verify identity and value
        assert copied == member
        assert copied.value == member.value
        assert type(copied) is EnumSubjectType
        # For enums, deep copy should return the same object (singletons)
        assert copied is member
