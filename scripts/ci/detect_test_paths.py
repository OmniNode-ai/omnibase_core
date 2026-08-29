# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Change-aware test path resolution for omnibase_core CI."""

from __future__ import annotations

import argparse
import fnmatch
import math
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from scripts.ci.test_selection_closure import compute_closure_selection
from scripts.ci.test_selection_loader import (
    load_adjacency_map,
)
from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
    ModelTestSelection,
)

SRC_PREFIX = "src/omnibase_core/"
TEST_UNIT_PREFIX = "tests/unit/"
TEST_INTEGRATION_PREFIX = "tests/integration/"
REQUIRED_CHECKS_MANIFEST_PATH = ".github/required-checks.yaml"
REQUIRED_CHECKS_MANIFEST_TEST = (
    "tests/unit/validation/test_required_check_skip_guard.py"
)

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
# change there must still run the fallback rather than select nothing. The
# required-check manifest has a positive mapping below because otherwise the
# generic import-graph closure cannot resolve it and falls back to all unit tests.
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

# --- Unnarrowable test paths (OMN-15661) -----------------------------------
# The import-graph closure narrows WITHIN `tests/unit/`: that is the only tree
# `compute_closure_selection` collects candidates from. `tests/integration/` is
# excluded because it has its own unconditional CI job (ci.yml `tests-integration`,
# and both pytest steps pass `--ignore=tests/integration`). EVERY OTHER test path
# the full-suite step runs (`pytest tests/`) — `tests/gates/`, `tests/validation/`,
# `tests/scripts/`, the loose `tests/test_*.py` files, and whatever lands
# tomorrow — is outside the closure's candidate universe and can therefore never
# appear in a narrowed selection, no matter what changed.
#
# That is fail-OPEN, and it was live: the OMN-15639 AC3 gate
# (`tests/gates/test_consumer_group_name_authorization.py`) was collected ZERO
# times on the everyday narrowed dev path, so a PR reintroducing the exact
# consumer-group defect literal it guards would have passed narrowed CI
# (OMN-15661). The closure cannot fix this by widening its candidate set either:
# that gate's relationship to a source change is not an import edge at all — it
# AST-scans every file under `src/` off disk, an edge no import graph models.
#
# So these paths are ALWAYS selected alongside the closure's answer whenever the
# selection is narrowed and non-empty. The only exemption stays the docs-only
# selection (step 5), which is positively proven to be able to affect nothing.
#
# The set is DERIVED from the tree, never hand-listed: a new `tests/<dir>/` is
# covered the day it lands, with nobody having to remember a list — the same
# default-deny posture the rest of this selector is built on.
TESTS_DIR = "tests"

# Roots deliberately NOT treated as unnarrowable, each for a proven reason.
CLOSURE_NARROWABLE_TEST_ROOTS = frozenset({"unit"})  # the closure's own universe
SEPARATELY_GATED_TEST_ROOTS = frozenset({"integration"})  # own unconditional job

# Mirrors `[tool.pytest.ini_options] python_files` in pyproject.toml. Held equal
# by tests/unit/scripts/ci/test_detect_test_paths.py, which reads that key — so
# widening pytest's collection patterns without widening this fails a test rather
# than silently dropping a newly-collectable family from the narrowed path.
TEST_FILE_PATTERNS = ("test_*.py", "*_test.py")

# --- CI-contract test class for `.github/**` diffs (OMN-16917) --------------
# Applies the OMN-16745 ruling — written up in omnibase_infra
# `docs/reference/selector-workflow-diff-ruling.md`, landed as
# omnibase_infra#2988 (95fb95837) — to THIS repo's selector, which is a
# different design (the OMN-14921 import-graph closure, not infra's static
# reverse-dependency map) and was not touched by that PR.
#
# The ruling: for a `.github/**` diff the necessary and sufficient proof is the
# CI-contract class — the tests that read `.github/**` off disk and assert its
# contents — plus any test module the diff itself touches. The unit suite is
# neither necessary nor sufficient: no test under `tests/unit/` that never reads
# `.github/**` has an outcome a workflow YAML edit can change, so escalating to
# it is cost without proof.
#
# What it cost here, measured live: the real OMN-16625 diff in this repo
# (.github/required-checks.yaml + .github/workflows/ci.yml + three
# tests/unit/validation modules) resolved to `split_count=39` with
# `selected_paths` containing the whole `tests/unit/` tree (1,478 collectable
# files). `.github/**` is unresolvable to `resolve_changed_src_modules`, and any
# unresolvable path fails the WHOLE selection closed to the `["tests/unit/"]`
# sentinel — a whole-suite-equivalent selection carrying `is_full_suite=False`,
# exactly the shape the pre-push hook's OMN-15408 `selection_is_whole_suite`
# predicate routes into the OMN-15059 / OMN-16295 host-load guard. That is how
# OMN-16346 and OMN-16625 got stranded in omnibase_infra.
#
# The class may never select NOTHING (OMN-15541): a workflow edit breaks the
# ENFORCEMENT of tests rather than the tests themselves — there, `ci.yml`
# hardcoded a pytest root the selector and pyproject did not name, so full-suite
# escalation itself collected ZERO of the top-level `tests/` tree and no Python
# test failed to say so. An empty or unenumerable class therefore escalates.
#
# The membership is DERIVED from the tree, never hand-listed — the same posture
# as `unnarrowable_test_paths` above: a new workflow-shape test joins the class
# the day it lands, with nobody having to remember a list.
CI_CONTRACT_TEST_ROOT = "tests/ci/"
CI_CONTRACT_MARKER = ".github"
GITHUB_DIR_PREFIX = ".github/"


def is_test_file_name(name: str) -> bool:
    """True when pytest would collect a file with this name (``python_files``)."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in TEST_FILE_PATTERNS)


def _raise_walk_error(error: OSError) -> None:
    raise error


def _contains_collectable_test(directory: Path) -> bool:
    """True when ``directory`` holds at least one file pytest would collect.

    Keeps genuinely test-free directories (``tests/fixtures/``, ``__pycache__``)
    out of the always-run set on POSITIVE evidence — there is nothing in them to
    run — rather than by naming them in an exclusion list that would rot.
    """
    for _root, _dirs, files in os.walk(directory, onerror=_raise_walk_error):
        if any(is_test_file_name(name) for name in files):
            return True
    return False


def unnarrowable_test_paths(repo_root: Path) -> list[str]:
    """Test paths the full suite runs that the closure cannot reason about.

    Everything directly under ``tests/`` that holds collectable tests, minus the
    closure's own universe (``tests/unit/``) and the separately-gated
    ``tests/integration/``. See the block comment on
    :data:`CLOSURE_NARROWABLE_TEST_ROOTS` for why these must always run.

    Raises ``OSError`` when the tree cannot be enumerated — the caller escalates
    to the full suite rather than emitting a selection it cannot prove covers
    them.
    """
    tests_dir = repo_root / TESTS_DIR
    if not tests_dir.is_dir():
        # No tests/ tree at all (synthetic fixture roots): nothing is being
        # dropped, so there is nothing to force. Distinct from "cannot read".
        return []
    paths: list[str] = []
    for entry in sorted(tests_dir.iterdir()):
        name = entry.name
        if name in CLOSURE_NARROWABLE_TEST_ROOTS or name in SEPARATELY_GATED_TEST_ROOTS:
            continue
        if entry.is_dir():
            if _contains_collectable_test(entry):
                paths.append(f"{TESTS_DIR}/{name}/")
        elif is_test_file_name(name):
            paths.append(f"{TESTS_DIR}/{name}")
    return paths


def _with_unnarrowable(selected: list[str], unnarrowable: list[str]) -> list[str]:
    """Union a narrowed selection with the always-run paths, order-stable."""
    return [*selected, *[path for path in unnarrowable if path not in selected]]


def _dedup(paths: list[str]) -> list[str]:
    """Order-stable de-duplication."""
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def ci_contract_test_paths(repo_root: Path) -> list[str]:
    """The CI-contract class: tests whose outcome depends on ``.github/**``.

    Two positively-evidenced sources, both derived from the tree (see the block
    comment on :data:`CI_CONTRACT_TEST_ROOT`):

    * ``tests/ci/`` — the positively-named CI-contract root, included whenever
      it holds at least one collectable test.
    * every collectable test module under ``tests/unit/`` whose source
      references ``.github`` — i.e. reads the workflow / required-check files
      off disk and asserts their contents. These are the only ``tests/unit/``
      modules a ``.github/**`` edit can change the outcome of, and the closure
      cannot find them because the edge is a filesystem read, not an import.

    A candidate that cannot be read is KEPT, not dropped: the class never
    shrinks on an unproven negative. ``OSError`` propagates when the tree itself
    cannot be enumerated — the caller escalates rather than emit a class it
    cannot prove is complete.

    Returns ``[]`` only when this tree genuinely holds no CI-contract proof; the
    caller must then escalate (OMN-15541 — the class may never select nothing).
    """
    paths: list[str] = []

    ci_root = repo_root / CI_CONTRACT_TEST_ROOT.rstrip("/")
    if ci_root.is_dir() and _contains_collectable_test(ci_root):
        paths.append(CI_CONTRACT_TEST_ROOT)

    unit_root = repo_root / TEST_UNIT_PREFIX.rstrip("/")
    if unit_root.is_dir():
        for dirpath, _dirs, files in os.walk(unit_root, onerror=_raise_walk_error):
            for name in sorted(files):
                if not is_test_file_name(name):
                    continue
                candidate = Path(dirpath) / name
                try:
                    source = candidate.read_text(encoding="utf-8")
                except (OSError, ValueError):  # boundary-ok: unreadable → keep
                    paths.append(candidate.relative_to(repo_root).as_posix())
                    continue
                if CI_CONTRACT_MARKER in source:
                    paths.append(candidate.relative_to(repo_root).as_posix())

    return sorted(set(paths))


def compute_selection(
    changed_files: list[str],
    adjacency_path: Path,
    ref_name: str,
    event_name: str = "pull_request",
    feature_flag_enabled: bool = True,
    pyproject_dependency_relevant: bool | None = None,
    repo_root: Path | None = None,
) -> ModelTestSelection:
    """Resolve the test selection for a change set.

    ``pyproject_dependency_relevant`` carries the content-aware classification of a
    ``pyproject.toml`` change (computed by the CLI via a base-vs-head TOML diff):
    ``True`` = a dependency-bearing table changed (escalate), ``False`` = the change
    is metadata-only (do not escalate on ``pyproject.toml`` alone), ``None`` = not
    classified. When ``pyproject.toml`` is in the change set and this is not
    ``False`` (i.e. ``True`` or ``None``), the selector fails closed and escalates.

    ``repo_root`` is the tree the file-grain import-graph closure (OMN-14921) is
    computed over — defaults to :data:`REPO_ROOT` (this checkout). Tests inject a
    synthetic tree here so the closure runs over controlled fixtures.
    """
    config = load_adjacency_map(adjacency_path)
    closure_root = repo_root if repo_root is not None else REPO_ROOT

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

    # 3. Shared module escalation. (OMN-14921: this set is the raw top-level
    # module name under src/omnibase_core/ for every changed source file — it
    # is no longer intersected against a hand-curated adjacency-map key set,
    # which is retired. The intersection served only to filter to "known"
    # modules; membership in `shared_modules`/the threshold count below needs
    # no such filter.)
    changed_modules = {
        path[len(SRC_PREFIX) :].split("/", 1)[0]
        for path in changed_files
        if path.startswith(SRC_PREFIX)
    }
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

    # 5a. Always-run set (OMN-15661). Resolved once here, after the docs-only
    # exemption (which stays empty — documentation is positively proven inert)
    # and before every branch that emits a narrowed selection. Enumerating the
    # tests/ tree is the same class of read this function already does through
    # the closure; if it fails we cannot prove the narrowed selection covers the
    # gates, so we fail closed. TEST_INFRASTRUCTURE is the honest reason: the
    # tests/ tree IS the test infrastructure being enumerated.
    try:
        unnarrowable = unnarrowable_test_paths(closure_root)
    except OSError:
        return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)

    # 5b. Required-check manifest changes are non-Python governance data with a
    # dedicated validator test. Without this positive mapping the import-graph
    # closure correctly treats the path as unresolved and selects tests/unit/,
    # which makes pre-push run the broad unit/import suite for manifest-only
    # reconciliations.
    if changed_files and set(changed_files) == {REQUIRED_CHECKS_MANIFEST_PATH}:
        selected = _with_unnarrowable([REQUIRED_CHECKS_MANIFEST_TEST], unnarrowable)
        split_count = _split_count_for(selected, repo_root=closure_root)
        return ModelTestSelection(
            selected_paths=selected,
            split_count=split_count,
            is_full_suite=False,
            full_suite_reason=None,
            matrix=list(range(1, split_count + 1)),
        )

    # 5c. CI-contract classification for `.github/**` diffs (OMN-16917, applying
    # the OMN-16745 ruling — see the block comment on CI_CONTRACT_TEST_ROOT).
    # Placed AFTER every escalation above, so a `.github/**` edit paired with a
    # shared module (step 3), a dependency-bearing pyproject.toml or any
    # `test_infrastructure_paths` entry including the selector itself (step 2),
    # or >= 8 changed modules (step 4) still escalates on that path's own rules.
    # `.md` under `.github/` stays documentation and is handled by step 5.
    github_ci_files = [
        path
        for path in changed_files
        if path.startswith(GITHUB_DIR_PREFIX) and not _is_docs_only_path(path)
    ]
    if github_ci_files:
        try:
            ci_contract = ci_contract_test_paths(closure_root)
        except OSError:
            return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)
        if not ci_contract:
            # OMN-15541: the class may never select NOTHING. With no CI-contract
            # proof resolvable in this tree there is no substitute for the
            # escalation, so take it rather than narrow on absence of evidence.
            return _full_suite(EnumFullSuiteReason.TEST_INFRASTRUCTURE)

        residual = [path for path in changed_files if path not in set(github_ci_files)]
        # A directly-touched unit-test module narrows to ITSELF, at file grain —
        # strictly narrower than the containing directory the closure's
        # forced-keep would emit, and strictly covering the changed module
        # (the OMN-16745 grain lesson). A non-collectable file under tests/unit/
        # (a helper, a conftest) is NOT narrowable this way and falls through to
        # the closure below, which still forces its directory.
        touched_tests = [
            path
            for path in residual
            if path.startswith(TEST_UNIT_PREFIX) and is_test_file_name(Path(path).name)
        ]
        # Documentation is positively inert (step 5's own premise), so it is not
        # a closure input. Everything else still goes through the closure and
        # still fails closed there to the ["tests/unit/"] sentinel.
        closure_inputs = [
            path
            for path in residual
            if path not in set(touched_tests) and not _is_docs_only_path(path)
        ]
        closure_files: list[str] = []
        if closure_inputs:
            closure_files = list(
                compute_closure_selection(
                    closure_inputs, repo_root=closure_root
                ).selected_files
            )
        selected = _with_unnarrowable(
            _dedup([*closure_files, *touched_tests, *ci_contract]), unnarrowable
        )
        split_count = _split_count_for(selected, repo_root=closure_root)
        return ModelTestSelection(
            selected_paths=selected,
            split_count=split_count,
            is_full_suite=False,
            full_suite_reason=None,
            matrix=list(range(1, split_count + 1)),
        )

    # 6. Smart selection (OMN-14921: file-grain import-graph closure, computed
    # over the live grimp graph — replaces the retired hand-curated adjacency
    # map). Every ambiguity fails closed to the conservative ["tests/unit/"]
    # whole-tree sentinel inside compute_closure_selection itself; a genuinely
    # empty result here means the closure positively proved zero test files
    # reference the change (stronger evidence than "no mapping found").
    closure = compute_closure_selection(changed_files, repo_root=closure_root)
    # The closure answers only for tests/unit/; the paths it structurally cannot
    # see (OMN-15661) are unioned in so a narrowed run still covers them.
    selected = _with_unnarrowable(closure.selected_files, unnarrowable)
    split_count = _split_count_for(selected, repo_root=closure_root)

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
    """Count the collectable test files a selection covers.

    ``selected_paths`` entries are either a directory (module-grain sentinel,
    e.g. ``tests/unit/`` or ``tests/unit/cli/`` — walked recursively) or an
    individual test FILE (OMN-14921 file-grain closure output, e.g.
    ``tests/unit/cli/test_foo.py`` — counted directly, no walk needed).

    Directory walks count every name :func:`is_test_file_name` accepts — i.e.
    the whole of ``TEST_FILE_PATTERNS``, which mirrors pytest's ``python_files``
    — not just the ``test_*.py`` half. Counting only one pattern here while
    ``_contains_collectable_test`` admits both would let a directory be SELECTED
    on the strength of files this function then does not count, undercounting
    the volume and emitting too few matrix splits (OMN-16917 review finding).
    """
    total = 0
    for rel in selected_paths:
        target = repo_root / rel
        if target.is_dir():
            total += sum(
                1
                for candidate in target.rglob("*.py")
                if is_test_file_name(candidate.name)
            )
        elif target.is_file():
            total += 1
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
    parser.add_argument(
        "--shadow-closure",
        choices=("on", "off"),
        default="off",
        help=(
            "SHADOW MODE (OMN-14921, default off): additionally compute the "
            "file-grain import-graph-closure selection, emit both selections + "
            "delta to --shadow-closure-output and stderr, and return the "
            "module-grain selection UNCHANGED. Observational only — promotion "
            "out of shadow is a separate burn-in-gated decision."
        ),
    )
    parser.add_argument(
        "--shadow-closure-output",
        type=Path,
        default=Path("shadow_closure.json"),
        help="Where to write the shadow closure report JSON (only when --shadow-closure on).",
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
        repo_root=args.repo_root,
    )
    if args.shadow_closure == "on":
        # SHADOW MODE (OMN-14921): now vestigial post-promotion — compute_selection's
        # own smart-selection step already IS the closure computation, so this
        # necessarily reports delta=0 (module_grain == the promoted selection).
        # Left wired (harmless, non-blocking) rather than removed in this PR;
        # a follow-up should retire the --shadow-closure flag and CI wiring once
        # burn-in data collection for the (still-open) shared_modules-demotion
        # question (OMN-14342) is no longer needed. ANY shadow failure is
        # contained here — it must never change or break the returned selection.
        _emit_shadow_closure(changed, selection, args)
    sys.stdout.write(selection.model_dump_json())
    sys.stdout.write("\n")
    return 0


def _emit_shadow_closure(
    changed: list[str],
    selection: ModelTestSelection,
    args: argparse.Namespace,
) -> None:
    from scripts.ci.test_selection_closure import (
        ModelShadowClosureReport,
        compute_shadow_closure,
    )

    try:
        report = compute_shadow_closure(
            changed_files=changed,
            selection=selection,
            repo_root=args.repo_root,
        )
    except Exception as exc:  # noqa: BLE001  # boundary-ok: shadow must never break the selector
        report = ModelShadowClosureReport(
            fail_closed_reasons=[f"shadow computation error: {exc!r}"],
            module_grain_is_full_suite=selection.is_full_suite,
            module_grain_reason=(
                selection.full_suite_reason.value
                if selection.full_suite_reason is not None
                else None
            ),
            module_grain_paths=list(selection.selected_paths),
            changed_file_count=len(changed),
        )
    try:
        args.shadow_closure_output.write_text(
            report.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:  # boundary-ok: artifact write failure is non-fatal
        sys.stderr.write(f"SHADOW_CLOSURE: report write failed: {exc}\n")
    sys.stderr.write(
        "SHADOW_CLOSURE: "
        f"skipped={report.skipped_reason!r} narrowed={report.narrowed} "
        f"module_grain={report.module_grain_paths} "
        f"candidates={report.candidate_file_count} "
        f"file_grain={report.file_grain_file_count} "
        f"delta={report.delta_file_count} "
        f"kept_fail_closed={report.kept_fail_closed_count} "
        f"fail_closed_reasons={report.fail_closed_reasons} "
        f"elapsed={report.elapsed_seconds}s\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
