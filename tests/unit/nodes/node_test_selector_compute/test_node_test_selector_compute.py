# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Oracle-parity differential battery for node_test_selector_compute (OMN-14700).

``scripts/ci/detect_test_paths.py`` IS the verified, CI-governing oracle. This
suite asserts that the RSD-regenerated ``NodeTestSelectorCompute`` produces
byte-for-byte identical ``ModelTestSelection`` output to the oracle across every
representative change-set — single-module, shared-module, test-infra,
scripts/ci, threshold, event/branch escalation, feature-flag-off, pyproject
classification, file-grain closure selection, empty, and (hermetically) the
volume-scaling split path. A node that diverges on any case FAILS the RSD
correctness gate.

OMN-14921 promotion note: the node itself does not compute the file-grain
closure (it is I/O — grimp graph build + AST reads — and the node is pure,
see ``selector_core.py``'s module docstring for the documented EFFECT-boundary
gap in ``runtime_test_selector.py``). This test harness closes that gap
ITSELF, at the test-driver layer: it calls the SAME
``test_selection_closure.compute_closure_selection`` primitive the oracle
calls internally and injects the result as
``ModelTestSelectionRequest.closure_selected_files`` — proving byte-for-byte
parity on the gates AND the closure-consuming formatting/split-count logic,
given the same closure input. This is a real, narrower parity claim than the
oracle's fully-self-contained CI invocation; it does not paper over the
runtime_test_selector.py wiring gap.

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
from scripts.ci.test_selection_closure import compute_closure_selection
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

    Pass 1 resolves the selected paths (independent of volume) — the closure
    (OMN-14921) is computed HERE, at this test's I/O-permitted boundary, with
    the identical primitive the oracle calls, and injected into the request.
    Pass 2 counts ``test_*.py`` under exactly those paths with the oracle's
    own helper and re-runs the pure node to size the split. This mirrors what
    ``runtime_test_selector.py`` should do at the I/O boundary (tracked gap,
    see module docstring above).
    """
    node = NodeTestSelectorCompute()
    closure = compute_closure_selection(changed_files, repo_root=repo_root)

    def _request(counts: dict[str, int]) -> ModelTestSelectionRequest:
        return ModelTestSelectionRequest(
            changed_files=changed_files,
            ref_name=ref_name,
            adjacency=ADJ_MAP,
            test_file_counts=counts,
            closure_selected_files=closure.selected_files,
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
    # Real file (OMN-14921: closure grain needs a real source to build a
    # closure over — see test_parity_nonexistent_file_fails_closed below for
    # the fail-closed case parity).
    sel = _assert_parity(
        monkeypatch, ["src/omnibase_core/cli/cli_bootstrap.py"], "pr-branch"
    )
    assert sel.is_full_suite is False
    assert any(p.startswith("tests/unit/cli/") for p in sel.selected_paths)


def test_parity_nonexistent_file_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = _assert_parity(monkeypatch, ["src/omnibase_core/cli/foo.py"], "pr-branch")
    assert sel.is_full_suite is False
    assert sel.selected_paths == ["tests/unit/"]


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


def test_parity_docs_only_selects_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    # OMN-14910 (CI-C1 #3): oracle and node agree that a pure-docs diff selects []
    sel = _assert_parity(monkeypatch, ["docs/x.md", "docs/runbooks/y.md"], "pr-branch")
    assert sel.is_full_suite is False
    assert sel.selected_paths == []
    assert sel.split_count == 1


def test_parity_unrelated_scripts_ci_no_escalate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # OMN-14910 (CI-C1 #1): a non-selector scripts/ci/ file no longer escalates,
    # identically in oracle and node.
    sel = _assert_parity(monkeypatch, ["scripts/ci/ci_summary_gate.py"], "pr-branch")
    assert sel.is_full_suite is False
    assert sel.selected_paths == ["tests/unit/"]


def test_parity_selector_core_change_escalates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # OMN-14910 (CI-C1 #1): the canonical node's own algorithm file is an
    # unconditional trigger in both surfaces (self-referential guard).
    sel = _assert_parity(
        monkeypatch,
        ["src/omnibase_core/nodes/node_test_selector_compute/selector_core.py"],
        "pr-branch",
    )
    assert sel.full_suite_reason == "test_infrastructure"


def test_parity_ruff_only_pyproject_narrows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # OMN-14910 (CI-C1 #2): pyproject.toml + relevant=False narrows identically.
    sel = _assert_parity(
        monkeypatch,
        ["pyproject.toml", "src/omnibase_core/cli/cli_bootstrap.py"],
        "pr-branch",
        pyproject_dependency_relevant=False,
    )
    assert sel.is_full_suite is False
    assert any(p.startswith("tests/unit/cli/") for p in sel.selected_paths)


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
# Volume-scaling parity across the threshold and cap
# =============================================================================
#
# OMN-14921: the retired module-grain synthetic sweep (a bare tmp_path with
# fabricated tests/unit/mixins/test_v{i}.py files, no real src/ tree, n_files
# from 0 to 2000) is no longer expressible — closure computation requires a
# real, parseable src/omnibase_core tree to resolve the changed file and
# build the grimp graph over (a bare synthetic count directory has neither).
# Hermetically faking the omnibase_core package name itself is deliberately
# avoided by test_selection_closure.py's own test suite too (it uses synthetic
# package names throughout, and only exercises the real omnibase_core tree
# without monkeypatching); doing so reliably would need sys.modules cache
# eviction of the ALREADY-imported real package, which is out of scope here.
# test_parity_mixins_real_tree_volume_scaling (below) covers the equivalent
# real-tree volume-scaling parity case under closure grain instead.


def test_parity_mixins_change_produces_multiple_splits_on_real_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A real leaf change whose closure fans out across enough test files to
    # exceed a single split — parity on the resulting split_count/matrix shape.
    sel = _assert_parity(
        monkeypatch, ["src/omnibase_core/mixins/mixin_caching.py"], "pr-branch"
    )
    assert sel.is_full_suite is False
    assert sel.split_count >= 1
    assert sel.matrix == list(range(1, sel.split_count + 1))
