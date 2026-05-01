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
    """Build a repo-relative import graph for Python and JS/TS source files.

    Args:
        repo_root: Repository root whose source files should be scanned.

    Returns:
        ImportGraph mapping each importing file to repo-relative imported files.
    """
    graph = ImportGraph()
    repo_root = repo_root.resolve()

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
        edges = _parse_python_imports(path, repo_root)
        if edges:
            graph.edges_out[rel] = edges

    for path in js_files:
        rel = str(path.relative_to(repo_root))
        edges = _parse_js_imports(path, repo_root)
        if edges:
            graph.edges_out[rel] = edges

    return graph


def _parse_python_imports(path: Path, repo_root: Path) -> set[str]:
    """Extract imported module paths from a Python file, resolved to repo-relative paths."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_python_module(alias.name, path, repo_root)
                if resolved:
                    imports.add(resolved)
        elif isinstance(node, ast.ImportFrom):
            imports.update(_resolve_python_import_from(node, path, repo_root))

    edges: set[str] = set()
    src_rel = str(path.relative_to(repo_root))

    for imported_rel in imports:
        if imported_rel != src_rel:
            edges.add(imported_rel)

    return edges


def _resolve_python_import_from(
    node: ast.ImportFrom, importing_file: Path, repo_root: Path
) -> set[str]:
    if node.level == 0:
        return _resolve_absolute_import_from(node, importing_file, repo_root)

    package_dir = importing_file.parent
    base_dir = package_dir
    for _ in range(node.level - 1):
        base_dir = base_dir.parent

    module_parts = node.module.split(".") if node.module else []
    module_base = base_dir.joinpath(*module_parts)
    resolved: set[str] = set()
    if node.module:
        module_resolved = _resolve_python_path_candidate(module_base, repo_root)
        if module_resolved:
            resolved.add(module_resolved)

    for alias in node.names:
        if alias.name == "*":
            continue
        alias_candidate = module_base.joinpath(*alias.name.split("."))
        alias_resolved = _resolve_python_path_candidate(alias_candidate, repo_root)
        if alias_resolved:
            resolved.add(alias_resolved)

    return resolved


def _resolve_absolute_import_from(
    node: ast.ImportFrom, importing_file: Path, repo_root: Path
) -> set[str]:
    resolved: set[str] = set()
    if node.module:
        module_resolved = _resolve_python_module(node.module, importing_file, repo_root)
        if module_resolved:
            resolved.add(module_resolved)
        for alias in node.names:
            if alias.name == "*":
                continue
            alias_module = f"{node.module}.{alias.name}"
            alias_resolved = _resolve_python_module(
                alias_module, importing_file, repo_root
            )
            if alias_resolved:
                resolved.add(alias_resolved)
    return resolved


def _resolve_python_path_candidate(candidate: Path, repo_root: Path) -> str | None:
    pkg_path = candidate / "__init__.py"
    if pkg_path.is_file():
        return str(pkg_path.relative_to(repo_root))

    mod_path = candidate.with_suffix(".py")
    if mod_path.is_file():
        return str(mod_path.relative_to(repo_root))

    return None


def _resolve_python_module(
    module_name: str, importing_file: Path, repo_root: Path
) -> str | None:
    """Convert a dotted module name to a repo-relative file path."""
    # Convert dotted module to path segments
    parts = module_name.split(".")
    candidate_rel = Path(*parts)

    # Search from repo root and common src layouts
    search_roots = [repo_root]
    for src_dir in repo_root.rglob("src"):
        if src_dir.is_dir():
            search_roots.append(src_dir)
            break

    for search_root in search_roots:
        # Try as package (directory with __init__.py)
        pkg_path = search_root / candidate_rel / "__init__.py"
        if pkg_path.is_file():
            return str(pkg_path.relative_to(repo_root))
        # Try as module file
        mod_path = search_root / candidate_rel.with_suffix(".py")
        if mod_path.is_file():
            return str(mod_path.relative_to(repo_root))

    # Try relative to the importing file's directory
    import_dir = importing_file.parent
    for search_root in [import_dir]:
        pkg_path = search_root / candidate_rel / "__init__.py"
        if pkg_path.is_file():
            return str(pkg_path.relative_to(repo_root))
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
