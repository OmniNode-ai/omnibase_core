# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for resolution tier and failure code enums."""

import pytest

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier


@pytest.mark.unit
class TestEnumResolutionTier:
    """Tests for EnumResolutionTier."""

    def test_all_values_present(self) -> None:
        """All five tier values exist."""
        assert EnumResolutionTier.LOCAL_EXACT.value == "local_exact"
        assert EnumResolutionTier.LOCAL_COMPATIBLE.value == "local_compatible"
        assert EnumResolutionTier.ORG_TRUSTED.value == "org_trusted"
        assert EnumResolutionTier.FEDERATED_TRUSTED.value == "federated_trusted"
        assert EnumResolutionTier.QUARANTINE.value == "quarantine"

    def test_member_count(self) -> None:
        """Exactly five members defined."""
        assert len(EnumResolutionTier) == 5

    def test_str_returns_value(self) -> None:
        """str() returns the raw string value (StrValueHelper)."""
        assert str(EnumResolutionTier.LOCAL_EXACT) == "local_exact"
        assert str(EnumResolutionTier.QUARANTINE) == "quarantine"

    def test_lookup_by_value(self) -> None:
        """Can construct from string value."""
        assert EnumResolutionTier("local_exact") is EnumResolutionTier.LOCAL_EXACT
        assert EnumResolutionTier("quarantine") is EnumResolutionTier.QUARANTINE

    def test_invalid_value_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            EnumResolutionTier("nonexistent_tier")

    def test_unique_values(self) -> None:
        """All values are unique strings."""
        values = [m.value for m in EnumResolutionTier]
        assert len(values) == len(set(values))

    def test_is_string_subclass(self) -> None:
        """Enum members are str instances."""
        assert isinstance(EnumResolutionTier.LOCAL_EXACT, str)


@pytest.mark.unit
class TestEnumResolutionFailureCode:
    """Tests for EnumResolutionFailureCode."""

    def test_all_values_present(self) -> None:
        """All seven failure code values exist."""
        assert EnumResolutionFailureCode.NO_MATCH.value == "no_match"
        assert (
            EnumResolutionFailureCode.MATCH_INSUFFICIENT_TRUST.value
            == "match_insufficient_trust"
        )
        assert EnumResolutionFailureCode.POLICY_DENIED.value == "policy_denied"
        assert EnumResolutionFailureCode.KEY_MISMATCH.value == "key_mismatch"
        assert (
            EnumResolutionFailureCode.ATTESTATION_INVALID.value == "attestation_invalid"
        )
        assert EnumResolutionFailureCode.SLA_NOT_MET.value == "sla_not_met"
        assert EnumResolutionFailureCode.TIER_EXHAUSTED.value == "tier_exhausted"

    def test_member_count(self) -> None:
        """Exactly seven members defined."""
        assert len(EnumResolutionFailureCode) == 7

    def test_str_returns_value(self) -> None:
        """str() returns the raw string value (StrValueHelper)."""
        assert str(EnumResolutionFailureCode.NO_MATCH) == "no_match"
        assert str(EnumResolutionFailureCode.TIER_EXHAUSTED) == "tier_exhausted"

    def test_lookup_by_value(self) -> None:
        """Can construct from string value."""
        assert (
            EnumResolutionFailureCode("no_match") is EnumResolutionFailureCode.NO_MATCH
        )
        assert (
            EnumResolutionFailureCode("tier_exhausted")
            is EnumResolutionFailureCode.TIER_EXHAUSTED
        )

    def test_invalid_value_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            EnumResolutionFailureCode("bogus_code")

    def test_unique_values(self) -> None:
        """All values are unique strings."""
        values = [m.value for m in EnumResolutionFailureCode]
        assert len(values) == len(set(values))

    def test_is_string_subclass(self) -> None:
        """Enum members are str instances."""
        assert isinstance(EnumResolutionFailureCode.NO_MATCH, str)
