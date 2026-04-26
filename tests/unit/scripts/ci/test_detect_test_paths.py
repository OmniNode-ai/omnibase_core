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
