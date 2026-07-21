# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from pathlib import Path

import pytest

from scripts.ci.test_selection_loader import (
    ModelAdjacencyMap,
    load_adjacency_map,
)

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


# ---------------------------------------------------------------------------
# OMN-14897: the loader FAILS on a duplicate mapping key instead of silently
# keeping the last occurrence (a fail-open shape — a duplicate with a *narrower*
# reverse_deps would be dropped with no signal). The check has to run at parse
# time, before the dict collapses; the ModelAdjacencyMap set-equality validator
# cannot see a key that has already been deduplicated.
# ---------------------------------------------------------------------------


def test_duplicate_adjacency_key_is_rejected(tmp_path: Path) -> None:
    dup_yaml = """
schema_version: 1
shared_modules: [models]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: []
adjacency:
  models: { reverse_deps: [nodes] }
  nodes: { reverse_deps: [] }
  models: { reverse_deps: [] }
"""
    tmp = tmp_path / "dup_adj.yaml"
    tmp.write_text(dup_yaml)
    with pytest.raises(ValueError, match="duplicate key 'models'"):
        load_adjacency_map(tmp)


def test_duplicate_key_with_differing_reverse_deps_does_not_silently_win(
    tmp_path: Path,
) -> None:
    # The exact latent hazard C1.3 describes: a second `nodes:` with a DIFFERENT
    # reverse_deps must not silently replace the first. Absent the guard, YAML
    # last-wins would keep `reverse_deps: []` and the selector would compute a
    # narrower closure than intended, with no error.
    dup_yaml = """
schema_version: 1
shared_modules: [models]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: []
adjacency:
  models: { reverse_deps: [] }
  nodes: { reverse_deps: [models] }
  nodes: { reverse_deps: [] }
"""
    tmp = tmp_path / "dup_diff_adj.yaml"
    tmp.write_text(dup_yaml)
    with pytest.raises(ValueError, match="duplicate key 'nodes'"):
        load_adjacency_map(tmp)


def test_repo_adjacency_has_no_duplicate_keys() -> None:
    # Regression for the removed `dispatch`/`analysis` duplicates: the real file
    # must load clean (47 modules, no last-wins drop).
    config_path = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
    config = load_adjacency_map(config_path)
    assert len(config.adjacency) == 47
