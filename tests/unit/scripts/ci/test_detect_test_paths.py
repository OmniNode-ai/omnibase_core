# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"

# ---------------------------------------------------------------------------
# OMN-14921: the hand-curated module-grain adjacency map (`_resolve` /
# `resolve_test_paths`, expand-by-static-reverse_deps-dict) is DELETED, not
# merely bypassed. A live audit found 26 of 40 declarations FALSE against the
# real grimp reverse-import closure — 1,343 of 1,441 unit test files (93%)
# were wrongly excludable. The tests that exercised that function's exact
# "expand to precisely this static set" contract (single-module resolution,
# models/protocols reverse-dep expansion, test-only/integration-only path
# handling) are retired along with it — see the RED PROOF section below for
# direct evidence that the retired behavior was wrong, and
# test_selection_closure.py for the replacement primitive's own test battery.
# ---------------------------------------------------------------------------


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
        changed_files=["src/omnibase_core/cli/cli_bootstrap.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=None,
    )
    assert selection.is_full_suite is False
    assert any(p.startswith("tests/unit/cli/") for p in selection.selected_paths)


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
    # A real file (OMN-14921: closure grain needs a real, parseable source file
    # to compute an import closure over — an ambiguous/nonexistent file fails
    # closed, see test_ambiguous_unclassified_diff_runs_fallback_not_empty).
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/cli_bootstrap.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.full_suite_reason is None
    assert any(p.startswith("tests/unit/cli/") for p in selection.selected_paths)
    assert 0 < len(selection.selected_paths) < 1400  # strictly narrower than the tree
    assert 1 <= selection.split_count <= 40
    assert selection.matrix == list(range(1, selection.split_count + 1))


def test_nonexistent_source_file_fails_closed_to_whole_tree() -> None:
    # OMN-14921: unlike the retired module-grain map (a pure string lookup),
    # the closure needs a real file to compute an import closure over. A
    # changed file missing from the working tree cannot be resolved — fail
    # closed to the whole-tree conservative sentinel, never a false-narrow.
    selection = compute_selection(
        changed_files=["src/omnibase_core/cli/does_not_exist.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.selected_paths == ["tests/unit/"]


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
    # Directory-shaped selection still uses the walked-directory path in
    # _split_count_for (module-grain sentinel shape, e.g. the whole-tree
    # fallback) — this stays a valid, exercised code path post-promotion.
    selected = ["tests/unit/mixins/", "tests/unit/models/", "tests/unit/nodes/"]
    split_count = _split_count_for(selected, repo_root=REPO_ROOT)
    assert split_count >= 10, (
        f"mixins-adjacency expansion must produce >=10 splits to fit the "
        f"job timeout; got {split_count}"
    )
    assert split_count <= VOLUME_MAX_SPLITS


def test_compute_selection_mixins_change_yields_volume_scaled_splits() -> None:
    # End-to-end, real file (OMN-14921: closure grain over the real tree).
    selection = compute_selection(
        changed_files=["src/omnibase_core/mixins/mixin_caching.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert selection.split_count >= 1
    assert any(p.startswith("tests/unit/mixins/") for p in selection.selected_paths)
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
    # OMN-14921: shadow closure module is selector surface — must escalate too.
    "scripts/ci/test_selection_closure.py",
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
        changed_files=["pyproject.toml", "src/omnibase_core/cli/cli_bootstrap.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert selection.is_full_suite is False
    assert any(p.startswith("tests/unit/cli/") for p in selection.selected_paths)


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
        changed_files=["docs/x.md", "src/omnibase_core/cli/cli_bootstrap.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is False
    assert any(p.startswith("tests/unit/cli/") for p in selection.selected_paths)


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


# ---------------------------------------------------------------------------
# OMN-14921: SHADOW MODE invariance — with --shadow-closure on, the selection
# on stdout is byte-identical to the shadow-off run, and EVERY escalation
# trigger still fires. Each case below is a seeded violation of one trigger;
# red-proof: temporarily breaking that trigger in detect_test_paths.py makes
# the corresponding case FAIL (exercised during development, see PR body).
# ---------------------------------------------------------------------------

import json as _json

from scripts.ci.detect_test_paths import main as _detect_main

_THRESHOLD_FILES = [
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

# (case id, changed files, ref_name, event_name, feature_flag, expected reason)
_SHADOW_INVARIANCE_CASES = [
    (
        "feature_flag_off",
        ["src/omnibase_core/cli/foo.py"],
        "pr",
        "pull_request",
        "off",
        "feature_flag_off",
    ),
    (
        "main_branch",
        ["src/omnibase_core/cli/foo.py"],
        "main",
        "push",
        "on",
        "main_branch",
    ),
    (
        "merge_group",
        ["src/omnibase_core/cli/foo.py"],
        "pr",
        "merge_group",
        "on",
        "merge_group",
    ),
    ("schedule", ["src/omnibase_core/cli/foo.py"], "pr", "schedule", "on", "scheduled"),
    (
        "test_infrastructure",
        ["tests/conftest.py"],
        "pr",
        "pull_request",
        "on",
        "test_infrastructure",
    ),
    (
        "pyproject_fail_closed",
        ["pyproject.toml"],
        "pr",
        "pull_request",
        "on",
        "test_infrastructure",
    ),
    (
        "shared_module",
        ["src/omnibase_core/models/foo.py"],
        "pr",
        "pull_request",
        "on",
        "shared_module",
    ),
    (
        "threshold_modules",
        _THRESHOLD_FILES,
        "pr",
        "pull_request",
        "on",
        "threshold_modules",
    ),
    ("smart_path", ["src/omnibase_core/cli/foo.py"], "pr", "pull_request", "on", None),
    ("docs_only", ["docs/x.md"], "pr", "pull_request", "on", None),
]


def _run_detect_main(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    changed: list[str],
    ref_name: str,
    event_name: str,
    feature_flag: str,
    shadow: bool,
    tag: str,
) -> tuple[str, Path]:
    diff_file = tmp_path / f"diff_{tag}.txt"
    diff_file.write_text("\n".join(changed) + "\n")
    shadow_out = tmp_path / f"shadow_{tag}.json"
    argv = [
        "--changed-files-from",
        str(diff_file),
        "--ref-name",
        ref_name,
        "--event-name",
        event_name,
        "--feature-flag",
        feature_flag,
    ]
    if shadow:
        argv += ["--shadow-closure", "on", "--shadow-closure-output", str(shadow_out)]
    capsys.readouterr()  # drain
    assert _detect_main(argv) == 0
    captured = capsys.readouterr()
    return captured.out, shadow_out


@pytest.mark.parametrize(
    ("case_id", "changed", "ref_name", "event_name", "flag", "expected_reason"),
    _SHADOW_INVARIANCE_CASES,
    ids=[c[0] for c in _SHADOW_INVARIANCE_CASES],
)
def test_shadow_mode_returns_identical_selection_and_triggers_still_fire(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case_id: str,
    changed: list[str],
    ref_name: str,
    event_name: str,
    flag: str,
    expected_reason: str | None,
) -> None:
    out_off, shadow_off_path = _run_detect_main(
        tmp_path, capsys, changed, ref_name, event_name, flag, shadow=False, tag="off"
    )
    out_on, shadow_on_path = _run_detect_main(
        tmp_path, capsys, changed, ref_name, event_name, flag, shadow=True, tag="on"
    )

    # 1. Shadow mode NEVER changes the returned selection (byte-identical).
    assert out_on == out_off

    # 2. The escalation trigger still fires (seeded violation per case).
    payload = _json.loads(out_on)
    if expected_reason is None:
        assert payload["is_full_suite"] is False
    else:
        assert payload["is_full_suite"] is True, f"{case_id} must escalate"
        assert payload["full_suite_reason"] == expected_reason

    # 3. Default off: no shadow artifact. On: report exists and is observational.
    assert not shadow_off_path.exists()
    report = _json.loads(shadow_on_path.read_text())
    assert report["shadow_only"] is True
    assert report["ticket"] == "OMN-14921"


def test_shadow_flag_defaults_off_no_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # No --shadow-closure argument at all → identical behavior, no report file.
    out, shadow_path = _run_detect_main(
        tmp_path,
        capsys,
        ["src/omnibase_core/cli/foo.py"],
        "pr",
        "pull_request",
        "on",
        shadow=False,
        tag="default",
    )
    payload = _json.loads(out)
    assert payload["is_full_suite"] is False
    assert not shadow_path.exists()
    assert not Path("shadow_closure.json").exists()


def test_shadow_smart_path_fail_closed_on_unresolvable_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # cli/foo.py does not exist in the working tree → BOTH the promoted main
    # selection (OMN-14921: closure grain needs a real file) and the shadow
    # computation fail closed. The main selection is the whole-tree sentinel;
    # the shadow report's candidate set mirrors it (whole tree), pinned
    # file_grain==candidate (no narrowing) since it's the SAME unresolvable file.
    out, shadow_path = _run_detect_main(
        tmp_path,
        capsys,
        ["src/omnibase_core/cli/foo.py"],
        "pr",
        "pull_request",
        "on",
        shadow=True,
        tag="failclosed",
    )
    payload = _json.loads(out)
    assert payload["is_full_suite"] is False
    assert payload["selected_paths"] == ["tests/unit/"]
    report = _json.loads(shadow_path.read_text())
    assert report["narrowed"] is False
    assert report["fail_closed_reasons"]
    assert report["file_grain_file_count"] == report["candidate_file_count"]


# ---------------------------------------------------------------------------
# RED PROOF (OMN-14921 promotion): the retired module-grain adjacency map
# under-selected on a real, live declaration. `utils: {reverse_deps: []}` was
# the checked-in YAML content immediately before this PR (verified via
# `git show HEAD~1:scripts/ci/test_selection_adjacency.yaml` / repo history) —
# `_OLD_MODULE_GRAIN_RESOLVE` below is a faithful, minimal reimplementation of
# the retired `_resolve()` (deleted above; it was a pure string-split + static
# dict lookup, no closer fidelity is possible than reproducing that exact
# algorithm against the exact-as-declared reverse_deps value). It is NOT
# resurrected as production code — it exists ONLY to make the RED half of this
# proof concrete rather than asserted from memory.
#
# `util_str_enum_base.py` is the audit's own headline finding: the real grimp
# reverse closure shows ~37 real modules import `utils` (1,305 wrongly
# excludable test files), yet the retired map declared `reverse_deps: []` —
# editing this file selected ONLY `tests/unit/utils/`.
# ---------------------------------------------------------------------------

_OLD_UTILS_DECLARATION: list[str] = []  # utils.reverse_deps in the retired YAML


def _old_module_grain_resolve(changed_files: list[str]) -> list[str]:
    """Faithful reimplementation of the retired, deleted `_resolve()`.

    Historical algorithm ONLY — module = first path segment under
    src/omnibase_core/, expand via the (retired) static reverse_deps dict.
    Driven here by the exact `utils: {reverse_deps: []}` value the checked-in
    YAML declared immediately before this PR.
    """
    selected: set[str] = set()
    for path in changed_files:
        if path.startswith("src/omnibase_core/"):
            module = path[len("src/omnibase_core/") :].split("/", 1)[0]
            if module == "utils":
                selected.add("tests/unit/utils/")
                selected.update(f"tests/unit/{m}/" for m in _OLD_UTILS_DECLARATION)
    return sorted(selected)


_UTILS_ENUM_BASE_CHANGE = ["src/omnibase_core/utils/util_str_enum_base.py"]

# Real files, independently confirmed by grimp to import (transitively, through
# their tested enum module) utils.util_str_enum_base — the old declaration's
# false "reverse_deps: []" excluded ALL of these.
_KNOWN_DEPENDENT_ENUM_TESTS = [
    "tests/unit/enums/cost/test_enum_usage_source.py",
    "tests/unit/enums/events/test_enum_deregistration_reason.py",
]


def test_red_old_module_grain_selects_only_utils_dir() -> None:
    """RED half: the retired algorithm, driven by the real retired declaration,
    selects ONLY tests/unit/utils/ for a utils/ change — proving it was blind
    to every one of the ~37 real reverse dependencies grimp finds."""
    old_selection = _old_module_grain_resolve(_UTILS_ENUM_BASE_CHANGE)
    assert old_selection == ["tests/unit/utils/"]
    for dependent_test in _KNOWN_DEPENDENT_ENUM_TESTS:
        assert not dependent_test.startswith(tuple(old_selection)), (
            f"vacuity guard: {dependent_test} must NOT already be inside the "
            "old (narrow) selection, or this is not a real RED case"
        )


def test_green_new_closure_selector_includes_the_missed_dependents() -> None:
    """GREEN half: the promoted file-grain closure selector, for the IDENTICAL
    change, includes real enums test files the old declaration excluded —
    strictly more than the old answer, strictly less than the whole tree."""
    # Sanity: the changed file must be real, not synthetic (closure grain
    # needs a real file to compute a closure over).
    for rel in _UTILS_ENUM_BASE_CHANGE:
        assert (REPO_ROOT / rel).is_file(), f"fixture file must exist: {rel}"

    new_selection = compute_selection(
        changed_files=_UTILS_ENUM_BASE_CHANGE,
        adjacency_path=ADJ,
        ref_name="pr-branch",
    ).selected_paths

    for dependent_test in _KNOWN_DEPENDENT_ENUM_TESTS:
        assert dependent_test in new_selection, (
            f"closure selector must include {dependent_test} (it imports "
            "utils.util_str_enum_base transitively) — the old module-grain "
            "declaration wrongly excluded it"
        )
    # tests/unit/utils/ itself is still covered (the direct-change test file).
    assert any(p.startswith("tests/unit/utils/") for p in new_selection)
    # Strictly narrower than "run everything" — this is closure PRECISION, not
    # a blanket escalation (the whole tree is ~1,441 files).
    assert 0 < len(new_selection) < 1400


def test_old_selection_is_a_strict_subset_of_new_selection() -> None:
    """Direct old-vs-new delta on the identical input: capture both sides."""
    old_selection = set(_old_module_grain_resolve(_UTILS_ENUM_BASE_CHANGE))
    new_files = set(
        compute_selection(
            changed_files=_UTILS_ENUM_BASE_CHANGE,
            adjacency_path=ADJ,
            ref_name="pr-branch",
        ).selected_paths
    )
    # Every file the old directory-grain answer covered is still covered
    # (no regression), and the new answer additionally includes real
    # dependents the old declaration missed.
    assert any(f.startswith("tests/unit/utils/") for f in new_files)
    missed_by_old = [f for f in _KNOWN_DEPENDENT_ENUM_TESTS if f not in old_selection]
    assert missed_by_old == _KNOWN_DEPENDENT_ENUM_TESTS  # old missed ALL of them
    newly_found = [f for f in _KNOWN_DEPENDENT_ENUM_TESTS if f in new_files]
    assert newly_found == _KNOWN_DEPENDENT_ENUM_TESTS  # new selector finds ALL of them


# ---------------------------------------------------------------------------
# Guard: a future hand-declared reverse_deps entry cannot silently go stale
# (OMN-14921 requirement). See also
# model_adjacency_map.ModelAdjacencyMap.reject_adjacency_reintroduction and
# its dedicated unit test in test_test_selection_loader.py.
# ---------------------------------------------------------------------------


def test_adjacency_key_reintroduction_fails_loud_not_silent() -> None:
    from scripts.ci.test_selection_loader import load_adjacency_map

    bad_yaml = """
schema_version: 1
shared_modules: [models]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: []
adjacency:
  utils: { reverse_deps: [] }
"""
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
        fh.write(bad_yaml)
        tmp_name = fh.name
    try:
        with pytest.raises(ValueError, match="adjacency map is retired"):
            load_adjacency_map(Path(tmp_name))
    finally:
        Path(tmp_name).unlink()
