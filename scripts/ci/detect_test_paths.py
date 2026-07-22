# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Change-aware test path resolution for omnibase_core CI."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from scripts.ci.test_selection_loader import (
    ModelAdjacencyMap,
    load_adjacency_map,
)
from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
    ModelTestSelection,
)

SRC_PREFIX = "src/omnibase_core/"
TEST_UNIT_PREFIX = "tests/unit/"
TEST_INTEGRATION_PREFIX = "tests/integration/"

FULL_SUITE_BRANCHES = {"main"}

# Positive-evidence documentation classification (OMN-14910, CI-C1 #3; ports the
# merged omnibase_infra#2372 / OMN-14753 approach). A path matching either of
# these can never contain executable code or fixture data, so it cannot influence
# any test outcome. This is narrower and STRONGER than the conservative
# "no unit-test mapping" tests/unit/ fallback in compute_selection: it only
# exempts a diff when EVERY changed file is affirmatively provable as
# prose/documentation, not merely unclassified. Deliberately does NOT include
# `.github/`, `.pre-commit-config.yaml`, or `scripts/hooks/`: core has
# workflow-shape unit tests (tests/unit/validation/test_occ_preflight_workflow_shape.py,
# test_receipt_gate_workflow_shape.py) whose outcome depends on those files, so a
# change there must still run the fallback rather than select nothing.
DOCS_ONLY_SUFFIXES = (".md",)
DOCS_ONLY_PREFIXES = ("docs/",)


def _is_docs_only_path(path: str) -> bool:
    """True when ``path`` is documentation that cannot affect any test outcome."""
    return path.endswith(DOCS_ONLY_SUFFIXES) or path.startswith(DOCS_ONLY_PREFIXES)


# pyproject.toml is handled content-aware (not as a bare path-prefix trigger).
# See classify_pyproject_dependency_relevant / step 2 in compute_selection.
PYPROJECT_PATH = "pyproject.toml"

# Keys under [project] whose change is metadata-only — it cannot alter dependency
# resolution, build inputs, or test behavior, so a diff confined to these must NOT
# escalate to the full suite. Everything else in pyproject.toml (the `dependencies`
# array, [project.optional-dependencies], [dependency-groups], [build-system],
# [tool.*] EXCEPT [tool.ruff.*] — see _PYPROJECT_SAFE_TOOL_KEYS —, requires-python)
# is treated as escalation-worthy. This is deliberately an allow-list of SAFE keys
# (not a block-list of dependency tables): an unrecognized/new pyproject key
# escalates by default, keeping the selector fail-closed.
_PYPROJECT_SAFE_PROJECT_KEYS = frozenset(
    {
        "version",
        "name",
        "description",
        "readme",
        "authors",
        "maintainers",
        "keywords",
        "classifiers",
        "urls",
        "license",
        "license-files",
        "entry-points",
        "scripts",
        "gui-scripts",
    }
)

# Keys under [tool] whose change is lint-only — it configures a static-analysis
# gate that runs as its OWN CI job (ruff), never the pytest suite, so it cannot
# change any test outcome (OMN-14910, CI-C1 #2). All 8 pyproject escalations in
# the 30-PR sample were a single added [tool.ruff.lint.per-file-ignores] entry —
# a lint-ignore line paying for a 40-way full suite. [tool.pytest.ini_options]
# and [tool.coverage] DELIBERATELY stay escalation-worthy (they change what/how
# tests run); only ruff is exempt. Fail-closed is preserved: a diff touching any
# other [tool.*] table, dependencies, or [build-system] still escalates, and an
# unparseable pyproject still escalates.
_PYPROJECT_SAFE_TOOL_KEYS = frozenset({"ruff"})

# Volume-aware split sizing (OMN-11026).
# Main-branch full-suite uses 40 splits over the whole tree (~1,500 test files,
# ~40K test items) and finishes within the 35-min job timeout. We match that
# density — roughly 40 test files per split — when smart-selection expands to
# large test directories. The path-count floor still keeps small PRs cheap.
VOLUME_TARGET_FILES_PER_SPLIT = 40
VOLUME_THRESHOLD_FILES = 80
VOLUME_MAX_SPLITS = 40

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_test_paths(
    changed_files: list[str],
    adjacency_path: Path,
) -> list[str]:
    """Map changed file paths to deterministic UNIT test directories.

    Behavior:
      - Source changes under src/omnibase_core/<module>: include
        tests/unit/<module>/.
      - Test-only changes under tests/unit/: include the changed unit-test directory.
      - Test-only changes under tests/integration/: ignored (integration runs always).
      - Files outside src/ and tests/unit/: no contribution; caller decides
        whether to escalate to full suite.

    Adjacency expansion is added in Task 5.
    """
    config = load_adjacency_map(adjacency_path)
    return _resolve(changed_files, config)


def _resolve(changed_files: list[str], config: ModelAdjacencyMap) -> list[str]:
    direct_modules: set[str] = set()
    selected: set[str] = set()

    for path in changed_files:
        if path.startswith(SRC_PREFIX):
            module = path[len(SRC_PREFIX) :].split("/", 1)[0]
            if module in config.adjacency:
                direct_modules.add(module)
        elif path.startswith(TEST_UNIT_PREFIX):
            parts = path.split("/")
            if len(parts) >= 3:
                selected.add(f"{TEST_UNIT_PREFIX}{parts[2]}/")

    expanded: set[str] = set(direct_modules)
    for module in direct_modules:
        expanded.update(config.adjacency[module].reverse_deps)

    for module in expanded:
        selected.add(f"{TEST_UNIT_PREFIX}{module}/")

    return sorted(selected)


def compute_selection(
    changed_files: list[str],
    adjacency_path: Path,
    ref_name: str,
    event_name: str = "pull_request",
    feature_flag_enabled: bool = True,
    pyproject_dependency_relevant: bool | None = None,
) -> ModelTestSelection:
    """Resolve the test selection for a change set.

    ``pyproject_dependency_relevant`` carries the content-aware classification of a
    ``pyproject.toml`` change (computed by the CLI via a base-vs-head TOML diff):
    ``True`` = a dependency-bearing table changed (escalate), ``False`` = the change
    is metadata-only (do not escalate on ``pyproject.toml`` alone), ``None`` = not
    classified. When ``pyproject.toml`` is in the change set and this is not
    ``False`` (i.e. ``True`` or ``None``), the selector fails closed and escalates.
    """
    config = load_adjacency_map(adjacency_path)

    # 0. Feature flag short-circuit: off → legacy 40-split full suite.
    if not feature_flag_enabled:
        return _full_suite(EnumFullSuiteReason.FEATURE_FLAG_OFF)

    # 1. Branch / event escalation.
    if ref_name in FULL_SUITE_BRANCHES:
        return _full_suite(EnumFullSuiteReason.MAIN_BRANCH)
    if event_name == "merge_group":
        return _full_suite(EnumFullSuiteReason.MERGE_GROUP)
    if event_name == "schedule":
        return _full_suite(EnumFullSuiteReason.SCHEDULED)

    # 2. Test infrastructure escalation.
    for changed in changed_files:
        if changed == PYPROJECT_PATH:
            # Content-aware: pyproject.toml escalates only when a dependency-bearing
            # table changed, OR when classification is unavailable (None) — fail
            # closed. A bare `version` bump / entry-point registration / metadata
            # edit must NOT force the full suite. `pyproject.toml` is intentionally
            # NOT in `test_infrastructure_paths` (it would be a bare path-prefix
            # trigger); it is handled here instead.
            if pyproject_dependency_relevant is None or pyproject_dependency_relevant:
                return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)
            continue
        if any(
            changed == infra or changed.startswith(infra.rstrip("/") + "/")
            for infra in config.test_infrastructure_paths
        ):
            return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)

    # 3. Shared module escalation.
    changed_modules = {
        path[len(SRC_PREFIX) :].split("/", 1)[0]
        for path in changed_files
        if path.startswith(SRC_PREFIX)
    } & set(config.adjacency.keys())
    if changed_modules & set(config.shared_modules):
        return _full_suite(EnumFullSuiteReason.SHARED_MODULE)

    # 4. Threshold escalation: too many distinct modules.
    if len(changed_modules) >= config.thresholds.modules_changed_for_full_suite:
        return _full_suite(EnumFullSuiteReason.THRESHOLD_MODULES)

    # 5. Docs-only exemption (OMN-14910, CI-C1 #3): a diff where EVERY changed
    # file is documentation cannot affect any test outcome, so select NOTHING
    # rather than falling through to the conservative tests/unit/ fallback below
    # (which runs ~94% of the tree). A single non-doc file anywhere in the diff —
    # including one this selector does not otherwise recognize — disqualifies the
    # exemption and falls through to normal smart-selection/fallback, so mixed or
    # ambiguous changes still run tests.
    if changed_files and all(_is_docs_only_path(p) for p in changed_files):
        return ModelTestSelection(
            selected_paths=[],
            split_count=1,
            is_full_suite=False,
            full_suite_reason=None,
            matrix=[1],
        )

    # 6. Smart selection.
    selected = _resolve(changed_files, config)
    if not selected:
        # Conservative one-shard fallback over the full tests/unit/ tree. This
        # is NOT a no-op — it runs ~3-5 min of unit tests. It fires for changes
        # that have no unit-test mapping (doc-only, integration-only, or other
        # low-signal metadata). CI workflow and selector changes are test
        # infrastructure and escalate before this fallback.
        selected = ["tests/unit/"]
    split_count = _split_count_for(selected, repo_root=REPO_ROOT)

    return ModelTestSelection(
        selected_paths=selected,
        split_count=split_count,
        is_full_suite=False,
        full_suite_reason=None,
        matrix=list(range(1, split_count + 1)),
    )


def _full_suite(reason: EnumFullSuiteReason) -> ModelTestSelection:
    return ModelTestSelection(
        selected_paths=["tests/"],
        split_count=40,
        is_full_suite=True,
        full_suite_reason=reason,
        matrix=list(range(1, 41)),
    )


def _split_count_for(selected_paths: list[str], repo_root: Path | None = None) -> int:
    """Volume-aware split count for a set of selected unit-test paths.

    Two signals combine:
      1. Path-count floor — the original heuristic; keeps small PRs cheap.
      2. Test-volume scaling — when expanded paths cover a large number of test
         files (e.g. mixins → models adjacency pulls in ~700 test files under
         tests/unit/models/), one-or-two splits cannot finish inside the
         ``test-parallel`` job timeout. Scale up to match main's ~1K-tests-per-
         split density (OMN-11026).

    The final split count is ``max(path_floor, volume_scaled)``, capped at
    ``VOLUME_MAX_SPLITS`` to match the main-branch full-suite shape.
    """
    path_floor = _path_count_floor(len(selected_paths))
    volume_scaled = _volume_split_count(selected_paths, repo_root)
    return min(max(path_floor, volume_scaled), VOLUME_MAX_SPLITS)


def _path_count_floor(n: int) -> int:
    """Original path-count heuristic, retained as a lower bound."""
    if n <= 2:
        return 1
    if n <= 5:
        return 2
    if n <= 10:
        return 3
    if n <= 16:
        return 4
    return 5


def _volume_split_count(selected_paths: list[str], repo_root: Path | None) -> int:
    """Count actual test files under selected paths and scale splits.

    Returns 0 when the test file count is below ``VOLUME_THRESHOLD_FILES`` —
    the caller then falls back to the path-count floor. When ``repo_root`` is
    None or the resolved directories don't exist (e.g. unit tests with a
    synthetic path list), this also returns 0.
    """
    if repo_root is None:
        return 0
    total = _count_test_files(selected_paths, repo_root)
    if total < VOLUME_THRESHOLD_FILES:
        return 0
    return math.ceil(total / VOLUME_TARGET_FILES_PER_SPLIT)


def _count_test_files(selected_paths: list[str], repo_root: Path) -> int:
    total = 0
    for rel in selected_paths:
        directory = repo_root / rel
        if not directory.is_dir():
            continue
        total += sum(1 for _ in directory.rglob("test_*.py"))
    return total


def _pyproject_without_safe_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Return the parsed pyproject with metadata-only / lint-only keys removed.

    Two revisions compare equal iff their escalation-worthy content — the
    ``dependencies`` array, ``[project.optional-dependencies]``,
    ``[dependency-groups]``, ``[build-system]``, every ``[tool.*]`` table EXCEPT
    ``[tool.ruff.*]``, ``requires-python``, and any other non-safe key — is
    identical. Only the metadata-only ``[project]`` keys in
    ``_PYPROJECT_SAFE_PROJECT_KEYS`` and the lint-only ``[tool]`` keys in
    ``_PYPROJECT_SAFE_TOOL_KEYS`` are stripped, so a diff confined to them does
    not escalate. ``[tool.pytest.ini_options]`` and ``[tool.coverage]`` are NOT
    stripped and still escalate.
    """
    reduced = dict(data)
    project = reduced.get("project")
    if isinstance(project, dict):
        reduced["project"] = {
            key: value
            for key, value in project.items()
            if key not in _PYPROJECT_SAFE_PROJECT_KEYS
        }
    tool = reduced.get("tool")
    if isinstance(tool, dict):
        reduced["tool"] = {
            key: value
            for key, value in tool.items()
            if key not in _PYPROJECT_SAFE_TOOL_KEYS
        }
    return reduced


def classify_pyproject_dependency_relevant(
    old_content: str | None,
    new_content: str | None,
) -> bool:
    """Classify whether a ``pyproject.toml`` change should escalate to the full suite.

    Returns ``True`` (escalate) when the change touches any escalation-worthy content
    OR cannot be proven metadata-only. Returns ``False`` (safe to narrow) only when
    both revisions parse as TOML and differ solely in metadata-only ``[project]``
    keys (``version``, ``entry-points``, ``scripts``, ``urls``, ``description``, …).

    Fail-closed by construction: missing base or head content, or a TOML parse
    failure, all return ``True``. This is a governed safety selector — it never
    narrows on ambiguity.
    """
    if old_content is None or new_content is None:
        return True
    try:
        old_data = tomllib.loads(old_content)
        new_data = tomllib.loads(new_content)
    except tomllib.TOMLDecodeError:
        return True
    return _pyproject_without_safe_keys(old_data) != _pyproject_without_safe_keys(
        new_data
    )


def _git_show(ref: str, rel_path: str, repo_root: Path) -> str | None:
    """Return the content of ``rel_path`` at ``ref`` via ``git show``, or None.

    None signals the caller to fail closed (the base revision could not be read —
    e.g. the ref is unfetched, or the file did not exist at the base).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _resolve_pyproject_dependency_relevant(
    base_ref: str | None,
    repo_root: Path,
) -> bool | None:
    """Classify the working-tree ``pyproject.toml`` against its ``base_ref`` revision.

    Returns ``None`` when classification is impossible (no base ref supplied, or the
    head file can't be read) so the caller escalates (fail closed). Otherwise returns
    the classifier's bool — which itself fails closed on parse/retrieval errors.
    """
    if not base_ref:
        return None
    try:
        new_content = (repo_root / PYPROJECT_PATH).read_text(encoding="utf-8")
    except OSError:
        return None
    old_content = _git_show(base_ref, PYPROJECT_PATH, repo_root)
    return classify_pyproject_dependency_relevant(old_content, new_content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve change-aware test paths")
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
        default=Path(__file__).parent / "test_selection_adjacency.yaml",
    )
    parser.add_argument(
        "--feature-flag",
        choices=("on", "off"),
        default="on",
        help="When 'off', emit a FEATURE_FLAG_OFF full-suite selection regardless of changed files.",
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(
            "Base git ref/SHA for content-aware pyproject.toml classification. When "
            "pyproject.toml is in the diff and this is omitted (or the base cannot be "
            "read), the selector fails closed and escalates to the full suite."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root used to read the working-tree pyproject.toml and run git show.",
    )
    args = parser.parse_args(argv)

    changed = [
        line.strip()
        for line in args.changed_files_from.read_text().splitlines()
        if line.strip()
    ]
    # Content-aware pyproject.toml classification (only when it is in the diff, to
    # avoid a spurious git call otherwise). None → compute_selection fails closed.
    pyproject_dependency_relevant: bool | None = None
    if PYPROJECT_PATH in changed:
        pyproject_dependency_relevant = _resolve_pyproject_dependency_relevant(
            args.base_ref, args.repo_root
        )
    selection = compute_selection(
        changed_files=changed,
        adjacency_path=args.adjacency,
        ref_name=args.ref_name,
        event_name=args.event_name,
        feature_flag_enabled=(args.feature_flag == "on"),
        pyproject_dependency_relevant=pyproject_dependency_relevant,
    )
    sys.stdout.write(selection.model_dump_json())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
