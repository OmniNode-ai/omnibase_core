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
    OCC_WRITER_BOT_AUTHORS,
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


# OMN-20161: the OCC writer app is exempt ONLY when pin-only is proven. It lives
# in a SEPARATE set so DEPENDENCY_BOT_AUTHORS (unconditional) stays untouched.
WRITER_LOGINS = (
    "onexbot-occ-writer[bot]",  # raw API / event login form
    "app/onexbot-occ-writer",  # gh CLI login form
    "onexbot-occ-writer",
)
WRITER_NEAR_MISSES = (
    "onexbot-occ-writer-fork",
    "app/onexbot-occ-writerx",
    "xonexbot-occ-writer",
    "ONEXBOT-OCC-WRITER",
)


@pytest.mark.unit
def test_dependency_bot_authors_is_unchanged_by_the_writer_exemption() -> None:
    assert (
        frozenset(
            {
                "dependabot[bot]",
                "app/dependabot",
                "dependabot",
                "renovate[bot]",
                "app/renovate",
                "renovate",
            }
        )
        == DEPENDENCY_BOT_AUTHORS
    )


@pytest.mark.unit
def test_writer_set_is_exactly_the_three_logins_and_disjoint() -> None:
    assert isinstance(OCC_WRITER_BOT_AUTHORS, frozenset)
    assert frozenset(WRITER_LOGINS) == OCC_WRITER_BOT_AUTHORS
    assert OCC_WRITER_BOT_AUTHORS.isdisjoint(DEPENDENCY_BOT_AUTHORS)


@pytest.mark.unit
@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_app_is_exempt_only_when_pin_only_is_proven(login: str) -> None:
    assert is_dependency_bot_author(login, pin_only_proven=True) is True
    assert is_dependency_bot_author(login, pin_only_proven=False) is False
    assert is_dependency_bot_author(login) is False  # default: not proven


@pytest.mark.unit
@pytest.mark.parametrize("login", WRITER_NEAR_MISSES)
def test_writer_near_misses_are_never_exempt(login: str) -> None:
    assert is_dependency_bot_author(login, pin_only_proven=True) is False
    assert is_dependency_bot_author(login, pin_only_proven=False) is False


@pytest.mark.unit
@pytest.mark.parametrize("login", [None, "", "jonah", "jonahgabriel"])
def test_humans_are_not_exempt_even_when_pin_only_is_proven(
    login: str | None,
) -> None:
    assert is_dependency_bot_author(login, pin_only_proven=True) is False


@pytest.mark.unit
@pytest.mark.parametrize("proven", [True, False])
def test_dependency_bots_stay_exempt_regardless_of_pin_only(proven: bool) -> None:
    for login in DEPENDENCY_BOT_AUTHORS:
        assert is_dependency_bot_author(login, pin_only_proven=proven) is True
