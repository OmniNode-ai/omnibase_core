# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for build_import_graph."""

from pathlib import Path

import pytest

from omnibase_core.analysis.import_graph import build_import_graph

pytestmark = pytest.mark.unit


def test_python_from_import_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("from b import foo\n")
    b.write_text("def foo(): ...\n")
    g = build_import_graph(tmp_path)
    assert "b.py" in g.edges_out["a.py"]


def test_python_bare_import_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("import b\n")
    b.write_text("x = 1\n")
    g = build_import_graph(tmp_path)
    assert "b.py" in g.edges_out["a.py"]


def test_js_require_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.js"
    b = tmp_path / "b.js"
    a.write_text("const x = require('./b');\n")
    b.write_text("module.exports = 1;\n")
    g = build_import_graph(tmp_path)
    assert "b.js" in g.edges_out["a.js"]


def test_js_esm_import_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.js"
    b = tmp_path / "utils.js"
    a.write_text("import x from './utils';\n")
    b.write_text("export const x = 1;\n")
    g = build_import_graph(tmp_path)
    assert "utils.js" in g.edges_out["a.js"]


def test_tsx_import_detected(tmp_path: Path) -> None:
    subdir = tmp_path / "components"
    subdir.mkdir()
    a = tmp_path / "page.tsx"
    b = subdir / "Widget.tsx"
    a.write_text("import Widget from './components/Widget';\n")
    b.write_text("export default function Widget() {}\n")
    g = build_import_graph(tmp_path)
    assert "components/Widget.tsx" in g.edges_out["page.tsx"]


def test_no_self_loop(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("from a import something\n")
    g = build_import_graph(tmp_path)
    assert "a.py" not in g.edges_out.get("a.py", set())


def test_missing_import_target_excluded(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("from nonexistent_module import foo\n")
    g = build_import_graph(tmp_path)
    assert g.edges_out.get("a.py", set()) == set()


def test_python_import_in_subpackage(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    a = pkg / "a.py"
    b = pkg / "b.py"
    a.write_text("from pkg.b import bar\n")
    b.write_text("def bar(): ...\n")
    g = build_import_graph(tmp_path)
    assert "pkg/b.py" in g.edges_out["pkg/a.py"]


def test_python_relative_import_detected(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    a = pkg / "a.py"
    b = pkg / "b.py"
    a.write_text("from . import b\n")
    b.write_text("VALUE = 1\n")
    g = build_import_graph(tmp_path)
    assert "pkg/b.py" in g.edges_out["pkg/a.py"]


def test_python_relative_from_import_submodule_detected(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    nested = pkg / "nested"
    nested.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (nested / "__init__.py").write_text("")
    (nested / "submodule.py").write_text("VALUE = 1\n")
    a = pkg / "a.py"
    a.write_text("from .nested import submodule\n")
    g = build_import_graph(tmp_path)
    assert {"pkg/nested/__init__.py", "pkg/nested/submodule.py"}.issubset(
        g.edges_out["pkg/a.py"]
    )


def test_python_from_import_submodules_detected(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "submodule.py").write_text("VALUE = 1\n")
    (pkg / "other.py").write_text("VALUE = 2\n")
    a = tmp_path / "a.py"
    a.write_text("from pkg import submodule, other\n")
    g = build_import_graph(tmp_path)
    assert {"pkg/__init__.py", "pkg/submodule.py", "pkg/other.py"}.issubset(
        g.edges_out["a.py"]
    )


def test_python_absolute_import_does_not_resolve_sibling(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    a = pkg / "a.py"
    b = pkg / "b.py"
    a.write_text("import b\n")
    b.write_text("VALUE = 1\n")
    g = build_import_graph(tmp_path)
    assert g.edges_out.get("pkg/a.py", set()) == set()


def test_edges_out_keys_are_repo_relative(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("import b\n")
    b.write_text("")
    g = build_import_graph(tmp_path)
    for key in g.edges_out:
        assert not key.startswith("/"), f"Key {key!r} should be repo-relative"


def test_empty_repo(tmp_path: Path) -> None:
    g = build_import_graph(tmp_path)
    assert g.edges_out == {}


def test_js_index_tsx_import_detected(tmp_path: Path) -> None:
    widget = tmp_path / "widget"
    widget.mkdir()
    a = tmp_path / "page.tsx"
    b = widget / "index.tsx"
    a.write_text("import Widget from './widget';\n")
    b.write_text("export default function Widget() {}\n")
    g = build_import_graph(tmp_path)
    assert "widget/index.tsx" in g.edges_out["page.tsx"]


def test_js_comment_and_string_imports_are_ignored(tmp_path: Path) -> None:
    a = tmp_path / "a.js"
    commented = tmp_path / "commented.js"
    quoted = tmp_path / "quoted.js"
    real = tmp_path / "real.js"
    a.write_text(
        "\n".join(
            [
                "// import './commented';",
                "/* require('./quoted') */",
                "const doc = \"require('./quoted')\";",
                "import real from './real';",
            ]
        )
    )
    commented.write_text("export const value = 1;\n")
    quoted.write_text("module.exports = 1;\n")
    real.write_text("export const value = 2;\n")
    g = build_import_graph(tmp_path)
    assert g.edges_out["a.js"] == {"real.js"}


def test_js_multiline_esm_import_detected(tmp_path: Path) -> None:
    a = tmp_path / "a.ts"
    b = tmp_path / "utils.ts"
    a.write_text(
        "\n".join(
            [
                "import {",
                "  foo,",
                "  bar,",
                "} from './utils';",
                "export const value = foo + bar;",
            ]
        )
    )
    b.write_text("export const foo = 1; export const bar = 2;\n")
    g = build_import_graph(tmp_path)
    assert "utils.ts" in g.edges_out["a.ts"]
