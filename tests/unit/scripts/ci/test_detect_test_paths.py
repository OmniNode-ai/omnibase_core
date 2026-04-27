# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

from scripts.ci.detect_test_paths import resolve_test_paths

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"


def test_single_module_change_resolves_to_one_test_dir() -> None:
    changed_files = ["src/omnibase_core/cli/foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    # `_resolve` returns ONLY unit-test paths. Integration runs always via
    # the separate fixed-matrix tests-integration job, so the smart-selection
    # contract excludes tests/integration/ entirely.
    assert paths == ["tests/unit/cli/"]


def test_test_only_change_runs_only_changed_test_dir() -> None:
    changed_files = ["tests/unit/nodes/test_foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == ["tests/unit/nodes/"]


def test_root_level_unit_test_file_maps_to_unit_root() -> None:
    # Root-level files like tests/unit/test_foo.py must NOT produce
    # tests/unit/test_foo.py/ (an invalid directory target).
    changed_files = ["tests/unit/test_foo.py"]
    paths = resolve_test_paths(changed_files, adjacency_path=ADJ)
    assert paths == ["tests/unit/"]


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
