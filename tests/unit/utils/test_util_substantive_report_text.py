# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``validate_substantive_report_text`` (OMN-15161).

Ported from steel_onslaught PR #213's
``tests/scripts/test_check_report_contract.py`` pure-function suite. Every
case here drives the real function -- no mocks.
"""

from __future__ import annotations

import pytest

from omnibase_core.utils.util_substantive_report_text import (
    validate_substantive_report_text,
)

pytestmark = pytest.mark.unit

_SUBSTANTIVE_SUMMARY = (
    "Implemented the golden-chain report contract module and CLI validator, "
    "added seeded RED/GREEN tests per role, and confirmed ruff/mypy/pytest "
    "all pass locally before opening the PR."
)


def test_accepts_real_prose() -> None:
    assert (
        validate_substantive_report_text(_SUBSTANTIVE_SUMMARY) == _SUBSTANTIVE_SUMMARY
    )


def test_accepts_prose_that_mentions_the_word_test() -> None:
    """A real report that legitimately uses the word 'test' in a sentence must
    never be flagged -- placeholder matching is exact-literal, not substring.
    """
    text = (
        "Ran the full integration test suite locally; all 214 tests passed before push."
    )
    assert validate_substantive_report_text(text) == text


@pytest.mark.parametrize(
    "literal",
    ["test", "TEST", "Test.", "  test  ", "todo", "placeholder", "lorem ipsum"],
)
def test_rejects_placeholder_literals(literal: str) -> None:
    with pytest.raises(ValueError, match="placeholder"):
        validate_substantive_report_text(literal)


@pytest.mark.parametrize(
    "literal",
    ["Done.", "done", "Task complete.", "No further action taken.", "Finished", "ok."],
)
def test_rejects_bare_acknowledgements(literal: str) -> None:
    with pytest.raises(ValueError, match="bare acknowledgement"):
        validate_substantive_report_text(literal)


def test_rejects_under_length_filler() -> None:
    with pytest.raises(ValueError, match="too short"):
        validate_substantive_report_text("Fixed the bug, all good now.")  # 29 chars


def test_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        validate_substantive_report_text("   ")


@pytest.mark.parametrize(
    "literal",
    [
        "Done. Done. Done. Done. Done. Done. Done.",
        "test. test. test. test. test. test. test.",
        "ok. ok. ok. ok. ok. ok. ok. ok. ok.",
    ],
)
def test_rejects_padded_repeated_literal(literal: str) -> None:
    """A banned bare-acknowledgement/placeholder literal repeated with
    sentence separators past the length minimum must still be rejected --
    the whole padded string is never itself an exact match for the bare
    literal, so this is a distinct detector from the exact-literal check.
    """
    with pytest.raises(ValueError, match="repetitive low-content padding"):
        validate_substantive_report_text(literal)


def test_rejects_keyboard_mash_filler() -> None:
    """A short unit repeated with no separators at all (no real content,
    just enough characters to clear the length floor) must be rejected on
    the same grounds as padded-literal repetition.
    """
    with pytest.raises(ValueError, match="repetitive low-content padding"):
        validate_substantive_report_text("asdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf")


def test_accepts_prose_with_incidental_repeated_word() -> None:
    """Real prose that happens to repeat a word a couple of times (not the
    entire content, not a short-unit blob) must never be flagged -- the
    padding detector requires the repeated unit to dominate the text.
    """
    text = (
        "Reviewed the diff twice: once for correctness, once for style, and confirmed "
        "the tests still pass both times before opening the PR."
    )
    assert validate_substantive_report_text(text) == text


def test_custom_field_name_appears_in_error() -> None:
    with pytest.raises(ValueError, match=r"^summary is"):
        validate_substantive_report_text("Done.", field_name="summary")
