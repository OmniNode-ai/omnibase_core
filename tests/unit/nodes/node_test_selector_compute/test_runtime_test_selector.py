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
    _TEST_FILE_PATTERNS as RUNTIME_TEST_FILE_PATTERNS,
)
from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
    main as node_main,
)
from scripts.ci.detect_test_paths import TEST_FILE_PATTERNS as ORACLE_TEST_FILE_PATTERNS
from scripts.ci.detect_test_paths import main as oracle_main
from scripts.ci.detect_test_paths import unnarrowable_test_paths

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
    assert RUNTIME_TEST_FILE_PATTERNS == ORACLE_TEST_FILE_PATTERNS

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
    # under-selection — the fallback is conservative, never narrower). The
    # always-run paths (OMN-15661) are present on BOTH sides: unlike the
    # closure, this EFFECT boundary does resolve them, so the divergence stays
    # confined to the closure gap.
    assert node_payload["is_full_suite"] is False
    assert node_payload["selected_paths"] == [
        "tests/unit/",
        *unnarrowable_test_paths(REPO_ROOT),
    ]
    for path in unnarrowable_test_paths(REPO_ROOT):
        assert path in oracle_payload["selected_paths"]

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


def test_always_run_derivations_agree_between_the_two_surfaces() -> None:
    """OMN-15661: the oracle and this EFFECT boundary derive the SAME set.

    `runtime_test_selector.py` cannot import `scripts/ci/` (src must not depend
    on the CI scripts tree), so the walk exists twice — the same arrangement
    already used for `_count_test_files`. This asserts the two copies agree on
    the real tree directly, rather than leaving it implied by the stdout parity
    cases above, and it fails the moment one side learns a rule the other has
    not.
    """
    from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
        _unnarrowable_test_paths,
    )

    derived = _unnarrowable_test_paths(REPO_ROOT)
    assert derived == unnarrowable_test_paths(REPO_ROOT)
    assert "tests/gates/" in derived


def test_node_split_count_counts_every_configured_test_filename_pattern(
    tmp_path: Path,
) -> None:
    """OMN-16619: this node's volume counter must match the oracle's fix.

    OMN-16917 fixed ``scripts.ci.detect_test_paths._count_test_files`` to count
    BOTH ``TEST_FILE_PATTERNS`` (``test_*.py`` and ``*_test.py``), not just the
    ``test_*.py`` half — see
    ``tests/unit/scripts/ci/test_detect_test_paths_ci_contract_omn16917.py::
    test_split_count_counts_every_configured_test_filename_pattern``, which this
    test mirrors. That fix was never ported to this node's own
    ``_count_test_files`` copy, so the two "byte-for-byte" implementations
    silently diverged: on a real tree large enough for the undercount to cross
    a split-count rounding boundary, ``node_main`` and ``oracle_main`` emit
    different ``split_count`` values for the identical selection — caught by
    ``test_cli_stdout_parity`` failing on CI's checked-out tree (39 vs 40) while
    passing locally (below the boundary on a smaller/differently-shaped local
    tree). Asserted against the counter directly so the invariant holds
    regardless of which patterns happen to be populated in the live tree today.
    """
    from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
        _count_test_files as node_count_test_files,
    )
    from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
        _is_test_file_name,
    )

    suite = tmp_path / "tests" / "suite"
    suite.mkdir(parents=True)
    (suite / "test_prefix_style.py").write_text("def test_a() -> None: ...\n")
    (suite / "suffix_style_test.py").write_text("def test_b() -> None: ...\n")
    (suite / "helper.py").write_text("VALUE = 1\n")

    assert node_count_test_files("tests/suite", tmp_path) == 2
    assert _is_test_file_name("suffix_style_test.py") is True
    assert _is_test_file_name("helper.py") is False


def test_node_count_test_files_counts_an_individual_file_path(
    tmp_path: Path,
) -> None:
    """OMN-16619: a ``selected_paths`` entry can be a single FILE, not just a
    directory — the OMN-14921 file-grain closure selects individual test files
    directly (e.g. ``tests/test_foo.py``), and this repo has real top-level
    test files that are never inside a directory sentinel (measured live:
    ``tests/test_db_ownership_subcontract.py``,
    ``tests/test_direct_instantiation_danger.py``,
    ``tests/test_json_serialization_crash.py``).

    The oracle's ``scripts.ci.detect_test_paths._count_test_files`` handles
    this explicitly (``elif target.is_file(): total += 1``). This node's
    per-path twin only ever checked ``directory.is_dir()`` and returned 0 for
    anything else — silently undercounting every individual-file selection by
    1. On the real tree this crossed the ``VOLUME_TARGET_FILES_PER_SPLIT``
    rounding boundary by exactly the 3 top-level test files above (oracle
    total 1561 -> split_count 40, node total 1558 -> split_count 39),
    reproduced via a scratch merge of this branch with ``origin/dev`` (the
    actual tree CI's ``pull_request`` merge-ref checks out) — this unit test
    pins the underlying per-path defect directly, independent of which files
    happen to sit at the tree's rounding boundary today.

    Verified failing pre-fix: ``node_count_test_files(...) == 0``.
    """
    from omnibase_core.nodes.node_test_selector_compute.runtime_test_selector import (
        _count_test_files as node_count_test_files,
    )

    lone_file = tmp_path / "tests" / "test_lone.py"
    lone_file.parent.mkdir(parents=True)
    lone_file.write_text("def test_a() -> None: ...\n")

    assert node_count_test_files("tests/test_lone.py", tmp_path) == 1
    assert node_count_test_files("tests/does_not_exist.py", tmp_path) == 0
