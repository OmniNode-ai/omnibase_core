# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest

from scripts.ci.detect_test_paths import resolve_test_paths

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"


def test_single_module_change_resolves_to_one_test_dir() -> None:
    changed_files = ["src/omnibase_core/cli/foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    # `_resolve` returns ONLY unit-test paths. Integration runs always via
    # the separate fixed-matrix tests-integration job, so the smart-selection
    # contract excludes tests/integration/ entirely.
    assert paths == ["tests/unit/cli/"]


def test_agents_module_change_resolves_to_agents_tests() -> None:
    changed_files = ["src/omnibase_core/agents/prm_detectors.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == ["tests/unit/agents/"]


def test_test_only_change_runs_only_changed_test_dir() -> None:
    changed_files = ["tests/unit/nodes/test_foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == ["tests/unit/nodes/"]


def test_integration_test_only_change_does_not_select_unit_tests() -> None:
    # Integration test changes do not contribute to unit-job selection;
    # the integration job runs all integration tests on every PR anyway.
    changed_files = ["tests/integration/nodes/test_foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == []


def test_unknown_source_path_falls_back_to_full_suite_signal() -> None:
    # Files outside src/ and tests/unit/ — no unit-test mapping.
    changed_files = ["docs/README.md", ".github/workflows/foo.yml"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == []


def test_change_in_models_expands_to_exact_set() -> None:
    changed_files = ["src/omnibase_core/models/foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    # models is in shared_modules — full-suite escalation lives in compute_selection
    # (Task 6). resolve_test_paths returns the *expanded* unit-test dirs only.
    expected = sorted(
        f"tests/unit/{m}/"
        for m in (
            "analysis",
            "models",
            "nodes",
            "contracts",
            "runtime",
            "validation",
            "services",
            "factories",
            "container",
        )
    )
    assert paths == expected


def test_change_in_protocols_expands_to_exact_set() -> None:
    changed_files = ["src/omnibase_core/protocols/foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    expected = sorted(
        f"tests/unit/{m}/" for m in ("protocols", "nodes", "services", "factories")
    )
    assert paths == expected


# ---------------------------------------------------------------------------
# Task 6: compute_selection escalation tests
# ---------------------------------------------------------------------------

from scripts.ci.detect_test_paths import compute_selection
from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
)


def test_shared_module_change_escalates_to_full_suite() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/models/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


def test_test_infrastructure_change_escalates_to_full_suite() -> None:
    selection = compute_selection(
        changed_files=["tests/conftest.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_workflow_only_change_no_longer_escalates() -> None:
    # OMN-14081: .github/workflows/ was removed from test_infrastructure_paths to
    # align with omnibase_infra. A workflow-only change carries zero test-code delta,
    # is exercised on the PR's own CI run, and is backstopped by the unconditional
    # merge_group -> main full suite (root CLAUDE.md Rule #4). It now falls to the
    # conservative tests/unit/ fallback instead of forcing the distributed full suite.
    selection = compute_selection(
        changed_files=[".github/workflows/receipt-gate.yml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert selection.selected_paths == ["tests/unit/"]


def test_selector_change_escalates_to_distributed_full_suite() -> None:
    # OMN-14910 (CI-C1 #1): scripts/ci/ was NARROWED from a blanket directory
    # trigger to the selector's OWN files. detect_test_paths.py is the selector,
    # so a change here still escalates — a selector that narrowed on a change to
    # ITSELF would be self-referentially fail-open.
    selection = compute_selection(
        changed_files=["scripts/ci/detect_test_paths.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


# ---------------------------------------------------------------------------
# OMN-14081: content-aware pyproject.toml classification
# ---------------------------------------------------------------------------

from scripts.ci.detect_test_paths import classify_pyproject_dependency_relevant

_BASE_PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "omnibase-core"
version = "0.46.5"
description = "Core models"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.0", "pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.entry-points."onex.nodes"]
foo = "omnibase_core.nodes.foo"

[project.urls]
Homepage = "https://example.com"

[dependency-groups]
test = ["pytest-xdist"]

[tool.uv.sources]
omnibase-compat = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra"

[tool.ruff]
line-length = 88
"""


def _mutate(base: str, old: str, new: str) -> str:
    assert old in base, f"fixture missing marker: {old!r}"
    return base.replace(old, new, 1)


def test_classify_version_bump_is_not_dependency_relevant() -> None:
    # The dominant core case: a bare version bump must NOT escalate.
    new = _mutate(_BASE_PYPROJECT, 'version = "0.46.5"', 'version = "0.46.6"')
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is False


def test_classify_entry_point_registration_is_not_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT,
        'foo = "omnibase_core.nodes.foo"',
        'foo = "omnibase_core.nodes.foo"\nbar = "omnibase_core.nodes.bar"',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is False


def test_classify_metadata_edit_is_not_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT,
        'description = "Core models"',
        'description = "Core models and contracts"',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is False


def test_classify_dependency_add_is_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT,
        'dependencies = ["pydantic>=2.0", "pyyaml>=6.0"]',
        'dependencies = ["pydantic>=2.0", "pyyaml>=6.0", "httpx>=0.27"]',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_optional_dependency_change_is_dependency_relevant() -> None:
    new = _mutate(_BASE_PYPROJECT, 'dev = ["pytest>=8.0"]', 'dev = ["pytest>=8.1"]')
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_dependency_group_change_is_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT,
        'test = ["pytest-xdist"]',
        'test = ["pytest-xdist", "pytest-cov"]',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_build_system_change_is_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT, 'requires = ["hatchling"]', 'requires = ["setuptools"]'
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_uv_sources_change_is_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT,
        "omnibase-compat = { workspace = true }",
        'omnibase-compat = { git = "https://example.com/compat" }',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_requires_python_change_is_dependency_relevant() -> None:
    new = _mutate(
        _BASE_PYPROJECT, 'requires-python = ">=3.12"', 'requires-python = ">=3.13"'
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_pytest_config_change_is_dependency_relevant() -> None:
    # [tool.pytest.ini_options] is genuine test infrastructure — it MUST escalate.
    new = _mutate(
        _BASE_PYPROJECT, 'addopts = "-ra"', 'addopts = "-ra -p no:cacheprovider"'
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_malformed_new_toml_fails_closed() -> None:
    assert (
        classify_pyproject_dependency_relevant(_BASE_PYPROJECT, "this = = broken")
        is True
    )


def test_classify_malformed_old_toml_fails_closed() -> None:
    assert (
        classify_pyproject_dependency_relevant("this = = broken", _BASE_PYPROJECT)
        is True
    )


def test_classify_missing_base_content_fails_closed() -> None:
    assert classify_pyproject_dependency_relevant(None, _BASE_PYPROJECT) is True


def test_classify_missing_head_content_fails_closed() -> None:
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, None) is True


def test_pyproject_version_bump_narrows_via_compute_selection() -> None:
    # End-to-end at the compute_selection layer: pyproject.toml in the diff, classified
    # metadata-only (relevant=False) → narrow, not full suite.
    selection = compute_selection(
        changed_files=["pyproject.toml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert selection.selected_paths == ["tests/unit/"]


def test_pyproject_dependency_change_escalates_via_compute_selection() -> None:
    selection = compute_selection(
        changed_files=["pyproject.toml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=True,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_pyproject_unclassified_fails_closed_via_compute_selection() -> None:
    # relevant=None (base ref unavailable / unsupplied) → escalate, fail closed.
    selection = compute_selection(
        changed_files=["pyproject.toml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=None,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_pyproject_metadata_only_does_not_suppress_shared_module_escalation() -> None:
    # A metadata-only pyproject change bundled with a shared-module source change must
    # still escalate — via SHARED_MODULE, not TEST_INFRASTRUCTURE.
    selection = compute_selection(
        changed_files=["pyproject.toml", "src/omnibase_core/models/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


def test_pyproject_relevance_ignored_when_pyproject_not_in_diff() -> None:
    # The classification param only matters when pyproject.toml is in the change set.
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=None,
    )
    assert selection.is_full_suite is False
    assert "tests/unit/cli/" in selection.selected_paths


def test_threshold_module_count_escalates() -> None:
    # 8 distinct, non-shared modules changed → THRESHOLD_MODULES.
    changed_files = [
        f"src/omnibase_core/{m}/x.py"
        for m in [
            "cli",
            "constants",
            "decorators",
            "logging",
            "merge",
            "navigation",
            "package",
            "rendering",
        ]
    ]
    selection = compute_selection(
        changed_files=changed_files,
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.THRESHOLD_MODULES


def test_main_branch_always_full_suite() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/x.py"],
        adjacency_path=ADJ,
        ref_name="main",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.MAIN_BRANCH


def test_small_change_returns_smart_selection_no_reason() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert "tests/unit/cli/" in selection.selected_paths
    assert 1 <= selection.split_count <= 5
    assert selection.matrix == list(range(1, selection.split_count + 1))


# ---------------------------------------------------------------------------
# Task 10: feature_flag_off branch
# ---------------------------------------------------------------------------


def test_feature_flag_off_returns_full_suite() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        feature_flag_enabled=False,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.FEATURE_FLAG_OFF
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


# ---------------------------------------------------------------------------
# OMN-9855: schedule + merge_group event escalation
# ---------------------------------------------------------------------------


def test_schedule_event_escalates_to_full_suite() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        event_name="schedule",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SCHEDULED
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


def test_merge_group_event_escalates_to_full_suite() -> None:
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        event_name="merge_group",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.MERGE_GROUP
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


# ---------------------------------------------------------------------------
# OMN-11026: volume-aware _split_count_for
# ---------------------------------------------------------------------------

from scripts.ci.detect_test_paths import (
    VOLUME_MAX_SPLITS,
    VOLUME_TARGET_FILES_PER_SPLIT,
    VOLUME_THRESHOLD_FILES,
    _split_count_for,
)


def test_split_count_small_path_set_unchanged_without_repo_root() -> None:
    # No repo_root → volume scaling is inert; behavior matches the original
    # path-count formula. Verifies the existing small-PR contract is preserved.
    assert _split_count_for(["tests/unit/cli/"]) == 1
    assert _split_count_for(["tests/unit/cli/", "tests/unit/agents/"]) == 1
    assert _split_count_for(["a/", "b/", "c/"]) == 2
    assert _split_count_for([f"p{i}/" for i in range(6)]) == 3
    assert _split_count_for([f"p{i}/" for i in range(11)]) == 4
    assert _split_count_for([f"p{i}/" for i in range(17)]) == 5


def test_split_count_below_threshold_uses_path_floor(tmp_path: Path) -> None:
    # 10 test files across 1 selected path is well under VOLUME_THRESHOLD_FILES;
    # volume scaling does not engage and the path-count floor (1) wins.
    target = tmp_path / "tests/unit/cli"
    target.mkdir(parents=True)
    for i in range(10):
        (target / f"test_x{i}.py").write_text("")
    assert _split_count_for(["tests/unit/cli/"], repo_root=tmp_path) == 1


def test_split_count_above_threshold_scales_by_file_count(tmp_path: Path) -> None:
    # 200 test files across 3 expanded paths must produce
    # ceil(200 / VOLUME_TARGET_FILES_PER_SPLIT) splits — well above the
    # path-floor of 2 that the old formula returned.
    for module in ("mixins", "models", "nodes"):
        d = tmp_path / "tests" / "unit" / module
        d.mkdir(parents=True)
    for i in range(200):
        (tmp_path / "tests/unit/models" / f"test_m{i}.py").write_text("")
    selected = ["tests/unit/mixins/", "tests/unit/models/", "tests/unit/nodes/"]
    expected = -(-200 // VOLUME_TARGET_FILES_PER_SPLIT)  # ceil(200/40) = 5
    assert _split_count_for(selected, repo_root=tmp_path) == expected
    assert expected > 2  # would otherwise time out at the old path-floor


def test_split_count_caps_at_max_splits(tmp_path: Path) -> None:
    # 10K test files would push the volume scaler to 250 splits; the cap keeps
    # the matrix shape consistent with the main-branch full-suite layout.
    d = tmp_path / "tests/unit/models"
    d.mkdir(parents=True)
    for i in range(10_000):
        (d / f"test_big{i}.py").write_text("")
    assert (
        _split_count_for(["tests/unit/models/"], repo_root=tmp_path)
        == VOLUME_MAX_SPLITS
    )


def test_split_count_path_floor_wins_when_higher(tmp_path: Path) -> None:
    # 17 paths → path-floor = 5; if test volume is below the threshold, the
    # floor takes over and we don't regress to a smaller split count.
    selected = [f"tests/unit/p{i}/" for i in range(17)]
    for rel in selected:
        (tmp_path / rel).mkdir(parents=True)
    assert _split_count_for(selected, repo_root=tmp_path) == 5


def test_split_count_mixins_change_against_real_tree_yields_enough_splits() -> None:
    # Regression coverage for the mixins-adjacency timeout. With mixins →
    # [models, nodes] expansion, the resolved unit-test directories must
    # produce enough splits that no single split has to run hundreds of test
    # files within the 35-minute job timeout. Lower bound is conservative; the
    # actual value rises if the test tree grows.
    selected = ["tests/unit/mixins/", "tests/unit/models/", "tests/unit/nodes/"]
    split_count = _split_count_for(selected, repo_root=REPO_ROOT)
    assert split_count >= 10, (
        f"mixins-adjacency expansion must produce >=10 splits to fit the "
        f"job timeout; got {split_count}"
    )
    assert split_count <= VOLUME_MAX_SPLITS


def test_compute_selection_mixins_change_yields_volume_scaled_splits() -> None:
    # End-to-end: a mixins-only PR must not be capped at the old 2-split shape.
    selection = compute_selection(
        changed_files=["src/omnibase_core/mixins/mixin_caching.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.split_count >= 10
    assert selection.matrix == list(range(1, selection.split_count + 1))


def test_threshold_constant_is_consistent() -> None:
    # Guardrail: the threshold must not be raised without intent; setting it
    # too high reintroduces the OMN-11026 timeout regression.
    assert VOLUME_THRESHOLD_FILES <= 100
    assert VOLUME_TARGET_FILES_PER_SPLIT <= 50


# ---------------------------------------------------------------------------
# OMN-14910 (CI-C1 #1): scripts/ci/ narrowed to the selector's own files.
# The selector's own files stay unconditional full-suite triggers (self-
# referential fail-open guard); unrelated scripts/ci/ files no longer escalate.
# ---------------------------------------------------------------------------

_SELECTOR_OWN_FILES = [
    "scripts/ci/detect_test_paths.py",
    "scripts/ci/test_selection_loader.py",
    "scripts/ci/test_selection_models.py",
    "scripts/ci/test_selection_adjacency.yaml",
    "src/omnibase_core/nodes/node_test_selector_compute/selector_core.py",
]


@pytest.mark.parametrize("selector_file", _SELECTOR_OWN_FILES)
def test_selector_own_files_still_escalate(selector_file: str) -> None:
    # A diff touching the selection logic or its config MUST re-run everything —
    # a selector that narrowed on a change to itself is self-referentially
    # fail-open (the C1.1 gate-erosion caveat).
    selection = compute_selection(
        changed_files=[selector_file],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True, f"{selector_file} must escalate"
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


@pytest.mark.parametrize(
    "unrelated_ci_file",
    [
        "scripts/ci/ci_summary_gate.py",
        "scripts/ci/verify_flip_bundle.py",
        "scripts/ci/canonical_handler_shape.py",
        "scripts/ci/product_readiness.py",
        "scripts/ci/product_reason_graph.py",
    ],
)
def test_unrelated_scripts_ci_file_no_longer_escalates(unrelated_ci_file: str) -> None:
    # These scripts/ci/ files have zero relationship to test selection; under the
    # OMN-14081 blanket `scripts/ci/` trigger they forced a 40-way full suite. They
    # now fall to the conservative fallback instead (no unit-test mapping).
    selection = compute_selection(
        changed_files=[unrelated_ci_file],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False, f"{unrelated_ci_file} should not escalate"
    assert selection.full_suite_reason is None
    assert selection.selected_paths == ["tests/unit/"]


# ---------------------------------------------------------------------------
# OMN-14910 (CI-C1 #2): lint-only [tool.ruff.*] is a safe pyproject table.
# ---------------------------------------------------------------------------


def test_classify_ruff_config_edit_is_not_dependency_relevant() -> None:
    new = _mutate(_BASE_PYPROJECT, "line-length = 88", "line-length = 100")
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is False


def test_classify_ruff_per_file_ignores_addition_is_not_relevant() -> None:
    # The exact core case: adding a [tool.ruff.lint.per-file-ignores] entry — a
    # lint-ignore line that currently pays for a 40-way full suite.
    new = _mutate(
        _BASE_PYPROJECT,
        "[tool.ruff]\nline-length = 88\n",
        (
            "[tool.ruff]\nline-length = 88\n\n"
            "[tool.ruff.lint.per-file-ignores]\n"
            '"scripts/x.py" = ["T201"]\n'
        ),
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is False


def test_classify_pytest_ini_options_change_still_escalates() -> None:
    # [tool.pytest.ini_options] changes what/how tests run — must NOT be exempt.
    new = _mutate(_BASE_PYPROJECT, 'addopts = "-ra"', 'addopts = "-ra -x"')
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_classify_ruff_plus_dependency_change_still_escalates() -> None:
    # A real dependency change bundled with a ruff edit must still escalate — the
    # ruff exemption does not mask the dependency change (fail closed).
    new = _mutate(_BASE_PYPROJECT, "line-length = 88", "line-length = 100")
    new = _mutate(
        new,
        'dependencies = ["pydantic>=2.0", "pyyaml>=6.0"]',
        'dependencies = ["pydantic>=2.0", "pyyaml>=6.0", "pathspec>=0.12"]',
    )
    assert classify_pyproject_dependency_relevant(_BASE_PYPROJECT, new) is True


def test_ruff_only_pyproject_narrows_via_compute_selection() -> None:
    # End-to-end: a ruff-only pyproject change (relevant=False) does not escalate
    # on pyproject.toml alone.
    selection = compute_selection(
        changed_files=["pyproject.toml", "src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert selection.is_full_suite is False
    assert "tests/unit/cli/" in selection.selected_paths


# ---------------------------------------------------------------------------
# OMN-14910 (CI-C1 #3): docs-only diffs select nothing instead of the ~94%
# tests/unit/ fallback. Ports omnibase_infra#2372 / OMN-14753. `.github/`,
# `.pre-commit-config.yaml`, and `scripts/hooks/` are deliberately NOT exempt.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "docs_files",
    [
        ["docs/runbooks/new-runbook.md"],
        ["README.md"],
        ["docs/architecture/overview.md", "docs/INDEX.md", "CHANGELOG.md"],
    ],
)
def test_docs_only_diff_selects_nothing(docs_files: list[str]) -> None:
    selection = compute_selection(
        changed_files=docs_files,
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert selection.selected_paths == []
    assert selection.split_count == 1
    assert selection.matrix == [1]


def test_markdown_under_shared_module_dir_still_escalates() -> None:
    # Ordering / fail-closed: a `.md` under a shared-module src dir is caught by
    # the shared-module check (step 3) BEFORE the docs-only exemption (step 5),
    # so it escalates. This matches the merged omnibase_infra ordering and errs
    # safe (runs MORE tests, never fewer).
    selection = compute_selection(
        changed_files=["src/omnibase_core/models/README.md"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


def test_mixed_docs_and_code_does_not_take_the_exemption() -> None:
    # A single non-doc file disqualifies the docs-only exemption — the code file
    # still selects its unit tests.
    selection = compute_selection(
        changed_files=["docs/x.md", "src/omnibase_core/cli/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.selected_paths == ["tests/unit/cli/"]


@pytest.mark.parametrize(
    "non_doc_only",
    [
        [".github/workflows/receipt-gate.yml"],
        [".pre-commit-config.yaml"],
        ["scripts/hooks/prepush_smart_tests.sh"],
    ],
)
def test_github_precommit_hooks_are_not_docs_exempt(non_doc_only: list[str]) -> None:
    # core has workflow-shape unit tests (test_occ_preflight_workflow_shape.py,
    # test_receipt_gate_workflow_shape.py) whose outcome depends on these files, so
    # they must run the conservative fallback, NOT the empty docs-only selection.
    selection = compute_selection(
        changed_files=non_doc_only,
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.selected_paths == ["tests/unit/"]


def test_docs_only_does_not_suppress_shared_module_escalation() -> None:
    # A docs file bundled with a shared-module source change must still escalate.
    selection = compute_selection(
        changed_files=["docs/x.md", "src/omnibase_core/models/foo.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.SHARED_MODULE


# ---------------------------------------------------------------------------
# Fail-closed proofs (C1 overall): ambiguous diff, unparseable pyproject,
# missing base ref each still run tests (never an empty/narrowed false-green).
# ---------------------------------------------------------------------------


def test_ambiguous_unclassified_diff_runs_fallback_not_empty() -> None:
    # A change the selector cannot map (not src, not tests/unit, not docs, not a
    # trigger) is AMBIGUOUS — it must run the conservative fallback, never select
    # nothing. Selecting [] here would be a false green.
    selection = compute_selection(
        changed_files=["some/unknown/config.json", "Makefile"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.selected_paths == ["tests/unit/"]
    assert selection.selected_paths != []


def test_unparseable_pyproject_fails_closed() -> None:
    # classify returns True (escalate) on a TOML parse error; compute_selection
    # then escalates when pyproject.toml is in the diff.
    assert (
        classify_pyproject_dependency_relevant(_BASE_PYPROJECT, "x = = broken") is True
    )
    selection = compute_selection(
        changed_files=["pyproject.toml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=True,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE


def test_missing_base_ref_fails_closed() -> None:
    # No base ref → classification impossible (None) → escalate. This mirrors the
    # CLI path where --base-ref is absent (_resolve_pyproject_dependency_relevant
    # returns None), which compute_selection treats as fail-closed.
    selection = compute_selection(
        changed_files=["pyproject.toml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=None,
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE
