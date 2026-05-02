# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json
from pathlib import Path

import pytest

from omnibase_core.analysis.consumer_graph import build_consumer_graph


@pytest.mark.unit
def test_build_consumer_graph_counts_imports(tmp_path: Path) -> None:
    # a.py imports b.py; c.py imports b.py — b should have count 2
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "c.py").write_text("import b\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert "b.py" in result
    assert result["b.py"] == 2


@pytest.mark.unit
def test_build_consumer_graph_unreferenced_file_absent(tmp_path: Path) -> None:
    (tmp_path / "standalone.py").write_text("x = 1\n", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert "standalone.py" not in result


@pytest.mark.unit
def test_build_consumer_graph_cache_hit(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text("import y\n", encoding="utf-8")
    (tmp_path / "y.py").write_text("", encoding="utf-8")

    # Prime cache by calling once (no git repo, sha=None)
    build_consumer_graph(tmp_path)

    cache_path = tmp_path / ".onex_state" / "consumer-graph.json"
    assert cache_path.is_file()

    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "y.py" in cached


@pytest.mark.unit
def test_build_consumer_graph_sha_mismatch_recomputes(tmp_path: Path) -> None:
    # Write a stale cache with a known SHA
    cache_path = tmp_path / ".onex_state" / "consumer-graph.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    stale = {"sha": "deadbeef" * 5, "old_file.py": 99}
    cache_path.write_text(json.dumps(stale), encoding="utf-8")

    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    # old stale entry must be gone; real computation used
    assert "old_file.py" not in result
    assert result.get("b.py") == 1


@pytest.mark.unit
def test_build_consumer_graph_returns_dict_str_int(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("import util\n", encoding="utf-8")
    (tmp_path / "util.py").write_text("", encoding="utf-8")

    result = build_consumer_graph(tmp_path)

    assert isinstance(result, dict)
    for k, v in result.items():
        assert isinstance(k, str)
        assert isinstance(v, int)
