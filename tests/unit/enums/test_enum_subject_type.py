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

    def test_is_valid_with_valid_values(self) -> None:
        """Test is_valid returns True for valid enum values."""
        assert EnumSubjectType.is_valid("agent") is True
        assert EnumSubjectType.is_valid("workflow") is True
        assert EnumSubjectType.is_valid("custom") is True

    def test_is_valid_with_invalid_values(self) -> None:
        """Test is_valid returns False for invalid values."""
        assert EnumSubjectType.is_valid("invalid_type") is False
        assert EnumSubjectType.is_valid("") is False
        assert EnumSubjectType.is_valid("AGENT") is False  # Case-sensitive

    def test_is_entity_type(self) -> None:
        """Test is_entity_type identifies entity subjects (agent, user, service)."""
        # Entity types
        assert EnumSubjectType.AGENT.is_entity_type() is True
        assert EnumSubjectType.USER.is_entity_type() is True
        assert EnumSubjectType.SERVICE.is_entity_type() is True
        # Non-entity types
        assert EnumSubjectType.WORKFLOW.is_entity_type() is False
        assert EnumSubjectType.PROJECT.is_entity_type() is False
        assert EnumSubjectType.SESSION.is_entity_type() is False
        # CUSTOM is not an entity type
        assert EnumSubjectType.CUSTOM.is_entity_type() is False

    def test_is_scope_type(self) -> None:
        """Test is_scope_type identifies scope subjects (workflow, project, etc.)."""
        # Scope types
        assert EnumSubjectType.WORKFLOW.is_scope_type() is True
        assert EnumSubjectType.PROJECT.is_scope_type() is True
        assert EnumSubjectType.ORG.is_scope_type() is True
        assert EnumSubjectType.TASK.is_scope_type() is True
        assert EnumSubjectType.SESSION.is_scope_type() is True
        assert EnumSubjectType.CORPUS.is_scope_type() is True
        # Non-scope types
        assert EnumSubjectType.AGENT.is_scope_type() is False
        assert EnumSubjectType.USER.is_scope_type() is False
        assert EnumSubjectType.SERVICE.is_scope_type() is False
        # CUSTOM is not a scope type
        assert EnumSubjectType.CUSTOM.is_scope_type() is False

    def test_is_persistent(self) -> None:
        """Test is_persistent identifies subjects with long-term memory."""
        # Persistent types (most subjects)
        assert EnumSubjectType.AGENT.is_persistent() is True
        assert EnumSubjectType.USER.is_persistent() is True
        assert EnumSubjectType.WORKFLOW.is_persistent() is True
        assert EnumSubjectType.PROJECT.is_persistent() is True
        # CUSTOM defaults to persistent
        assert EnumSubjectType.CUSTOM.is_persistent() is True
        # Non-persistent types (ephemeral)
        assert EnumSubjectType.SESSION.is_persistent() is False

    def test_pickle_serialization(self) -> None:
        """Test enum values can be pickled and unpickled correctly."""
        for member in EnumSubjectType:
            # Pickle and unpickle
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            # Verify identity and value
            assert unpickled == member
            assert unpickled.value == member.value
            assert type(unpickled) is EnumSubjectType

    def test_deep_copy(self) -> None:
        """Test enum values can be deep copied correctly."""
        for member in EnumSubjectType:
            # Deep copy
            copied = copy.deepcopy(member)
            # Verify identity and value
            assert copied == member
            assert copied.value == member.value
            assert type(copied) is EnumSubjectType
            # For enums, deep copy should return the same object (singletons)
            assert copied is member
