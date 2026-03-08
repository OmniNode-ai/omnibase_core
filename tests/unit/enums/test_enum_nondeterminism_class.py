# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumNondeterminismClass (OMN-1115)."""

import pytest

from omnibase_core.enums.enum_nondeterminism_class import EnumNondeterminismClass


@pytest.mark.unit
class TestEnumNondeterminismClass:
    """Tests for the nondeterminism classification enum."""

    def test_all_values_present(self) -> None:
        """All five nondeterminism classes are defined."""
        assert EnumNondeterminismClass.DETERMINISTIC == "deterministic"
        assert EnumNondeterminismClass.TIME == "time"
        assert EnumNondeterminismClass.RANDOM == "random"
        assert EnumNondeterminismClass.NETWORK == "network"
        assert EnumNondeterminismClass.EXTERNAL_STATE == "external_state"

    def test_values_class_method(self) -> None:
        """values() returns all enum values as strings."""
        values = EnumNondeterminismClass.values()
        assert len(values) == 5
        assert "deterministic" in values
        assert "network" in values

    def test_string_comparison(self) -> None:
        """Enum members compare equal to their string values."""
        assert EnumNondeterminismClass.DETERMINISTIC == "deterministic"
        assert EnumNondeterminismClass("network") == EnumNondeterminismClass.NETWORK

    def test_uniqueness(self) -> None:
        """All enum values are unique."""
        values = EnumNondeterminismClass.values()
        assert len(values) == len(set(values))
