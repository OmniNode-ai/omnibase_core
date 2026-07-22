# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure change-aware test-selection algorithm (OMN-14700).

Verbatim port of the deterministic logic in ``scripts/ci/detect_test_paths.py``
into the canonical node layer, with ONE structural change required for purity:
the volume-aware split count takes a caller-supplied ``test_file_counts`` map
instead of walking the filesystem. Every escalation branch, its ordering, the
path-count floor, and the ceil/threshold/cap arithmetic are unchanged, so this
module reproduces the oracle byte-for-byte (proven by the differential test
battery in ``tests/unit/nodes/node_test_selector_compute/``).

No I/O, no clock, no global state — safe to run inside a COMPUTE handler.
``detect_test_paths.py`` remains the frozen reference oracle until the CI +
pre-push swap follow-up (OMN-14700 DoD 2/3) deletes it.
"""

from __future__ import annotations

import math
import tomllib

from omnibase_core.enums.enum_full_suite_reason import EnumFullSuiteReason
from omnibase_core.models.nodes.test_selector.model_adjacency_map import (
    ModelAdjacencyMap,
)
from omnibase_core.models.nodes.test_selector.model_test_selection import (
    ModelTestSelection,
)

__all__ = [
    "PYPROJECT_PATH",
    "VOLUME_MAX_SPLITS",
    "VOLUME_TARGET_FILES_PER_SPLIT",
    "VOLUME_THRESHOLD_FILES",
    "classify_pyproject_dependency_relevant",
    "compute_selection",
    "path_count_floor",
    "resolve_test_paths",
    "split_count_from_total",
    "volume_split_from_total",
]

SRC_PREFIX = "src/omnibase_core/"
TEST_UNIT_PREFIX = "tests/unit/"

FULL_SUITE_BRANCHES = frozenset({"main"})

# Positive-evidence documentation classification (OMN-14910, CI-C1 #3; mirrors
# the oracle in scripts/ci/detect_test_paths.py and the merged
# omnibase_infra#2372 / OMN-14753 approach). A path matching either of these can
# never contain executable code or fixture data, so it cannot influence any test
# outcome. Narrower and STRONGER than the conservative tests/unit/ fallback: it
# only exempts a diff when EVERY changed file is affirmatively docs. Deliberately
# excludes `.github/`, `.pre-commit-config.yaml`, and `scripts/hooks/` — core has
# workflow-shape unit tests whose outcome depends on those files.
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
# [tool.*] EXCEPT [tool.ruff.*] (see _PYPROJECT_SAFE_TOOL_KEYS) — including
# [tool.pytest.ini_options]/[tool.coverage] —, requires-python)
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

# Lint-only [tool] keys (OMN-14910, CI-C1 #2): a change confined to [tool.ruff.*]
# configures the ruff static-analysis gate (its own CI job), never the pytest
# suite, so it cannot change a test outcome. [tool.pytest.ini_options] and
# [tool.coverage] deliberately stay escalation-worthy; only ruff is exempt.
_PYPROJECT_SAFE_TOOL_KEYS = frozenset({"ruff"})

# Volume-aware split sizing (OMN-11026). Match main's ~40-files-per-split density
# when smart-selection expands into large test directories; the path-count floor
# still keeps small PRs cheap.
VOLUME_TARGET_FILES_PER_SPLIT = 40
VOLUME_THRESHOLD_FILES = 80
VOLUME_MAX_SPLITS = 40


def resolve_test_paths(
    changed_files: list[str],
    config: ModelAdjacencyMap,
) -> list[str]:
    """Map changed file paths to deterministic UNIT test directories.

    Behavior:
      - Source changes under src/omnibase_core/<module>: include
        tests/unit/<module>/ plus the module's reverse-dep expansion.
      - Test-only changes under tests/unit/: include the changed unit-test directory.
      - Test-only changes under tests/integration/: ignored (integration runs always).
      - Files outside src/ and tests/unit/: no contribution; the caller decides
        whether to escalate to the full suite.
    """
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
    adjacency: ModelAdjacencyMap,
    ref_name: str,
    event_name: str = "pull_request",
    feature_flag_enabled: bool = True,
    pyproject_dependency_relevant: bool | None = None,
    test_file_counts: dict[str, int] | None = None,
) -> ModelTestSelection:
    """Resolve the test selection for a change set — pure, deterministic.

    ``pyproject_dependency_relevant`` carries the content-aware classification of a
    ``pyproject.toml`` change (see ``classify_pyproject_dependency_relevant``):
    ``True`` = a dependency-bearing table changed (escalate), ``False`` = the change
    is metadata-only (do not escalate on ``pyproject.toml`` alone), ``None`` = not
    classified. When ``pyproject.toml`` is in the change set and this is not
    ``False`` (i.e. ``True`` or ``None``), the selector fails closed and escalates.

    ``test_file_counts`` maps a selected test path to the recursive count of
    ``test_*.py`` files beneath it (computed by the caller/EFFECT boundary). It is
    consulted only on the smart-selection path to size the split count; an absent
    entry counts as ``0`` (mirrors the oracle's skip-if-missing directory).
    """
    counts = test_file_counts or {}

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
            # edit must NOT force the full suite.
            if pyproject_dependency_relevant is None or pyproject_dependency_relevant:
                return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)
            continue
        if any(
            changed == infra or changed.startswith(infra.rstrip("/") + "/")
            for infra in adjacency.test_infrastructure_paths
        ):
            return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)

    # 3. Shared module escalation.
    changed_modules = {
        path[len(SRC_PREFIX) :].split("/", 1)[0]
        for path in changed_files
        if path.startswith(SRC_PREFIX)
    } & set(adjacency.adjacency.keys())
    if changed_modules & set(adjacency.shared_modules):
        return _full_suite(EnumFullSuiteReason.SHARED_MODULE)

    # 4. Threshold escalation: too many distinct modules.
    if len(changed_modules) >= adjacency.thresholds.modules_changed_for_full_suite:
        return _full_suite(EnumFullSuiteReason.THRESHOLD_MODULES)

    # 5. Docs-only exemption (OMN-14910, CI-C1 #3): a diff where EVERY changed
    # file is documentation cannot affect any test outcome, so select NOTHING
    # rather than falling through to the conservative tests/unit/ fallback below.
    # A single non-doc file (including an unrecognized one) disqualifies the
    # exemption and falls through, so mixed/ambiguous changes still run tests.
    if changed_files and all(_is_docs_only_path(p) for p in changed_files):
        return ModelTestSelection(
            selected_paths=[],
            split_count=1,
            is_full_suite=False,
            full_suite_reason=None,
            matrix=[1],
        )

    # 6. Smart selection.
    selected = resolve_test_paths(changed_files, adjacency)
    if not selected:
        # Conservative one-shard fallback over the full tests/unit/ tree. NOT a
        # no-op — it runs the unit suite for changes with no unit-test mapping
        # (integration-only, low-signal metadata not provably docs-only).
        selected = ["tests/unit/"]
    total = sum(counts.get(path, 0) for path in selected)
    split_count = split_count_from_total(selected, total)

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


def split_count_from_total(selected_paths: list[str], total_test_files: int) -> int:
    """Volume-aware split count for a set of selected unit-test paths.

    Combines the path-count floor (keeps small PRs cheap) with test-volume scaling
    (a large expanded selection needs enough splits to fit the job timeout). The
    final value is ``max(path_floor, volume_scaled)`` capped at ``VOLUME_MAX_SPLITS``
    — identical to the oracle's ``_split_count_for``, but the file total is supplied
    rather than walked.
    """
    path_floor = path_count_floor(len(selected_paths))
    volume_scaled = volume_split_from_total(total_test_files)
    return min(max(path_floor, volume_scaled), VOLUME_MAX_SPLITS)


def path_count_floor(n: int) -> int:
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


def volume_split_from_total(total_test_files: int) -> int:
    """Scale splits by the number of selected test files.

    Returns 0 when the count is below ``VOLUME_THRESHOLD_FILES`` — the caller then
    falls back to the path-count floor. Mirrors the oracle's ``_volume_split_count``
    (which returns 0 for a synthetic/absent path list), with the total supplied
    instead of walked.
    """
    if total_test_files < VOLUME_THRESHOLD_FILES:
        return 0
    return math.ceil(total_test_files / VOLUME_TARGET_FILES_PER_SPLIT)


def _pyproject_without_safe_keys(data: dict[str, object]) -> dict[str, object]:
    """Return the parsed pyproject with metadata-only / lint-only keys removed.

    Strips the metadata-only ``[project]`` keys in ``_PYPROJECT_SAFE_PROJECT_KEYS``
    and the lint-only ``[tool]`` keys in ``_PYPROJECT_SAFE_TOOL_KEYS`` (``ruff``),
    so a diff confined to them does not escalate. ``[tool.pytest.ini_options]`` and
    ``[tool.coverage]`` are NOT stripped and still escalate.
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
    failure, all return ``True``. Pure — parses in-memory strings, no file I/O.
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
