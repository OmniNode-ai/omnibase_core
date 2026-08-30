# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumDelegationTerminalFailureCause.

Part of OMN-16998: a terminal delegation failure must name the provider status
class it actually observed. Before this ticket the enum carried a single member,
so a live HTTP 401 had no cause it could resolve to and was recorded as
``provider_quota_exhausted`` -- corrupting the over-quota refusal metric, which
is measured from this field.

These tests pin the wire vocabulary. The status-to-cause mapping itself is
asserted in omnimarket, where the classifier lives.
"""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)

# Every member and the exact wire string it serialises to. Adding a member here
# is deliberate: this constant is what makes a silent vocabulary change fail.
EXPECTED_MEMBERS: dict[EnumDelegationTerminalFailureCause, str] = {
    EnumDelegationTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED: "provider_quota_exhausted",
    EnumDelegationTerminalFailureCause.AUTH_FAILED: "auth_failed",
    EnumDelegationTerminalFailureCause.PROVIDER_ERROR: "provider_error",
}


@pytest.mark.unit
class TestEnumDelegationTerminalFailureCause:
    """Wire-contract tests for the terminal failure cause vocabulary."""

    @pytest.mark.parametrize(("member", "wire_value"), list(EXPECTED_MEMBERS.items()))
    def test_member_serialises_to_its_pinned_wire_value(
        self,
        member: EnumDelegationTerminalFailureCause,
        wire_value: str,
    ) -> None:
        """Each member's wire string is pinned to an exact value.

        These strings cross a process boundary into the terminal payload, so a
        rename is a breaking contract change and must fail here first.
        """
        assert member.value == wire_value
        assert json.dumps(member) == f'"{wire_value}"'

    @pytest.mark.parametrize(("member", "wire_value"), list(EXPECTED_MEMBERS.items()))
    def test_member_round_trips_from_its_wire_value(
        self,
        member: EnumDelegationTerminalFailureCause,
        wire_value: str,
    ) -> None:
        """A wire string deserialises back to the member that produced it."""
        assert EnumDelegationTerminalFailureCause(wire_value) is member

    def test_vocabulary_is_exactly_the_pinned_set(self) -> None:
        """No member exists that this suite does not know about.

        Guards the direction the parametrized tests cannot: they prove every
        expected member is present, this proves no unexpected one is.
        """
        assert set(EnumDelegationTerminalFailureCause) == set(EXPECTED_MEMBERS)

    def test_causes_are_mutually_distinct(self) -> None:
        """Auth, quota and generic provider failures are three separate facts.

        The OMN-16998 defect was an auth failure wearing the quota label. If any
        two of these ever compare equal, that defect becomes unobservable.
        """
        values = [member.value for member in EnumDelegationTerminalFailureCause]
        assert len(values) == len(set(values))

    def test_enum_is_a_string_enum(self) -> None:
        """Members must be ``str`` so they serialise without a custom encoder."""
        assert issubclass(EnumDelegationTerminalFailureCause, str)
        assert issubclass(EnumDelegationTerminalFailureCause, Enum)

    def test_unrecognised_wire_value_is_rejected(self) -> None:
        """An unknown cause fails loudly rather than coercing to a member.

        A terminal carrying a cause this build cannot express must surface as an
        error, not silently degrade to the nearest label -- which is the failure
        shape this ticket exists to remove.
        """
        with pytest.raises(ValueError):
            EnumDelegationTerminalFailureCause("rate_limited")
