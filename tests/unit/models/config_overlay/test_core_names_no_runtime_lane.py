# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Core names no runtime lane and no lab host (OMN-19746, OMN-19745 AC1).

Operator ruling 2026-09-26 (firm): runtime lanes and their roles come from a
deployment overlay whoever runs the runtime supplies. This architecture ships
to customers who have no access to our lab, so omnibase_core must not compile
our lane names or our lab hosts into code.

The check reads string constants in executable code. Docstrings, comments and
prose strings (any constant holding whitespace, such as a field description)
are history, not behaviour; a lane id or a host address a program compares
against, collects or connects to is a single token. The lane ids below are the ones our lab uses
today, listed here and nowhere else in core so this test can recognise them.
A new customer lane needs no entry: the point is that core names none.

The baseline is the two files that predate the ruling. Each carries the task
that removes it; the baseline only shrinks.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[4] / "src" / "omnibase_core"

# Our lab's lane ids and host address prefix. Test data, never product code.
_LAB_LANE_OR_HOST = re.compile(
    r"\b(?:compose-dev(?:-\d+)?|stability-test|onex-lab(?:-k3s)?|sim-\d+|"
    r"dev-\d{3}|prepr-\d+|dogfood|judge)\b|192\.168\.86\."
)

_PROSE = re.compile(r"\s")

# Files allowed to hold a lane literal, and the task that empties each one.
_BASELINE: dict[str, str] = {
    # REGISTERED_RUNTIME_LANES / LAB_RUNTIME_LANES: deleted by LO10 (OMN-19754).
    "constants/constants_runtime_lanes.py": "OMN-19754",
    # The deploy-request stage vocabulary of the prod promotion gate (dev,
    # stability-test, prod): out of scope of the ruling, plan section 10.
    "enums/enum_runtime_lane.py": "plan section 10",
}


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _lane_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_nodes(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and not _PROSE.search(node.value)
            and _LAB_LANE_OR_HOST.search(node.value)
        ):
            hits.append(f"{node.lineno}:{node.value[:60]!r}")
    return hits


def _findings() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(_SRC.rglob("*.py")):
        hits = _lane_literals(path)
        if hits:
            found[path.relative_to(_SRC).as_posix()] = hits
    return found


def test_core_code_names_no_runtime_lane_or_lab_host() -> None:
    new = {path: hits for path, hits in _findings().items() if path not in _BASELINE}
    assert not new, (
        "omnibase_core code names a runtime lane or a lab host. Lanes and their "
        "roles come from the deployment's runtime.lane overlay document "
        f"(OMN-19745); core names none: {new}"
    )


def test_the_baseline_only_shrinks() -> None:
    stale = sorted(set(_BASELINE) - set(_findings()))
    assert not stale, f"remove these from _BASELINE, they are clean now: {stale}"


def test_the_check_sees_a_lane_literal() -> None:
    # Positive control: an empty result must be able to be non-empty.
    tree_hits = _lane_literals(_SRC / "constants" / "constants_runtime_lanes.py")
    assert tree_hits
