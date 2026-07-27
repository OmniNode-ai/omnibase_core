# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI stdout parity: runtime_test_selector vs detect_test_paths (OMN-14700).

The follow-up (OMN-14700 DoD 2/3) will point the CI job and the pre-push hook at
``runtime_test_selector.main`` in place of ``detect_test_paths.main``. That swap
is only safe if the two entrypoints emit identical stdout for identical args.
This suite runs BOTH CLIs over the same change-sets, adjacency map, and repo root
and asserts the emitted ``ModelTestSelection`` JSON line is byte-for-byte equal —
EXCEPT for the ONE known, documented gap (OMN-14921): ``runtime_test_selector.py``
does not yet compute the file-grain import-graph closure (grimp graph build +
AST reads are I/O, and this EFFECT boundary hasn't been wired to call
``test_selection_closure.compute_closure_selection`` — filed as a fast-follow
in the OMN-14921 PR body). Every case that resolves via an ESCALATION gate
(shared_module, test_infra, main_branch, feature_flag_off, merge_group, or a
changed file the closure itself fails closed on) is unaffected and stays
byte-for-byte. The one case that reaches real closure narrowing on the oracle
side (a real, resolvable source file) is split out below into
``test_cli_stdout_diverges_on_smart_selection_pending_closure_wiring``, which
asserts the divergence explicitly rather than silently dropping coverage.
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


def test_cli_stdout_diverges_on_smart_selection_pending_closure_wiring(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Documents the ONE known gap (OMN-14921 fast-follow): a real, resolvable
    source-file change narrows via the real closure on the oracle side, but
    ``runtime_test_selector.py`` does not yet compute+inject that closure, so
    it fails closed to the whole-tree sentinel. This asserts the divergence
    explicitly — a silently-passing byte-for-byte comparison here would be a
    false green masking the gap, not a proof it doesn't exist."""
    changed_file = _changed_file(
        tmp_path, ["src/omnibase_core/mixins/mixin_caching.py"]
    )
    common = [
        "--changed-files-from",
        str(changed_file),
        "--adjacency",
        str(ADJ),
        "--repo-root",
        str(REPO_ROOT),
        "--ref-name",
        "pr-branch",
    ]

    oracle_rc = oracle_main(common)
    oracle_out = capsys.readouterr().out
    node_rc = node_main(common)
    node_out = capsys.readouterr().out

    assert oracle_rc == 0
    assert node_rc == 0
    oracle_payload = json.loads(oracle_out)
    node_payload = json.loads(node_out)

    # Oracle: real closure narrowing (strictly fewer than the whole tree).
    assert oracle_payload["is_full_suite"] is False
    assert oracle_payload["selected_paths"] != ["tests/unit/"]
    assert any(
        p.startswith("tests/unit/mixins/") for p in oracle_payload["selected_paths"]
    )

    # Node: fails closed to the whole-tree sentinel (documented gap, not silent
    # under-selection — the fallback is conservative, never narrower).
    assert node_payload["is_full_suite"] is False
    assert node_payload["selected_paths"] == ["tests/unit/"]

    assert node_out != oracle_out


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
