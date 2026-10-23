# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: keep every workflow and action runs-on value on one line.

The omninode_infra private-repo-runner-placement gate pinned at 9d4b381d
cannot parse a folded multi-line runs-on, so every runs-on under
.github/workflows and .github/actions is written on one line.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
YAML_FILES = sorted(
    path
    for directory in ("workflows", "actions")
    for pattern in ("*.yml", "*.yaml")
    for path in (REPO_ROOT / ".github" / directory).rglob(pattern)
)
_RUNS_ON = re.compile(r"^\s*runs-on:\s*(?P<rest>.*)$")


def _folded_runs_on_lines(text: str) -> list[int]:
    offenders: list[int] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _RUNS_ON.match(line)
        if match is None:
            continue
        rest = match.group("rest").strip()
        if not rest.startswith(("'", '"')):
            rest = rest.split("#", 1)[0].strip()
        if not rest or rest.startswith((">", "|")):
            offenders.append(lineno)
    return offenders


def test_all_workflow_and_action_runs_on_values_are_on_one_line() -> None:
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{lineno}"
        for path in YAML_FILES
        for lineno in _folded_runs_on_lines(path.read_text(encoding="utf-8"))
    ]

    assert not offenders, "runs-on values must be on one line:\n" + "\n".join(offenders)


def test_runs_on_scan_and_receipt_gate_have_positive_controls() -> None:
    runs_on_lines = [
        line
        for path in YAML_FILES
        for line in path.read_text(encoding="utf-8").splitlines()
        if _RUNS_ON.match(line)
    ]
    assert runs_on_lines, "expected at least one runs-on line in workflows or actions"

    receipt_gate = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
    receipt_runner_values = [
        match.group("rest")
        for line in receipt_gate.read_text(encoding="utf-8").splitlines()
        if (match := _RUNS_ON.match(line)) and not _folded_runs_on_lines(line)
    ]
    assert (
        sum(
            "fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON)" in value
            and "'ubuntu-latest'" in value
            for value in receipt_runner_values
        )
        >= 2
    ), "expected at least two one-line private/public receipt-gate runner expressions"


def test_folded_runs_on_detector_rejects_multiline_and_accepts_inline() -> None:
    assert _folded_runs_on_lines("    runs-on: >-\n      ${{ x }}\n") == [1]
    assert _folded_runs_on_lines("    runs-on: ubuntu-latest\n") == []
