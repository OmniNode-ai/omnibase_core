# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for EnumHookBit and hook_enabled()."""

from __future__ import annotations

import enum

import pytest

from omnibase_core.enums.enum_hook_bit import EnumHookBit, hook_enabled

pytestmark = pytest.mark.unit

# Frozen GATE count from Task 1 inventory. Update only when the inventory doc changes.
_N_GATE = 57


class TestEnumHookBit:
    def test_is_int_enum(self) -> None:
        assert issubclass(EnumHookBit, enum.IntEnum)

    def test_ci_reminder_is_power_of_two(self) -> None:
        assert EnumHookBit.CI_REMINDER > 0
        v = int(EnumHookBit.CI_REMINDER)
        assert v & (v - 1) == 0, "CI_REMINDER must be a single-bit power of two"

    def test_every_member_is_power_of_two(self) -> None:
        for m in EnumHookBit:
            v = int(m)
            assert v > 0
            assert v & (v - 1) == 0, f"{m.name}={v} is not a single-bit value"

    def test_no_duplicate_bits(self) -> None:
        values = [int(m) for m in EnumHookBit]
        assert len(values) == len(set(values))

    def test_bits_fit_in_64(self) -> None:
        for m in EnumHookBit:
            assert int(m) < (1 << 64)

    def test_member_count_matches_inventory(self) -> None:
        assert len(list(EnumHookBit)) == _N_GATE

    def test_default_mask_covers_all_members(self) -> None:
        from omnibase_core.enums.enum_hook_bit import _DEFAULT_MASK

        for m in EnumHookBit:
            assert _DEFAULT_MASK & m, f"{m.name} not covered by _DEFAULT_MASK"

    def test_default_mask_is_not_hardcoded_0xffffffff(self) -> None:
        from omnibase_core.enums.enum_hook_bit import _DEFAULT_MASK

        assert _DEFAULT_MASK != 0xFFFFFFFF


class TestHookEnabled:
    def test_default_mask_all_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ONEX_HOOKS_MASK", raising=False)
        for m in EnumHookBit:
            assert hook_enabled(m) is True

    def test_explicit_mask_disables_one_bit(self) -> None:
        ci = int(EnumHookBit.CI_REMINDER)
        all_on = (1 << len(EnumHookBit)) - 1
        mask = all_on & ~ci
        assert hook_enabled(EnumHookBit.CI_REMINDER, mask=mask) is False
        other = next(m for m in EnumHookBit if m is not EnumHookBit.CI_REMINDER)
        assert hook_enabled(other, mask=mask) is True

    def test_env_mask_hex(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ci = int(EnumHookBit.CI_REMINDER)
        all_on = (1 << len(EnumHookBit)) - 1
        monkeypatch.setenv("ONEX_HOOKS_MASK", hex(all_on & ~ci))
        assert hook_enabled(EnumHookBit.CI_REMINDER) is False

    def test_env_mask_decimal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ci = int(EnumHookBit.CI_REMINDER)
        all_on = (1 << len(EnumHookBit)) - 1
        monkeypatch.setenv("ONEX_HOOKS_MASK", str(all_on & ~ci))
        assert hook_enabled(EnumHookBit.CI_REMINDER) is False

    def test_env_mask_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ci = int(EnumHookBit.CI_REMINDER)
        all_on = (1 << len(EnumHookBit)) - 1
        monkeypatch.setenv("ONEX_HOOKS_MASK", bin(all_on & ~ci))
        assert hook_enabled(EnumHookBit.CI_REMINDER) is False

    def test_malformed_mask_defaults_to_all_on(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_HOOKS_MASK", "not-a-number")
        for m in EnumHookBit:
            assert hook_enabled(m) is True

    def test_explicit_negative_mask_minus_one_is_fail_open(self) -> None:
        for m in EnumHookBit:
            assert hook_enabled(m, mask=-1) is True, (
                f"{m.name}: mask=-1 should fail-open (True), not silently disable"
            )

    def test_explicit_negative_mask_minus_two_is_fail_open(self) -> None:
        # -2 in Python two's complement: bit 0 is clear, so CI_REMINDER would
        # return False if negative masks were evaluated as-is.
        for m in EnumHookBit:
            assert hook_enabled(m, mask=-2) is True, (
                f"{m.name}: mask=-2 must fail-open, not clear bit 0"
            )

    def test_env_negative_mask_is_fail_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ONEX_HOOKS_MASK", "-2")
        for m in EnumHookBit:
            assert hook_enabled(m) is True, (
                f"{m.name}: ONEX_HOOKS_MASK=-2 must fail-open"
            )
