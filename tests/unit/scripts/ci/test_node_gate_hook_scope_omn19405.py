# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The node-tree pre-commit gates must fire for a top-level node (OMN-19405).

The three node-tree gates below scan ``omnibase_core/**/nodes/**/contract.yaml``,
where ``**`` also matches zero directories, so a node directly under
``src/omnibase_core/nodes/`` is in their CI scope. Their pre-commit ``files``
regex once read ``src/omnibase_core/.*/nodes/``, which needs at least one
directory between the package and ``nodes/``. A new top-level node therefore
never triggered the hook locally, and the missing provenance stamp surfaced
only as a red CI job. This test pins the hook scope to the scan scope.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIG = _REPO_ROOT / ".pre-commit-config.yaml"

_NODE_GATE_HOOK_IDS = (
    "rsd-provenance-stamp",
    "canonical-handler-shape-ratchet",
    "verify-flip-bundle",
)

_TOP_LEVEL_CONTRACT = "src/omnibase_core/nodes/node_example_compute/contract.yaml"
_NESTED_CONTRACT = (
    "src/omnibase_core/validation/nodes/node_example_compute/contract.yaml"
)


def _hook_files_patterns() -> dict[str, str]:
    config = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    patterns: dict[str, str] = {}
    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook.get("id") in _NODE_GATE_HOOK_IDS:
                patterns[hook["id"]] = hook["files"]
    return patterns


@pytest.mark.unit
def test_every_node_gate_hook_is_present() -> None:
    assert set(_hook_files_patterns()) == set(_NODE_GATE_HOOK_IDS)


@pytest.mark.unit
@pytest.mark.parametrize("hook_id", _NODE_GATE_HOOK_IDS)
@pytest.mark.parametrize("path", [_TOP_LEVEL_CONTRACT, _NESTED_CONTRACT])
def test_node_gate_hook_fires_for_node_contract(hook_id: str, path: str) -> None:
    pattern = _hook_files_patterns()[hook_id]
    assert re.search(pattern, path), f"{hook_id} files regex skips {path}"


@pytest.mark.unit
def test_provenance_hook_fires_for_top_level_stamp() -> None:
    pattern = _hook_files_patterns()["rsd-provenance-stamp"]
    stamp = "src/omnibase_core/nodes/node_example_compute/.rsd_provenance.json"
    assert re.search(pattern, stamp)


@pytest.mark.unit
def test_node_gate_hook_ignores_non_node_source() -> None:
    """Negative control: widening the scope must not match every source file."""
    for hook_id, pattern in _hook_files_patterns().items():
        assert not re.search(pattern, "src/omnibase_core/models/model_x.py"), hook_id
