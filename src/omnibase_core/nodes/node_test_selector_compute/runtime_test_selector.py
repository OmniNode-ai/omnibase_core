# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the change-aware test selector — CI + pre-push entrypoint.

This is the stable entrypoint that the CI job and the pre-push hook
(``scripts/hooks/prepush_smart_tests.sh``) will invoke once the transparent
script→node swap follow-up lands (OMN-14700 DoD 2/3). It reproduces
``scripts/ci/detect_test_paths.py``'s stdout byte-for-byte for equivalent args —
a single ``ModelTestSelection.model_dump_json()`` line.

Boundary discipline (root CLAUDE.md rule #7a + the OMN-14694 no-I/O-outside-EFFECT
gate): every git-derived fact is resolved by the CALLER and passed in — the
changed-file list (``--changed-files-from``) and the ``pyproject.toml``
dependency-relevance classification (``--pyproject-relevant``). This mirrors the
repo's own CI convention (e.g. ``canonical-inference-gate.yml`` runs ``git show``
in the workflow step, then feeds a pure classifier), and keeps this COMPUTE node
package free of ``subprocess``/git. The one pure classifier the caller needs,
``classify_pyproject_dependency_relevant`` (in-memory TOML diff, no I/O), lives in
:mod:`.selector_core` for reuse.

The remaining boundary work here is read-only filesystem access the gate permits:
reading the changed-file list, loading the adjacency YAML, and counting
``test_*.py`` files. The pure ``NodeTestSelectorCompute`` handler receives only
typed data. Selection is resolved in two passes: pass 1 determines the selected
paths (independent of file volume), pass 2 counts ``test_*.py`` under exactly
those paths and re-runs the node to size the volume-aware split count — mirroring
the oracle, which computes ``selected`` first and then walks it.

Usage::

    python -m omnibase_core.nodes.node_test_selector_compute.runtime_test_selector \\
        --changed-files-from changed.txt --ref-name my-branch [--event-name pull_request] \\
        [--adjacency scripts/ci/test_selection_adjacency.yaml] [--feature-flag on] \\
        [--pyproject-relevant on|off] [--repo-root .]

Exit code: always 0 on a successful computation (the selection JSON is the product).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path

from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyMap,
)
from omnibase_core.models.nodes.test_selector.model_test_selection import (
    ModelTestSelection,
)
from omnibase_core.models.nodes.test_selector.model_test_selection_request import (
    ModelTestSelectionRequest,
)
from omnibase_core.nodes.node_test_selector_compute.handler import (
    NodeTestSelectorCompute,
)

__all__ = ["main"]

_DEFAULT_ADJACENCY_REL = "scripts/ci/test_selection_adjacency.yaml"

# --pyproject-relevant token -> the node's pyproject_dependency_relevant value.
# Absent (None) means "not classified" -> the node fails closed and escalates
# when pyproject.toml is in the diff.
_PYPROJECT_RELEVANT: dict[str, bool] = {"on": True, "off": False}

# OMN-15661 always-run set — mirrors the oracle's constants of the same names.
_TESTS_DIR = "tests"
_CLOSURE_NARROWABLE_TEST_ROOTS = frozenset({"unit"})
_SEPARATELY_GATED_ROOTS = frozenset({"integration"})
_TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")


def _load_adjacency(path: Path) -> ModelAdjacencyMap:
    """YAML read boundary — parse the static adjacency map into its typed model.

    Delegates to ``ModelAdjacencyMap.from_yaml_text``, which FAILS on a duplicate
    mapping key (OMN-14897) rather than silently last-wins — so the fail-closed
    guard runs on the node entrypoint as well as the legacy oracle.
    """
    return ModelAdjacencyMap.from_yaml_text(path.read_text(encoding="utf-8"))


def _count_test_files(rel_path: str, repo_root: Path) -> int:
    """Test-file count for one ``selected_paths`` entry (0 if absent).

    ``rel_path`` is either a directory (module-grain sentinel, e.g.
    ``tests/unit/`` -- walked recursively, matching BOTH
    ``_TEST_FILE_PATTERNS``: ``test_*.py`` and ``*_test.py``) or an individual
    test FILE (OMN-14921 file-grain closure output, e.g.
    ``tests/test_foo.py`` -- counted directly as 1, no walk needed). Mirrors
    the oracle's own ``scripts.ci.detect_test_paths._count_test_files``
    exactly, including its file branch.

    Two prior undercounts, both caught by the CLI stdout parity battery this
    module exists to hold honest:

    - Counting only the ``test_*.py`` half of the patterns while
      ``_contains_collectable_test`` admits both would let a directory be
      SELECTED on the strength of ``*_test.py`` files this function then
      does not count (the OMN-16917 oracle-side finding).
    - Checking only ``directory.is_dir()`` and returning 0 otherwise silently
      dropped every individual-file selection to 0 instead of 1 -- this repo
      has real top-level test files that are never inside a directory
      sentinel (``tests/test_db_ownership_subcontract.py`` and siblings),
      each undercounted by exactly 1 (OMN-16619).

    Both crossed the ``VOLUME_TARGET_FILES_PER_SPLIT`` rounding boundary on
    the real tree, emitting a ``split_count`` one lower than the oracle's for
    an identical selection -- reproducible only against CI's actual
    ``pull_request`` merge-ref tree (dev merged into the branch), not the
    branch tip alone.
    """
    target = repo_root / rel_path
    if target.is_dir():
        return sum(1 for f in target.rglob("*.py") if _is_test_file_name(f.name))
    if target.is_file():
        return 1
    return 0


def _is_test_file_name(name: str) -> bool:
    """True when pytest would collect a file with this name (``python_files``)."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in _TEST_FILE_PATTERNS)


def _raise_walk_error(error: OSError) -> None:
    raise error


def _contains_collectable_test(directory: Path) -> bool:
    for _root, _dirs, files in os.walk(directory, onerror=_raise_walk_error):
        if any(_is_test_file_name(name) for name in files):
            return True
    return False


def _unnarrowable_test_paths(repo_root: Path) -> list[str]:
    """Always-run test paths the import-graph closure cannot select (OMN-15661).

    Filesystem walk — this is the EFFECT boundary that owns it; the pure node
    receives the resolved list. Mirrors
    ``scripts.ci.detect_test_paths.unnarrowable_test_paths`` (the CI-governing
    oracle), which this module is required to reproduce byte-for-byte; the
    duplication is held honest by the CLI stdout parity battery in
    ``tests/unit/nodes/node_test_selector_compute/test_runtime_test_selector.py``,
    which runs BOTH entrypoints over the real repo root — the same arrangement
    already used for ``_count_test_files``.
    """
    tests_dir = repo_root / _TESTS_DIR
    if not tests_dir.is_dir():
        return []
    paths: list[str] = []
    for entry in sorted(tests_dir.iterdir()):
        name = entry.name
        if name in _CLOSURE_NARROWABLE_TEST_ROOTS or name in _SEPARATELY_GATED_ROOTS:
            continue
        if entry.is_dir():
            if _contains_collectable_test(entry):
                paths.append(f"{_TESTS_DIR}/{name}/")
        elif _is_test_file_name(name):
            paths.append(f"{_TESTS_DIR}/{name}")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="test-selector",
        description=(
            "Resolve change-aware test paths via the test_selector COMPUTE node "
            "(OMN-14700)."
        ),
    )
    parser.add_argument(
        "--changed-files-from",
        type=Path,
        required=True,
        help="Path to a file with one changed-file path per line.",
    )
    parser.add_argument("--ref-name", required=True)
    parser.add_argument("--event-name", default="pull_request")
    parser.add_argument(
        "--adjacency",
        type=Path,
        default=None,
        help=(f"Adjacency map YAML (default: <repo-root>/{_DEFAULT_ADJACENCY_REL})."),
    )
    parser.add_argument(
        "--feature-flag",
        choices=("on", "off"),
        default="on",
        help="When 'off', emit a FEATURE_FLAG_OFF full-suite selection regardless of changed files.",
    )
    parser.add_argument(
        "--pyproject-relevant",
        choices=("on", "off"),
        default=None,
        help=(
            "Caller-supplied content-aware classification of a pyproject.toml change "
            "('on' = a dependency-bearing table changed -> escalate; 'off' = "
            "metadata-only -> do not escalate on pyproject.toml alone). Compute it "
            "with selector_core.classify_pyproject_dependency_relevant over a base-vs-"
            "head diff at the git boundary. When pyproject.toml is in the diff and "
            "this is omitted, the selector fails closed and escalates."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root used to read the adjacency map and count test files "
        "(default: current working directory).",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    adjacency_path: Path = args.adjacency or (repo_root / _DEFAULT_ADJACENCY_REL)
    adjacency = _load_adjacency(adjacency_path)

    changed = [
        line.strip()
        for line in args.changed_files_from.read_text().splitlines()
        if line.strip()
    ]

    pyproject_dependency_relevant: bool | None = (
        _PYPROJECT_RELEVANT[args.pyproject_relevant]
        if args.pyproject_relevant is not None
        else None
    )

    node = NodeTestSelectorCompute()
    feature_flag_enabled = args.feature_flag == "on"

    # KNOWN GAP (OMN-14921 fast-follow, filed in the promotion PR body): this
    # EFFECT boundary does not yet compute the file-grain closure
    # (scripts.ci.test_selection_closure.compute_closure_selection) to inject as
    # closure_selected_files. Left None, the pure node fails closed to the
    # whole-tree fallback (never silently narrows on a missing closure) — this
    # entrypoint is not wired into CI (detect_test_paths.py is the governing
    # oracle), so the gap has no live-selection impact today.
    # OMN-15661: the always-run paths ARE resolved here — a tests/ directory walk
    # is read-only filesystem access this boundary already performs for
    # test-file counts, so there is no reason to leave the node failing closed.
    try:
        unnarrowable: list[str] | None = _unnarrowable_test_paths(repo_root)
    except OSError:  # boundary-ok: unreadable tests/ tree must fail closed
        # None -> the pure node escalates to the full suite, matching the
        # oracle's TEST_INFRASTRUCTURE escalation on the same failure.
        unnarrowable = None

    def _request(counts: dict[str, int]) -> ModelTestSelectionRequest:
        return ModelTestSelectionRequest(
            changed_files=changed,
            ref_name=args.ref_name,
            adjacency=adjacency,
            event_name=args.event_name,
            feature_flag_enabled=feature_flag_enabled,
            pyproject_dependency_relevant=pyproject_dependency_relevant,
            test_file_counts=counts,
            closure_selected_files=None,
            unnarrowable_test_paths=unnarrowable,
        )

    # Pass 1: selection (independent of test-file volume).
    prelim = node.handle(_request({}))

    # Pass 2: count test_*.py under exactly the selected paths and re-run so the
    # volume-aware split count matches the oracle. Full-suite selections have a
    # fixed 40-split shape, so counting is skipped there.
    if prelim.is_full_suite:
        selection: ModelTestSelection = prelim
    else:
        counts = {
            path: _count_test_files(path, repo_root) for path in prelim.selected_paths
        }
        selection = node.handle(_request(counts))

    sys.stdout.write(selection.model_dump_json())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
