# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest

from scripts.ci.test_selection_loader import (
    ModelAdjacencyMap,
    load_adjacency_map,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_load_adjacency_map_parses_repo_yaml() -> None:
    config_path = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
    config = load_adjacency_map(config_path)
    assert isinstance(config, ModelAdjacencyMap)
    assert config.schema_version == 1
    assert "models" in config.shared_modules
    assert "models" in config.adjacency


def test_load_rejects_unknown_shared_module(tmp_path: Path) -> None:
    bad_yaml = """
schema_version: 1
shared_modules: [does_not_exist]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: []
adjacency:
  nodes: { reverse_deps: [] }
"""
    tmp = tmp_path / "bad_adj.yaml"
    tmp.write_text(bad_yaml)
    with pytest.raises(ValueError, match="shared_module 'does_not_exist'"):
        load_adjacency_map(tmp)


def test_every_src_module_has_adjacency_entry() -> None:
    config_path = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
    config = load_adjacency_map(config_path)
    src_root = REPO_ROOT / "src/omnibase_core"
    src_modules = {
        p.name for p in src_root.iterdir() if p.is_dir() and not p.name.startswith("_")
    }
    missing = src_modules - set(config.adjacency.keys())
    assert not missing, f"Modules missing adjacency entry: {missing}"
