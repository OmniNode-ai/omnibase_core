# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure move parsing and shared baseline budget cases."""

from __future__ import annotations

import pytest

from omnibase_core.validation.checker_baseline_moves import (
    carry_baseline,
    parse_name_status_moves,
)


@pytest.mark.unit
def test_parse_name_status_moves_keeps_only_renames_and_copies() -> None:
    assert parse_name_status_moves(
        "R100\tsrc/old.py\tsrc/new.py\n"
        "C075\tsrc/source.py\tsrc/copy.py\n"
        "A\tsrc/added.py\n"
        "M\tsrc/modified.py\n"
        "D\tsrc/deleted.py\n\n"
    ) == {"src/new.py": "src/old.py", "src/copy.py": "src/source.py"}


@pytest.mark.unit
def test_parse_name_status_moves_preserves_spaces_and_first_destination() -> None:
    assert parse_name_status_moves(
        "R090\tsrc/old name.py\tsrc/new name.py\nC100\tsrc/other.py\tsrc/new name.py\n"
    ) == {"src/new name.py": "src/old name.py"}


@pytest.mark.unit
def test_parse_name_status_moves_ignores_malformed_records() -> None:
    assert (
        parse_name_status_moves(
            "\nR\told.py\tnew.py\nCbad\told.py\tnew.py\n"
            "R100\tonly.py\nR100\ta.py\tb.py\textra.py\n"
        )
        == {}
    )


@pytest.mark.unit
def test_own_entry_keeps_its_full_allowance_despite_a_move() -> None:
    assert carry_baseline(
        {"new.py": 1}, {"old.py": 5, "new.py": 2}, {"new.py": "old.py"}
    ) == {"new.py": 2}


@pytest.mark.unit
@pytest.mark.parametrize(("count", "allowed"), [(1, 1), (2, 2), (3, 2)])
def test_one_move_is_limited_by_the_head_and_origin(count: int, allowed: int) -> None:
    assert carry_baseline({"new.py": count}, {"old.py": 2}, {"new.py": "old.py"}) == {
        "new.py": allowed
    }


@pytest.mark.unit
def test_a_move_chain_reaches_the_base_origin() -> None:
    assert carry_baseline(
        {"c.py": 2}, {"a.py": 2}, {"b.py": "a.py", "c.py": "b.py"}
    ) == {"c.py": 2}


@pytest.mark.unit
def test_a_move_cycle_has_no_allowance() -> None:
    assert carry_baseline(
        {"a.py": 1, "b.py": 1}, {}, {"a.py": "b.py", "b.py": "a.py"}
    ) == {"a.py": 0, "b.py": 0}


@pytest.mark.unit
def test_destinations_share_one_budget_in_sorted_order() -> None:
    moves = {"b.py": "old.py", "a.py": "old.py"}
    base = {"old.py": 2}
    head = {"b.py": 1, "a.py": 2}
    assert carry_baseline(head, base, moves) == {"a.py": 2, "b.py": 0}
    assert carry_baseline(dict(reversed(head.items())), base, moves) == {
        "a.py": 2,
        "b.py": 0,
    }
    assert carry_baseline({"a.py": 1, "b.py": 1}, base, moves) == {
        "a.py": 1,
        "b.py": 1,
    }


@pytest.mark.unit
@pytest.mark.parametrize(("retained", "allowed"), [(1, 1), (2, 0), (3, 0)])
def test_the_origin_reserves_what_head_still_holds(retained: int, allowed: int) -> None:
    assert carry_baseline(
        {"old.py": retained, "new.py": 2},
        {"old.py": 2},
        {"new.py": "old.py"},
    ) == {"new.py": allowed, "old.py": 2}


@pytest.mark.unit
def test_chained_destinations_share_the_same_origin_budget() -> None:
    assert carry_baseline(
        {"b.py": 1, "c.py": 2},
        {"a.py": 2},
        {"b.py": "a.py", "c.py": "b.py"},
    ) == {"b.py": 1, "c.py": 1}


@pytest.mark.unit
def test_an_unrelated_new_path_has_no_allowance() -> None:
    assert carry_baseline({"fresh.py": 1}, {"old.py": 2}, {}) == {"fresh.py": 0}


@pytest.mark.unit
def test_empty_moves_matches_the_original_per_path_allowance() -> None:
    head = {"a.py": 1, "b.py": 3, "fresh.py": 1}
    base = {"a.py": 2, "b.py": 2, "removed.py": 4}
    assert carry_baseline(head, base, {}) == {path: base.get(path, 0) for path in head}
