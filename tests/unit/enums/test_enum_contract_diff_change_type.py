# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for EnumContractDiffChangeType."""

import pytest

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)


@pytest.mark.unit
class TestEnumContractDiffChangeType:
    """Test suite for EnumContractDiffChangeType enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values exist."""
        assert EnumContractDiffChangeType.ADDED.value == "added"
        assert EnumContractDiffChangeType.REMOVED.value == "removed"
        assert EnumContractDiffChangeType.MODIFIED.value == "modified"
        assert EnumContractDiffChangeType.MOVED.value == "moved"
        assert EnumContractDiffChangeType.UNCHANGED.value == "unchanged"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 5 members."""
        members = list(EnumContractDiffChangeType)
        assert len(members) == 5

    def test_is_change_property_added(self) -> None:
        """Test is_change returns True for ADDED."""
        assert EnumContractDiffChangeType.ADDED.is_change is True

    def test_is_change_property_removed(self) -> None:
        """Test is_change returns True for REMOVED."""
        assert EnumContractDiffChangeType.REMOVED.is_change is True

    def test_is_change_property_modified(self) -> None:
        """Test is_change returns True for MODIFIED."""
        assert EnumContractDiffChangeType.MODIFIED.is_change is True

    def test_is_change_property_moved(self) -> None:
        """Test is_change returns True for MOVED."""
        assert EnumContractDiffChangeType.MOVED.is_change is True

    def test_is_change_property_unchanged(self) -> None:
        """Test is_change returns False only for UNCHANGED."""
        assert EnumContractDiffChangeType.UNCHANGED.is_change is False

    def test_get_reverse_added_to_removed(self) -> None:
        """Test ADDED reverses to REMOVED."""
        result = EnumContractDiffChangeType.ADDED.get_reverse()
        assert result == EnumContractDiffChangeType.REMOVED

    def test_get_reverse_removed_to_added(self) -> None:
        """Test REMOVED reverses to ADDED."""
        result = EnumContractDiffChangeType.REMOVED.get_reverse()
        assert result == EnumContractDiffChangeType.ADDED

    def test_get_reverse_modified_unchanged(self) -> None:
        """Test MODIFIED reverses to MODIFIED."""
        result = EnumContractDiffChangeType.MODIFIED.get_reverse()
        assert result == EnumContractDiffChangeType.MODIFIED

    def test_get_reverse_moved_unchanged(self) -> None:
        """Test MOVED reverses to MOVED."""
        result = EnumContractDiffChangeType.MOVED.get_reverse()
        assert result == EnumContractDiffChangeType.MOVED

    def test_get_reverse_unchanged_unchanged(self) -> None:
        """Test UNCHANGED reverses to UNCHANGED."""
        result = EnumContractDiffChangeType.UNCHANGED.get_reverse()
        assert result == EnumContractDiffChangeType.UNCHANGED

    def test_string_representation(self) -> None:
        """Test __str__ returns value."""
        assert str(EnumContractDiffChangeType.ADDED) == "added"
        assert str(EnumContractDiffChangeType.REMOVED) == "removed"
        assert str(EnumContractDiffChangeType.MODIFIED) == "modified"
        assert str(EnumContractDiffChangeType.MOVED) == "moved"
        assert str(EnumContractDiffChangeType.UNCHANGED) == "unchanged"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        change1 = EnumContractDiffChangeType.ADDED
        change2 = EnumContractDiffChangeType.ADDED
        change3 = EnumContractDiffChangeType.REMOVED

        assert change1 == change2
        assert change1 != change3
        assert change1 is change2

    def test_enum_in_collection(self) -> None:
        """Test enum usage in collections."""
        changes = {
            EnumContractDiffChangeType.ADDED,
            EnumContractDiffChangeType.MODIFIED,
        }
        assert EnumContractDiffChangeType.ADDED in changes
        assert EnumContractDiffChangeType.REMOVED not in changes

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        members = list(EnumContractDiffChangeType)
        assert EnumContractDiffChangeType.ADDED in members
        assert EnumContractDiffChangeType.REMOVED in members
        assert EnumContractDiffChangeType.MODIFIED in members
        assert EnumContractDiffChangeType.MOVED in members
        assert EnumContractDiffChangeType.UNCHANGED in members

    def test_enum_membership_check(self) -> None:
        """Test membership checks."""
        values = [e.value for e in EnumContractDiffChangeType]
        assert "added" in values
        assert "removed" in values
        assert "modified" in values
        assert "moved" in values
        assert "unchanged" in values
        assert "invalid" not in values

    def test_enum_value_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [e.value for e in EnumContractDiffChangeType]
        assert len(values) == len(set(values))

    def test_enum_as_dict_key(self) -> None:
        """Test using enum as dictionary key."""
        change_config = {
            EnumContractDiffChangeType.ADDED: "new",
            EnumContractDiffChangeType.REMOVED: "deleted",
            EnumContractDiffChangeType.MODIFIED: "changed",
        }
        assert change_config[EnumContractDiffChangeType.ADDED] == "new"
        assert change_config[EnumContractDiffChangeType.REMOVED] == "deleted"

    def test_enum_name_attribute(self) -> None:
        """Test enum name attribute."""
        assert EnumContractDiffChangeType.ADDED.name == "ADDED"
        assert EnumContractDiffChangeType.REMOVED.name == "REMOVED"
        assert EnumContractDiffChangeType.MODIFIED.name == "MODIFIED"
        assert EnumContractDiffChangeType.MOVED.name == "MOVED"
        assert EnumContractDiffChangeType.UNCHANGED.name == "UNCHANGED"

    def test_reverse_is_idempotent_for_symmetric_types(self) -> None:
        """Test that double reverse returns original for symmetric types."""
        for change_type in [
            EnumContractDiffChangeType.MODIFIED,
            EnumContractDiffChangeType.MOVED,
            EnumContractDiffChangeType.UNCHANGED,
        ]:
            assert change_type.get_reverse().get_reverse() == change_type

    def test_reverse_swaps_added_removed(self) -> None:
        """Test that ADDED and REMOVED swap with each other."""
        added = EnumContractDiffChangeType.ADDED
        removed = EnumContractDiffChangeType.REMOVED
        assert added.get_reverse() == removed
        assert removed.get_reverse() == added
        assert added.get_reverse().get_reverse() == added
