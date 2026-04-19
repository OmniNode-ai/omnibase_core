# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumHandlerResolutionOutcome (OMN-9195/OMN-9196).

Verifies the enum contract for the HandlerResolver precedence chain:
exactly six terminal outcomes with lowercase-snake wire-stable values.
"""

from __future__ import annotations

import json
from enum import Enum, StrEnum

import pytest

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)


@pytest.mark.unit
class TestEnumHandlerResolutionOutcomeMembership:
    """Membership + inheritance contract."""

    def test_enum_inherits_from_str_enum(self) -> None:
        """Enum is a StrEnum (str + Enum)."""
        assert issubclass(EnumHandlerResolutionOutcome, StrEnum)
        assert issubclass(EnumHandlerResolutionOutcome, str)
        assert issubclass(EnumHandlerResolutionOutcome, Enum)

    def test_enum_has_six_members(self) -> None:
        """Plan §Task 1 Step 1: exactly six members with fixed names."""
        assert {m.name for m in EnumHandlerResolutionOutcome} == {
            "RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP",
            "RESOLVED_VIA_NODE_REGISTRY",
            "RESOLVED_VIA_CONTAINER",
            "RESOLVED_VIA_EVENT_BUS",
            "RESOLVED_VIA_ZERO_ARG",
            "UNRESOLVABLE",
        }
        assert len(list(EnumHandlerResolutionOutcome)) == 6


@pytest.mark.unit
class TestEnumHandlerResolutionOutcomeValues:
    """Wire-stable lowercase-snake serialization contract."""

    def test_enum_values_are_lowercase_snake(self) -> None:
        """Plan §Task 1 Step 1: explicit test asserting value format."""
        assert (
            EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP.value
            == "resolved_via_local_ownership_skip"
        )
        assert (
            EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY.value
            == "resolved_via_node_registry"
        )
        assert (
            EnumHandlerResolutionOutcome.RESOLVED_VIA_CONTAINER.value
            == "resolved_via_container"
        )
        assert (
            EnumHandlerResolutionOutcome.RESOLVED_VIA_EVENT_BUS.value
            == "resolved_via_event_bus"
        )
        assert (
            EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG.value
            == "resolved_via_zero_arg"
        )
        assert EnumHandlerResolutionOutcome.UNRESOLVABLE.value == "unresolvable"

    def test_values_are_all_strings(self) -> None:
        for member in EnumHandlerResolutionOutcome:
            assert isinstance(member.value, str)
            assert member.value == member.value.lower()
            assert " " not in member.value

    def test_values_are_unique(self) -> None:
        """No aliasing — five success branches + UNRESOLVABLE are distinct."""
        values = [m.value for m in EnumHandlerResolutionOutcome]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestEnumHandlerResolutionOutcomeRoundTrip:
    """Round-trip from value string reconstructs the correct member."""

    def test_from_string_round_trip(self) -> None:
        for member in EnumHandlerResolutionOutcome:
            reconstructed = EnumHandlerResolutionOutcome(member.value)
            assert reconstructed is member

    def test_json_round_trip(self) -> None:
        for member in EnumHandlerResolutionOutcome:
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)
            assert EnumHandlerResolutionOutcome(deserialized) is member

    def test_invalid_value_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            EnumHandlerResolutionOutcome("not_a_real_outcome")


@pytest.mark.unit
class TestEnumHandlerResolutionOutcomeExportedFromPackage:
    """Re-export hygiene: enum is importable from `omnibase_core.enums`."""

    def test_reexport_from_enums_package(self) -> None:
        from omnibase_core.enums import (
            EnumHandlerResolutionOutcome as ReexportedEnum,
        )

        assert ReexportedEnum is EnumHandlerResolutionOutcome


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
