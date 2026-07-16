# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI stdout parity: runtime_test_selector vs detect_test_paths (OMN-14700).

The follow-up (OMN-14700 DoD 2/3) will point the CI job and the pre-push hook at
``runtime_test_selector.main`` in place of ``detect_test_paths.main``. That swap
is only safe if the two entrypoints emit identical stdout for identical args.
This suite runs BOTH CLIs over the same change-sets, adjacency map, and repo root
and asserts the emitted ``ModelTestSelection`` JSON line is byte-for-byte equal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
    main as node_main,
)
from scripts.ci.detect_test_paths import main as oracle_main

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"

# Change-sets that need no git base-ref (no pyproject.toml classification), so the
# CLIs are pure functions of the working tree + args.
_CASES: list[tuple[str, list[str], list[str]]] = [
    ("single_module", ["src/omnibase_core/cli/foo.py"], ["--ref-name", "pr-branch"]),
    ("shared_module", ["src/omnibase_core/models/foo.py"], ["--ref-name", "pr-branch"]),
    ("test_infra", ["tests/conftest.py"], ["--ref-name", "pr-branch"]),
    ("empty", [], ["--ref-name", "pr-branch"]),
    ("main_branch", ["src/omnibase_core/cli/x.py"], ["--ref-name", "main"]),
    (
        "feature_flag_off",
        ["src/omnibase_core/cli/x.py"],
        ["--ref-name", "pr-branch", "--feature-flag", "off"],
    ),
    (
        "mixins_volume",
        ["src/omnibase_core/mixins/mixin_caching.py"],
        ["--ref-name", "pr-branch"],
    ),
    (
        "merge_group",
        ["src/omnibase_core/cli/x.py"],
        ["--ref-name", "pr-branch", "--event-name", "merge_group"],
    ),
]


def _changed_file(tmp_path: Path, changed: list[str]) -> Path:
    p = tmp_path / "changed.txt"
    p.write_text("\n".join(changed) + ("\n" if changed else ""))
    return p


@pytest.mark.parametrize(
    ("name", "changed", "extra"), _CASES, ids=[c[0] for c in _CASES]
)
def test_cli_stdout_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
    changed: list[str],
    extra: list[str],
) -> None:
    changed_file = _changed_file(tmp_path, changed)
    common = [
        "--changed-files-from",
        str(changed_file),
        "--adjacency",
        str(ADJ),
        "--repo-root",
        str(REPO_ROOT),
        *extra,
    ]

    oracle_rc = oracle_main(common)
    oracle_out = capsys.readouterr().out

    node_rc = node_main(common)
    node_out = capsys.readouterr().out

    assert oracle_rc == 0
    assert node_rc == 0
    assert node_out == oracle_out, {
        "case": name,
        "node": node_out,
        "oracle": oracle_out,
    }
    # Sanity: the emitted line is valid ModelTestSelection JSON.
    payload = json.loads(node_out)
    assert set(payload) == {
        "selected_paths",
        "split_count",
        "is_full_suite",
        "full_suite_reason",
        "matrix",
    }


def test_cli_emits_single_trailing_newline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changed_file = _changed_file(tmp_path, ["src/omnibase_core/cli/foo.py"])
    rc = node_main(
        [
            "--changed-files-from",
            str(changed_file),
            "--adjacency",
            str(ADJ),
            "--repo-root",
            str(REPO_ROOT),
            "--ref-name",
            "pr-branch",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert out.endswith("\n")
    assert not out.rstrip("\n").endswith("\n")  # exactly one trailing newline
