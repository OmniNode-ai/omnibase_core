# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the public FAIL > SKIP > PASS rule (OMN-21505).

``aggregate_overall_status`` lives beside :class:`EnumOverallStatus` and is the
single public statement of the precedence rule that
``node_contract_verify_replay_compute`` applied privately under OMN-15862.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path

import pytest

from omnibase_core.enums import enum_overall_status as enum_overall_status_module
from omnibase_core.enums.enum_check_status import EnumCheckStatus
from omnibase_core.enums.enum_overall_status import (
    EnumOverallStatus,
    aggregate_overall_status,
)

pytestmark = pytest.mark.unit

_ALL_STATUSES = (EnumCheckStatus.PASS, EnumCheckStatus.FAIL, EnumCheckStatus.SKIP)

# Every ordered combination of the three statuses, length 1 to 3, with repeats.
_COMBINATIONS = [
    combo
    for size in (1, 2, 3)
    for combo in itertools.product(_ALL_STATUSES, repeat=size)
]


def _expected(combo: tuple[EnumCheckStatus, ...]) -> EnumOverallStatus:
    if EnumCheckStatus.FAIL in combo:
        return EnumOverallStatus.FAIL
    if EnumCheckStatus.SKIP in combo:
        return EnumOverallStatus.SKIP
    return EnumOverallStatus.PASS


@pytest.mark.parametrize(
    "combo",
    _COMBINATIONS,
    ids=lambda combo: "+".join(s.value for s in combo),
)
def test_every_combination_follows_fail_skip_pass(
    combo: tuple[EnumCheckStatus, ...],
) -> None:
    """AC1: FAIL dominates, then SKIP, then PASS, for every combination."""
    assert aggregate_overall_status(combo) is _expected(combo)


def test_combination_count_is_exhaustive() -> None:
    """Positive control: 3 + 9 + 27 combinations were generated."""
    assert len(_COMBINATIONS) == 39


@pytest.mark.parametrize(
    ("combo", "expected"),
    [
        ((EnumCheckStatus.PASS,), EnumOverallStatus.PASS),
        ((EnumCheckStatus.SKIP, EnumCheckStatus.PASS), EnumOverallStatus.SKIP),
        (
            (EnumCheckStatus.PASS, EnumCheckStatus.SKIP, EnumCheckStatus.FAIL),
            EnumOverallStatus.FAIL,
        ),
    ],
)
def test_literal_verdicts(
    combo: tuple[EnumCheckStatus, ...], expected: EnumOverallStatus
) -> None:
    """The verdicts are pinned as literals, not only through the oracle."""
    assert aggregate_overall_status(combo) is expected


def test_empty_input_is_pass_exactly_as_the_node_decided() -> None:
    """No FAIL and no SKIP is PASS: the lifted rule is unchanged for no checks."""
    assert aggregate_overall_status([]) is EnumOverallStatus.PASS


def test_accepts_any_iterable_including_a_generator() -> None:
    assert (
        aggregate_overall_status(
            s for s in (EnumCheckStatus.PASS, EnumCheckStatus.SKIP)
        )
        is EnumOverallStatus.SKIP
    )


def test_never_returns_error() -> None:
    """ERROR is a run-level outcome, never an aggregate of check statuses."""
    assert all(
        aggregate_overall_status(combo) is not EnumOverallStatus.ERROR
        for combo in _COMBINATIONS
    )


def test_function_is_exported() -> None:
    assert "aggregate_overall_status" in enum_overall_status_module.__all__


# =============================================================================
# Configuration (AC3): a core library carries no deployment value
# =============================================================================


def test_module_reads_no_overlay_and_no_environment_variable() -> None:
    """AC3: the module imports no env, file, overlay or YAML reader."""
    source = Path(enum_overall_status_module.__file__ or "").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"os", "pathlib", "yaml", "json", "sys", "subprocess"})
    for token in ("environ", "getenv", "open(", "read_text", "load_overlay"):
        assert token not in source


def test_verdict_is_independent_of_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC3: changing the environment does not move any verdict."""
    baseline = {combo: aggregate_overall_status(combo) for combo in _COMBINATIONS}
    monkeypatch.setenv("ONEX_OVERLAY_PATH", "/nonexistent/overlay.yaml")
    monkeypatch.setenv("ONEX_ENV", "other")
    monkeypatch.delenv("HOME", raising=False)
    assert baseline == {
        combo: aggregate_overall_status(combo) for combo in _COMBINATIONS
    }
