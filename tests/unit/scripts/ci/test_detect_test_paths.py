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


def test_workflow_change_escalates_to_distributed_full_suite() -> None:
    selection = compute_selection(
        changed_files=[".github/workflows/receipt-gate.yml"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


def test_selector_change_escalates_to_distributed_full_suite() -> None:
    selection = compute_selection(
        changed_files=["scripts/ci/detect_test_paths.py"],
        adjacency_path=ADJ,
        ref_name="pr-branch",
    )
    assert selection.is_full_suite is True
    assert selection.full_suite_reason == EnumFullSuiteReason.TEST_INFRASTRUCTURE
    assert selection.split_count == 40
    assert selection.matrix == list(range(1, 41))


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
