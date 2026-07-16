# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Oracle-parity differential battery for node_test_selector_compute (OMN-14700).

``scripts/ci/detect_test_paths.py`` IS the verified oracle. This suite asserts
that the RSD-regenerated ``NodeTestSelectorCompute`` produces byte-for-byte
identical ``ModelTestSelection`` output to the oracle across every representative
change-set — single-module, shared-module, test-infra, scripts/ci, threshold,
event/branch escalation, feature-flag-off, pyproject classification, reverse-dep
expansion, empty, and (hermetically) the volume-scaling split path. A node that
diverges on any case FAILS the RSD correctness gate.

Parity is proven at the compute layer: both sides emit the SAME
``ModelTestSelection`` class, so ``model_dump_json()`` equality is a true
byte-for-byte comparison. The node is fed the identical per-path ``test_*.py``
counts the oracle walks (via the oracle's own ``_count_test_files``), so the
volume-aware split count is compared on equal footing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.detect_test_paths as detect
from omnibase_core.models.nodes.test_selector.model_test_selection import (
    ModelTestSelection,
)
from omnibase_core.models.nodes.test_selector.model_test_selection_request import (
    ModelTestSelectionRequest,
)
from omnibase_core.nodes.node_test_selector_compute.handler import (
    NodeTestSelectorCompute,
)
from scripts.ci.detect_test_paths import _count_test_files, compute_selection
from scripts.ci.test_selection_loader import load_adjacency_map

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
ADJ_MAP = load_adjacency_map(ADJ)


def _node_selection(
    changed_files: list[str],
    ref_name: str,
    repo_root: Path,
    **kwargs: object,
) -> ModelTestSelection:
    """Two-phase node dispatch mirroring the runtime/oracle: select, then count.

    Pass 1 resolves the selected paths (independent of volume); pass 2 counts
    ``test_*.py`` under exactly those paths with the oracle's own helper and
    re-runs the pure node to size the split. This is precisely what
    ``runtime_test_selector.py`` does at the I/O boundary.
    """
    node = NodeTestSelectorCompute()

    def _request(counts: dict[str, int]) -> ModelTestSelectionRequest:
        return ModelTestSelectionRequest(
            changed_files=changed_files,
            ref_name=ref_name,
            adjacency=ADJ_MAP,
            test_file_counts=counts,
            **kwargs,  # type: ignore[arg-type]
        )

    prelim = node.handle(_request({}))
    if prelim.is_full_suite:
        return prelim
    counts = {
        path: _count_test_files([path], repo_root) for path in prelim.selected_paths
    }
    return node.handle(_request(counts))


def _assert_parity(
    monkeypatch: pytest.MonkeyPatch,
    changed_files: list[str],
    ref_name: str,
    *,
    repo_root: Path = REPO_ROOT,
    **kwargs: object,
) -> ModelTestSelection:
    """Assert node output == oracle output, byte-for-byte, for one change-set."""
    # Pin the oracle's filesystem root so its internal _count_test_files walk and
    # the node's injected counts are computed against the identical tree.
    monkeypatch.setattr(detect, "REPO_ROOT", repo_root)
    oracle = compute_selection(
        changed_files=changed_files,
        adjacency_path=ADJ,
        ref_name=ref_name,
        **kwargs,  # type: ignore[arg-type]
    )
    node = _node_selection(changed_files, ref_name, repo_root, **kwargs)
    assert node.model_dump_json() == oracle.model_dump_json(), {
        "changed_files": changed_files,
        "ref_name": ref_name,
        "kwargs": kwargs,
        "node": node.model_dump(),
        "oracle": oracle.model_dump(),
    }
    return node


# =============================================================================
# Representative change-set battery (task-required cases)
# =============================================================================


def test_parity_single_module_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["src/omnibase_core/cli/foo.py"], "pr-branch")
    assert sel.is_full_suite is False
    assert "tests/unit/cli/" in sel.selected_paths


def test_parity_shared_module_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["src/omnibase_core/models/foo.py"], "pr-branch")
    assert sel.is_full_suite is True
    assert sel.full_suite_reason == "shared_module"


def test_parity_test_infrastructure_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["tests/conftest.py"], "pr-branch")
    assert sel.full_suite_reason == "test_infrastructure"


def test_parity_scripts_ci_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["scripts/ci/detect_test_paths.py"], "pr-branch")
    assert sel.full_suite_reason == "test_infrastructure"


def test_parity_multi_module_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    changed = [
        f"src/omnibase_core/{m}/x.py"
        for m in (
            "cli",
            "constants",
            "decorators",
            "logging",
            "merge",
            "navigation",
            "package",
            "rendering",
        )
    ]
    sel = _assert_parity(monkeypatch, changed, "pr-branch")
    assert sel.full_suite_reason == "threshold_modules"


def test_parity_empty_change_set(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, [], "pr-branch")
    assert sel.is_full_suite is False
    assert sel.selected_paths == ["tests/unit/"]


def test_parity_main_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["src/omnibase_core/cli/x.py"], "main")
    assert sel.full_suite_reason == "main_branch"


def test_parity_merge_group_event(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(
        monkeypatch,
        ["src/omnibase_core/cli/x.py"],
        "pr-branch",
        event_name="merge_group",
    )
    assert sel.full_suite_reason == "merge_group"


def test_parity_schedule_event(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(
        monkeypatch,
        ["src/omnibase_core/cli/x.py"],
        "pr-branch",
        event_name="schedule",
    )
    assert sel.full_suite_reason == "scheduled"


def test_parity_feature_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(
        monkeypatch,
        ["src/omnibase_core/cli/x.py"],
        "pr-branch",
        feature_flag_enabled=False,
    )
    assert sel.full_suite_reason == "feature_flag_off"


def test_parity_test_only_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["tests/unit/nodes/test_foo.py"], "pr-branch")
    assert sel.selected_paths == ["tests/unit/nodes/"] or sel.split_count >= 1


def test_parity_integration_only_change(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(
        monkeypatch, ["tests/integration/nodes/test_foo.py"], "pr-branch"
    )
    assert sel.selected_paths == ["tests/unit/"]


def test_parity_protocols_reverse_dep_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sel = _assert_parity(
        monkeypatch, ["src/omnibase_core/protocols/foo.py"], "pr-branch"
    )
    assert sel.is_full_suite is False


def test_parity_mixins_real_tree_volume_scaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # mixins -> [models, nodes] expansion against the real repo tree: the dominant
    # volume-scaling case (the oracle's own regression). Parity here proves the
    # node's injected-count split math matches the oracle's rglob walk.
    sel = _assert_parity(
        monkeypatch, ["src/omnibase_core/mixins/mixin_caching.py"], "pr-branch"
    )
    assert sel.is_full_suite is False
    assert sel.matrix == list(range(1, sel.split_count + 1))


# =============================================================================
# pyproject.toml content-aware classification (compute-layer parity)
# =============================================================================


@pytest.mark.parametrize("relevant", [True, False, None])
def test_parity_pyproject_classification(
    monkeypatch: pytest.MonkeyPatch, relevant: bool | None
) -> None:
    _assert_parity(
        monkeypatch,
        ["pyproject.toml"],
        "pr-branch",
        pyproject_dependency_relevant=relevant,
    )


def test_parity_pyproject_metadata_only_with_shared_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A metadata-only pyproject bundled with a shared-module change must still
    # escalate via SHARED_MODULE — precedence parity, not TEST_INFRASTRUCTURE.
    sel = _assert_parity(
        monkeypatch,
        ["pyproject.toml", "src/omnibase_core/models/foo.py"],
        "pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert sel.full_suite_reason == "shared_module"


# =============================================================================
# Hermetic volume-scaling parity across the threshold and cap
# =============================================================================


@pytest.mark.parametrize("n_files", [0, 79, 80, 120, 400, 2000])
def test_parity_volume_split_across_thresholds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, n_files: int
) -> None:
    # Build a controlled tree so the volume-scaling branch is exercised
    # deterministically at the boundary (below/at/above VOLUME_THRESHOLD_FILES and
    # above the VOLUME_MAX_SPLITS cap). mixins expands to [models, nodes]; only
    # mixins gets files, so the total equals n_files on both sides.
    mixins_dir = tmp_path / "tests/unit/mixins"
    mixins_dir.mkdir(parents=True)
    for i in range(n_files):
        (mixins_dir / f"test_v{i}.py").write_text("")
    _assert_parity(
        monkeypatch,
        ["src/omnibase_core/mixins/mixin_caching.py"],
        "pr-branch",
        repo_root=tmp_path,
    )
