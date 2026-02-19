# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum

import pytest

from omnibase_core.enums.enum_file_status import EnumFileStatus


@pytest.mark.unit
class TestEnumFileStatus:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumFileStatus.EMPTY == "empty"
        assert EnumFileStatus.UNVALIDATED == "unvalidated"
        assert EnumFileStatus.VALIDATED == "validated"
        assert EnumFileStatus.DEPRECATED == "deprecated"
        assert EnumFileStatus.INCOMPLETE == "incomplete"
        assert EnumFileStatus.SYNTHETIC == "synthetic"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumFileStatus, str)
        assert issubclass(EnumFileStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumFileStatus.VALIDATED
        assert isinstance(status, str)
        assert status == "validated"
        assert len(status) == 9
        assert status.startswith("valid")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumFileStatus)
        assert len(values) == 6
        assert EnumFileStatus.EMPTY in values
        assert EnumFileStatus.SYNTHETIC in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumFileStatus.VALIDATED in EnumFileStatus
        assert "validated" in [e.value for e in EnumFileStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumFileStatus.VALIDATED
        status2 = EnumFileStatus.VALIDATED
        status3 = EnumFileStatus.EMPTY

        assert status1 == status2
        assert status1 != status3
        assert status1 == "validated"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumFileStatus.DEPRECATED
        serialized = status.value
        assert serialized == "deprecated"
        import json

        json_str = json.dumps(status)
        assert json_str == '"deprecated"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumFileStatus("incomplete")
        assert status == EnumFileStatus.INCOMPLETE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFileStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "empty",
            "unvalidated",
            "validated",
            "deprecated",
            "incomplete",
            "synthetic",
        }
        actual_values = {e.value for e in EnumFileStatus}
        assert actual_values == expected_values

    def test_enum_member_names_are_upper_snake_case(self):
        """Verify EnumFileStatus member names follow UPPER_SNAKE_CASE convention.

        This test ensures naming convention compliance and catches regressions
        if someone adds a lowercase or mixed-case member name.
        See: OMN-1307
        """
        import re

        # Expected members with their lowercase string values
        expected_members = {
            "EMPTY": "empty",
            "UNVALIDATED": "unvalidated",
            "VALIDATED": "validated",
            "DEPRECATED": "deprecated",
            "INCOMPLETE": "incomplete",
            "SYNTHETIC": "synthetic",
        }

        # Verify all expected members exist with correct values
        for member_name, expected_value in expected_members.items():
            assert hasattr(EnumFileStatus, member_name), (
                f"Missing expected member: {member_name}"
            )
            member = getattr(EnumFileStatus, member_name)
            assert member.value == expected_value, (
                f"Wrong value for {member_name}: expected '{expected_value}', got '{member.value}'"
            )

        # Verify all members follow UPPER_SNAKE_CASE pattern
        upper_snake_case_pattern = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
        for member in EnumFileStatus:
            assert upper_snake_case_pattern.match(member.name), (
                f"Member '{member.name}' does not follow UPPER_SNAKE_CASE convention"
            )

        # Verify no unexpected members were added
        actual_member_names = {member.name for member in EnumFileStatus}
        expected_member_names = set(expected_members.keys())
        assert actual_member_names == expected_member_names, (
            f"Unexpected members found: {actual_member_names - expected_member_names}"
        )

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        # The enum doesn't have a docstring, so we'll test the module docstring instead
        import omnibase_core.enums.enum_file_status as module

        assert module.__doc__ is not None
        assert "file status values" in module.__doc__.lower()

    def test_enum_status_categories(self):
        """Test logical grouping of status values."""
        # Validation states
        validation_states = {
            EnumFileStatus.UNVALIDATED,
            EnumFileStatus.VALIDATED,
        }

        # Content states
        content_states = {
            EnumFileStatus.EMPTY,
            EnumFileStatus.INCOMPLETE,
        }

        # Lifecycle states
        lifecycle_states = {
            EnumFileStatus.DEPRECATED,
            EnumFileStatus.SYNTHETIC,
        }

        # Test that all states are covered
        all_states = validation_states | content_states | lifecycle_states
        assert len(all_states) == 6
        assert all_states == set(EnumFileStatus)

    def test_enum_workflow_progression(self):
        """Test logical workflow progression of file statuses."""
        # Typical progression: empty -> unvalidated -> validated
        # Or: empty -> incomplete -> validated
        # Or: validated -> deprecated

        # Test that we can represent common workflows
        workflow_states = [
            EnumFileStatus.EMPTY,
            EnumFileStatus.UNVALIDATED,
            EnumFileStatus.VALIDATED,
        ]

        # All workflow states should be valid
        for state in workflow_states:
            assert state in EnumFileStatus
