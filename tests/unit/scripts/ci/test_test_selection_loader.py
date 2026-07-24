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


def test_repo_adjacency_map_is_retired_empty() -> None:
    # OMN-14921: the checked-in YAML no longer carries an `adjacency:` block —
    # test selection is computed from the live import graph, not this map.
    # Positive-evidence check that the retirement actually landed (not just
    # that the guard below exists).
    config_path = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
    config = load_adjacency_map(config_path)
    assert config.adjacency == {}


def test_load_rejects_reintroduced_adjacency_map(tmp_path: Path) -> None:
    # OMN-14921 "cannot silently go stale" guard: ANY adjacency entry — even a
    # single, otherwise-plausible one — fails loud at load time. A hand-curated
    # reverse_deps map cannot be kept honest against the real import graph (26
    # of 40 prior declarations were already false); do not resurrect one.
    bad_yaml = """
schema_version: 1
shared_modules: [models]
thresholds:
  modules_changed_for_full_suite: 8
test_infrastructure_paths: []
adjacency:
  nodes: { reverse_deps: [] }
"""
    tmp = tmp_path / "bad_adj.yaml"
    tmp.write_text(bad_yaml)
    with pytest.raises(ValueError, match="adjacency map is retired"):
        load_adjacency_map(tmp)


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


def test_repo_yaml_loads_clean_no_duplicate_keys() -> None:
    # The real file must still load clean under the duplicate-key-rejecting
    # loader (OMN-14897) even with the adjacency block retired (OMN-14921) —
    # shared_modules/thresholds/test_infrastructure_paths are the remaining
    # surface a duplicate key could silently corrupt.
    config_path = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
    config = load_adjacency_map(config_path)
    assert len(config.shared_modules) == 6
