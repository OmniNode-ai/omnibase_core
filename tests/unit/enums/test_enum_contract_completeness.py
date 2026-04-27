# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumContractCompleteness enum.

Covers OMN-10063 (Task 1.5 of OMN-9582): Create EnumContractCompleteness in omnibase_core.
"""

from enum import Enum

import pytest
from omnibase_core.enums.enum_contract_completeness import EnumContractCompleteness


@pytest.mark.unit
class TestEnumContractCompleteness:
    """Test cases for EnumContractCompleteness enum."""

    def test_all_three_members_exist(self) -> None:
        """Test that STUB, ENRICHED, and FULL members are present."""
        assert EnumContractCompleteness.STUB is not None
        assert EnumContractCompleteness.ENRICHED is not None
        assert EnumContractCompleteness.FULL is not None

    def test_member_values(self) -> None:
        """Test that each member has the correct string value."""
        assert EnumContractCompleteness.STUB.value == "STUB"
        assert EnumContractCompleteness.ENRICHED.value == "ENRICHED"
        assert EnumContractCompleteness.FULL.value == "FULL"

    def test_is_str_subclass(self) -> None:
        """Test that enum is a str subclass (enables YAML serialization round-trip)."""
        assert issubclass(EnumContractCompleteness, str)
        assert issubclass(EnumContractCompleteness, Enum)

    def test_members_are_str_instances(self) -> None:
        """Test that enum members behave as strings."""
        assert isinstance(EnumContractCompleteness.STUB, str)
        assert isinstance(EnumContractCompleteness.ENRICHED, str)
        assert isinstance(EnumContractCompleteness.FULL, str)

    def test_round_trip_from_string(self) -> None:
        """Test that EnumContractCompleteness('STUB') round-trips without error."""
        assert EnumContractCompleteness("STUB") == EnumContractCompleteness.STUB
        assert EnumContractCompleteness("ENRICHED") == EnumContractCompleteness.ENRICHED
        assert EnumContractCompleteness("FULL") == EnumContractCompleteness.FULL

    def test_invalid_value_raises(self) -> None:
        """Test that an unknown value raises ValueError."""
        with pytest.raises(ValueError):
            EnumContractCompleteness("stub")  # lowercase — invalid

    def test_all_values_set(self) -> None:
        """Test that exactly three values are defined."""
        expected = {"STUB", "ENRICHED", "FULL"}
        actual = {member.value for member in EnumContractCompleteness}
        assert actual == expected

    def test_exported_from_package_init(self) -> None:
        """Test that EnumContractCompleteness is importable from omnibase_core.enums."""
        from omnibase_core.enums import EnumContractCompleteness as ImportedEnum

        assert ImportedEnum is EnumContractCompleteness
