# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-14206: ``detect_test_paths.compute_selection`` passes the policy file's
``closure:`` block to the packaged closure primitive.

Before this change every call site used the primitive's defaults, so a
``closure.candidate_roots`` entry in the policy YAML would have had no effect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.detect_test_paths as detect
from omnibase_core.models.nodes.test_selector.model_closure_selection import (
    ModelClosureSelection,
)
from omnibase_core.nodes.node_test_selector_compute import closure_selector

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_POLICY = REPO_ROOT / "scripts" / "ci" / "test_selection_adjacency.yaml"

_CLOSURE_BLOCK = """
closure:
  candidate_roots: [tests/unit/, tests/nodes/]
  test_file_patterns: ["test_*.py", "*_test.py"]
  ignored_prefixes: [tests/integration/, tests/e2e/]
"""


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def _fake(
        changed_files: list[str], repo_root: Path, package_name: str, **kwargs: object
    ) -> ModelClosureSelection:
        calls.append({"repo_root": repo_root, "package_name": package_name, **kwargs})
        return ModelClosureSelection(selected_files=["tests/unit/cli/"])

    # Patch the packaged primitive itself, so the test follows the values all
    # the way from the policy file to the closure's keyword arguments.
    monkeypatch.setattr(closure_selector, "compute_closure_selection", _fake)
    return calls


def _select(policy: Path, repo_root: Path) -> None:
    detect.compute_selection(
        changed_files=["src/omnibase_core/cli/cli_bootstrap.py"],
        adjacency_path=policy,
        ref_name="pr-branch",
        repo_root=repo_root,
    )


def test_policy_closure_block_reaches_the_closure_primitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.yaml"
    policy.write_text(CORE_POLICY.read_text("utf-8") + _CLOSURE_BLOCK, "utf-8")
    (tmp_path / "tests").mkdir()
    calls = _capture(monkeypatch)

    _select(policy, tmp_path)

    assert len(calls) == 1
    assert calls[0]["candidate_roots"] == ("tests/unit/", "tests/nodes/")
    assert calls[0]["test_file_patterns"] == ("test_*.py", "*_test.py")
    assert calls[0]["ignored_prefixes"] == ("tests/integration/", "tests/e2e/")
    assert calls[0]["repo_root"] == tmp_path
    assert calls[0]["package_name"] == "omnibase_core"


def test_core_policy_passes_the_historical_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: core's own policy file keeps tests/unit/ only."""
    (tmp_path / "tests").mkdir()
    calls = _capture(monkeypatch)

    _select(CORE_POLICY, tmp_path)

    assert len(calls) == 1
    assert calls[0]["candidate_roots"] == ("tests/unit/",)
    assert calls[0]["test_file_patterns"] == ("test_*.py",)
    assert calls[0]["ignored_prefixes"] == ("tests/integration/",)
