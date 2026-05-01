# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Static import graph builder for Python and JavaScript/TypeScript files."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

_JS_REQUIRE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_IMPORT = re.compile(
    r"""(?:^|\s)import\s+(?:[\w*{},\s]+\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE
)
_JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
_PY_EXTS = {".py"}


@dataclass
class ImportGraph:
    edges_out: dict[str, set[str]] = field(default_factory=dict)


def build_import_graph(repo_root: Path) -> ImportGraph:
    graph = ImportGraph()
    repo_root = repo_root.resolve()
    python_search_roots = _python_search_roots(repo_root)

    py_files: list[Path] = []
    js_files: list[Path] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in _PY_EXTS:
            py_files.append(path)
        elif path.suffix in _JS_EXTS:
            js_files.append(path)

    for path in py_files:
        rel = str(path.relative_to(repo_root))
        edges = _parse_python_imports(path, repo_root, python_search_roots)
        if edges:
            graph.edges_out[rel] = edges

    for path in js_files:
        rel = str(path.relative_to(repo_root))
        edges = _parse_js_imports(path, repo_root)
        if edges:
            graph.edges_out[rel] = edges

    return graph


def _parse_python_imports(
    path: Path, repo_root: Path, search_roots: list[Path]
) -> set[str]:
    """Extract imported module paths from a Python file, resolved to repo-relative paths."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return set()

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                imports.extend(_relative_import_names(node, path, search_roots))
            elif node.module:
                imports.append(node.module)
                imports.extend(
                    f"{node.module}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )

    edges: set[str] = set()
    src_rel = str(path.relative_to(repo_root))

    for module_name in imports:
        resolved = _resolve_python_module(module_name, repo_root, search_roots)
        if resolved and resolved != src_rel:
            edges.add(resolved)

    return edges


def _python_search_roots(repo_root: Path) -> list[Path]:
    """Return module-resolution roots once per graph build."""
    roots = [repo_root]
    roots.extend(path for path in repo_root.rglob("src") if path.is_dir())
    return roots


def _relative_import_names(
    node: ast.ImportFrom, importing_file: Path, search_roots: list[Path]
) -> list[str]:
    """Convert an ast.ImportFrom relative import into candidate dotted modules."""
    root = _nearest_search_root(importing_file, search_roots)
    if root is None:
        return []
    try:
        package_parts = list(importing_file.parent.relative_to(root).parts)
    except ValueError:
        return []

    if node.level > len(package_parts):
        return []

    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))
        names = [".".join(base_parts)]
        names.extend(
            ".".join([*base_parts, alias.name])
            for alias in node.names
            if alias.name != "*"
        )
        return names
    return [
        ".".join([*base_parts, alias.name]) for alias in node.names if alias.name != "*"
    ]


def _nearest_search_root(path: Path, search_roots: list[Path]) -> Path | None:
    """Return the deepest configured search root containing path."""
    for root in sorted(
        search_roots, key=lambda candidate: len(candidate.parts), reverse=True
    ):
        try:
            path.relative_to(root)
        except ValueError:
            continue
        return root
    return None


def _resolve_python_module(
    module_name: str, repo_root: Path, search_roots: list[Path]
) -> str | None:
    """Convert a dotted module name to a repo-relative file path."""
    # Convert dotted module to path segments
    parts = module_name.split(".")
    candidate_rel = Path(*parts)

    for search_root in search_roots:
        # Try as package (directory with __init__.py)
        pkg_path = search_root / candidate_rel / "__init__.py"
        if pkg_path.is_file():
            return str(pkg_path.relative_to(repo_root))
        # Try as module file
        mod_path = search_root / candidate_rel.with_suffix(".py")
        if mod_path.is_file():
            return str(mod_path.relative_to(repo_root))

    return None


def _parse_js_imports(path: Path, repo_root: Path) -> set[str]:
    """Extract imported module paths from a JS/TS file, resolved to repo-relative paths."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()

    src_rel = str(path.relative_to(repo_root))
    edges: set[str] = set()

    specifiers: list[str] = []
    for m in _JS_REQUIRE.finditer(source):
        specifiers.append(m.group(1))
    for m in _JS_IMPORT.finditer(source):
        specifiers.append(m.group(1))

    for spec in specifiers:
        if not spec.startswith("."):
            continue  # skip bare module specifiers (node_modules etc.)
        resolved = _resolve_js_specifier(spec, path, repo_root)
        if resolved and resolved != src_rel:
            edges.add(resolved)

    return edges


def _resolve_js_specifier(
    spec: str, importing_file: Path, repo_root: Path
) -> str | None:
    """Resolve a relative JS import specifier to a repo-relative path."""
    import_dir = importing_file.parent
    candidate = (import_dir / spec).resolve()

    # Try exact path, then with common extensions
    for attempt in [
        candidate,
        candidate.with_suffix(".js"),
        candidate.with_suffix(".jsx"),
        candidate.with_suffix(".ts"),
        candidate.with_suffix(".tsx"),
        candidate / "index.js",
        candidate / "index.ts",
    ]:
        if attempt.is_file():
            try:
                return str(attempt.relative_to(repo_root))
            except ValueError:
                return None

    return None
