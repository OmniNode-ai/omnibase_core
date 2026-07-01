# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the dependency-bot author exemption (OMN-13762).

The receipt-gate and occ-preflight reusable workflows skip their evidence
steps for trusted dependency-bot authors (Dependabot, Renovate) because a
dependency-bump PR cannot cite a Linear ticket or an OCC receipt. The canonical
allowlist lives in ``validator_receipt_gate.DEPENDENCY_BOT_AUTHORS`` and is
mirrored by the bash ``case`` guards in both workflow YAMLs. These tests pin the
allowlist membership and the ``is_dependency_bot_author`` predicate so the
Python source of truth and the YAML mirror cannot silently drift apart, and so a
near-miss / spoofed login is never exempt.
"""

from __future__ import annotations

import pytest

from omnibase_core.validation.validator_receipt_gate import (
    DEPENDENCY_BOT_AUTHORS,
    is_dependency_bot_author,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "login",
    [
        "dependabot[bot]",  # raw API / event login form
        "app/dependabot",  # gh CLI login form
        "dependabot",
        "renovate[bot]",
        "app/renovate",
        "renovate",
    ],
)
def test_trusted_dependency_bots_are_exempt(login: str) -> None:
    assert is_dependency_bot_author(login) is True
    assert login in DEPENDENCY_BOT_AUTHORS


@pytest.mark.unit
@pytest.mark.parametrize(
    "login",
    [
        None,
        "",
        "jonah",
        "jonahgabriel",
        "dependabot-fork",  # near-miss must NOT be exempt
        "evil-dependabot[bot]",
        "DEPENDABOT[BOT]",  # case-sensitive: GitHub logins are lowercase
        "app/dependabot-impersonator",
    ],
)
def test_non_bot_or_near_miss_authors_are_not_exempt(login: str | None) -> None:
    assert is_dependency_bot_author(login) is False


@pytest.mark.unit
def test_allowlist_is_frozen_and_exact() -> None:
    """The allowlist must stay an immutable, explicit set (no wildcard match)."""
    assert isinstance(DEPENDENCY_BOT_AUTHORS, frozenset)
    # Membership must be exact-match only — guard against an accidental
    # substring/prefix relaxation that would let a spoofed login through.
    assert is_dependency_bot_author("dependabot[bot] ") is False
    assert is_dependency_bot_author(" dependabot[bot]") is False
