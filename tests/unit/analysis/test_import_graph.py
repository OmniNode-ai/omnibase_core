# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from omnibase_core.analysis.import_graph import build_import_graph


@pytest.mark.unit
def test_build_import_graph_resolves_relative_imports(tmp_path):
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "sub.py").write_text("from . import helpers\n", encoding="utf-8")

    graph = build_import_graph(tmp_path)

    assert graph.edges_out["src/pkg/sub.py"] == {"src/pkg/helpers.py"}


@pytest.mark.unit
def test_build_import_graph_resolves_parent_relative_imports(tmp_path):
    package = tmp_path / "src" / "pkg"
    child = package / "child"
    child.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (child / "__init__.py").write_text("", encoding="utf-8")
    (child / "sub.py").write_text("from .. import helpers\n", encoding="utf-8")

    graph = build_import_graph(tmp_path)

    assert graph.edges_out["src/pkg/child/sub.py"] == {"src/pkg/helpers.py"}
