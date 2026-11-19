# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Keep the nodes that moved to omnimarket out of core (OMN-23932)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
NODES_DIR = REPO_ROOT / "src" / "omnibase_core" / "nodes"
PYPROJECT = REPO_ROOT / "pyproject.toml"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
EXPORTED_HOOKS = REPO_ROOT / ".pre-commit-hooks.yaml"
MOVED_NODE_NAMES = [
    "node_dev_tag_lineage_effect",
    "node_effect_backends_check_compute",
]


def _hook_mappings(path: Path) -> list[dict[str, object]]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list), "expected a YAML list of hook mappings"
    result: list[dict[str, object]] = []
    for hook in loaded:
        assert isinstance(hook, dict), "expected a YAML mapping of hooks"
        result.append(hook)
    return result


@pytest.mark.parametrize("node_name", MOVED_NODE_NAMES)
def test_core_holds_no_directory_for_a_moved_node(node_name: str) -> None:
    """Catch a moved node directory returning to the core node tree."""
    assert not (NODES_DIR / node_name).exists()


@pytest.mark.parametrize("node_name", MOVED_NODE_NAMES)
def test_core_registers_no_moved_node_entry_point(node_name: str) -> None:
    """Catch a moved node reappearing under the onex.nodes entry point group."""
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    group = pyproject["project"]["entry-points"]["onex.nodes"]
    assert isinstance(group, dict), "expected a mapping of entry points"
    assert node_name not in group


@pytest.mark.parametrize("node_name", MOVED_NODE_NAMES)
def test_no_hook_runs_a_moved_core_module(node_name: str) -> None:
    """Catch a hook entry still pointing at a moved core module."""
    module = f"omnibase_core.nodes.{node_name}"
    for config_path in (PRECOMMIT_CONFIG, EXPORTED_HOOKS):
        assert module not in config_path.read_text(encoding="utf-8")


def test_dev_tag_lineage_hook_runs_the_omnimarket_module() -> None:
    """Catch the lineage hook still pointing at the retired core module."""
    hooks = _hook_mappings(EXPORTED_HOOKS)
    matches = [hook for hook in hooks if hook.get("id") == "check-dev-tag-lineage"]
    assert len(matches) == 1
    entry = matches[0].get("entry")
    assert isinstance(entry, str), "expected a string hook entry"
    assert (
        "omnimarket.nodes.node_dev_tag_lineage_effect.runtime_dev_tag_lineage" in entry
    )
