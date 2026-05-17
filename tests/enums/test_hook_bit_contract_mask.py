# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-mask invariants for EnumHookBit (OMN-11083)."""

from __future__ import annotations

import functools
import operator

import pytest

from omnibase_core.enums.enum_hook_bit import (
    _DEFAULT_MASK,
    _DISABLED_BY_DEFAULT,
    EnumHookBit,
    hook_enabled,
)

pytestmark = pytest.mark.unit

_OPT_IN_GATES = frozenset({"AISLOP_GATE", "STOP_QUALITY_GATE", "INLINE_REVIEW_GATE"})


def test_opt_in_gate_members_are_append_only_bits() -> None:
    assert EnumHookBit.AISLOP_GATE == 1 << 60
    assert EnumHookBit.STOP_QUALITY_GATE == 1 << 61
    assert EnumHookBit.INLINE_REVIEW_GATE == 1 << 62


def test_disabled_by_default_names_match_omn_11083_contract() -> None:
    assert _DISABLED_BY_DEFAULT == _OPT_IN_GATES


def test_default_mask_matches_enabled_contract_bits() -> None:
    expected = functools.reduce(
        operator.or_,
        (int(member) for member in EnumHookBit if member.name not in _OPT_IN_GATES),
        0,
    )
    assert expected == _DEFAULT_MASK


def test_default_mask_excludes_opt_in_gates() -> None:
    for name in _OPT_IN_GATES:
        assert not (_DEFAULT_MASK & int(EnumHookBit[name]))


def test_default_mask_includes_existing_sixty_bits() -> None:
    for bit_index in range(60):
        assert _DEFAULT_MASK & (1 << bit_index), f"bit {bit_index} is not enabled"


def test_hook_enabled_uses_contract_default_mask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ONEX_HOOKS_MASK", raising=False)
    assert hook_enabled(EnumHookBit.AISLOP_GATE) is False
    assert hook_enabled(EnumHookBit.WORKTREE_GUARD) is True
