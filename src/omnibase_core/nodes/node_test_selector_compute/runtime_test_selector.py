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
import sys
from pathlib import Path

import yaml

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


def _load_adjacency(path: Path) -> ModelAdjacencyMap:
    """YAML read boundary — parse the static adjacency map into its typed model."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ModelAdjacencyMap.model_validate(raw)


def _count_test_files(rel_path: str, repo_root: Path) -> int:
    """Recursive ``test_*.py`` count beneath ``repo_root / rel_path`` (0 if absent)."""
    directory = repo_root / rel_path
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.rglob("test_*.py"))


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

    def _request(counts: dict[str, int]) -> ModelTestSelectionRequest:
        return ModelTestSelectionRequest(
            changed_files=changed,
            ref_name=args.ref_name,
            adjacency=adjacency,
            event_name=args.event_name,
            feature_flag_enabled=feature_flag_enabled,
            pyproject_dependency_relevant=pyproject_dependency_relevant,
            test_file_counts=counts,
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
