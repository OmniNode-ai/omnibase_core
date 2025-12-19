from enum import Enum

import pytest

from omnibase_core.enums.enum_file_status import EnumFileStatus


@pytest.mark.unit
class TestEnumFileStatus:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumFileStatus.empty == "empty"
        assert EnumFileStatus.unvalidated == "unvalidated"
        assert EnumFileStatus.validated == "validated"
        assert EnumFileStatus.deprecated == "deprecated"
        assert EnumFileStatus.incomplete == "incomplete"
        assert EnumFileStatus.synthetic == "synthetic"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumFileStatus, str)
        assert issubclass(EnumFileStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumFileStatus.validated
        assert isinstance(status, str)
        assert status == "validated"
        assert len(status) == 9
        assert status.startswith("valid")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumFileStatus)
        assert len(values) == 6
        assert EnumFileStatus.empty in values
        assert EnumFileStatus.synthetic in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumFileStatus.validated in EnumFileStatus
        assert "validated" in [e.value for e in EnumFileStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumFileStatus.validated
        status2 = EnumFileStatus.validated
        status3 = EnumFileStatus.empty

        assert status1 == status2
        assert status1 != status3
        assert status1 == "validated"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumFileStatus.deprecated
        serialized = status.value
        assert serialized == "deprecated"
        import json

        json_str = json.dumps(status)
        assert json_str == '"deprecated"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumFileStatus("incomplete")
        assert status == EnumFileStatus.incomplete

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
            EnumFileStatus.unvalidated,
            EnumFileStatus.validated,
        }

        # Content states
        content_states = {
            EnumFileStatus.empty,
            EnumFileStatus.incomplete,
        }

        # Lifecycle states
        lifecycle_states = {
            EnumFileStatus.deprecated,
            EnumFileStatus.synthetic,
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
            EnumFileStatus.empty,
            EnumFileStatus.unvalidated,
            EnumFileStatus.validated,
        ]

        # All workflow states should be valid
        for state in workflow_states:
            assert state in EnumFileStatus
