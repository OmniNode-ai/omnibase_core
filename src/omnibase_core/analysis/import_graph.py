# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Static import graph builder for Python and JavaScript/TypeScript files."""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

_JS_EXTS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
_PY_EXTS = (".py",)

# Directories that never contain first-party repo source. Descending into them
# is both a correctness bug (vendored site-packages copies of a first-party
# module shadow the real `src/` file when resolving a dotted import, so real
# consumers get undercounted) and the dominant cost of a cold graph build:
# an unpruned walk of a synced worktree AST-parses thousands of dependency
# files. See OMN-15431.
_PRUNED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".tox",
        ".nox",
        ".eggs",
        "site-packages",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".onex_state",
        "htmlcov",
    }
)


@dataclass
class ImportGraph:
    """Repo-relative static import edges keyed by importing source file."""

    edges_out: dict[str, set[str]] = field(default_factory=dict)


def _to_repo_rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def build_import_graph(repo_root: Path) -> ImportGraph:
    """Build a static import graph for Python and JS/TS files under repo_root."""
    graph = ImportGraph()
    repo_root = repo_root.resolve()
    py_files, js_files, src_dirs = _walk_source_tree(repo_root)
    python_search_roots = [repo_root, *src_dirs]

    for path in py_files:
        rel = _to_repo_rel(path, repo_root)
        edges = _parse_python_imports(path, repo_root, python_search_roots)
        if edges:
            graph.edges_out[rel] = edges

    for path in js_files:
        rel = _to_repo_rel(path, repo_root)
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
    src_rel = _to_repo_rel(path, repo_root)

    for module_name in imports:
        resolved = _resolve_python_module(module_name, repo_root, search_roots)
        if resolved and resolved != src_rel:
            edges.add(resolved)

    return edges


def _is_pruned_dir(path: Path, repo_root: Path) -> bool:
    """Return True for directories that hold no first-party repo source."""
    name = path.name
    if name in _PRUNED_DIR_NAMES or name.endswith(".egg-info"):
        return True
    # A nested checkout (submodule, sibling clone, or git worktree parked inside
    # the tree) carries its own history and is not this repo's source.
    return path != repo_root and (path / ".git").exists()


def _walk_source_tree(repo_root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Walk repo_root once, returning (python files, JS/TS files, ``src`` dirs).

    A single pruned walk replaces the previous pair of unpruned ``rglob`` passes.
    Pruning happens in-place on ``os.walk``'s dirnames so excluded subtrees are
    never descended into at all, rather than being enumerated and then filtered.
    """
    py_files: list[Path] = []
    js_files: list[Path] = []
    src_dirs: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        current = Path(dirpath)
        dirnames[:] = [
            name for name in dirnames if not _is_pruned_dir(current / name, repo_root)
        ]
        src_dirs.extend(current / name for name in dirnames if name == "src")
        for name in filenames:
            path = current / name
            if path.suffix in _PY_EXTS:
                py_files.append(path)
            elif path.suffix in _JS_EXTS:
                js_files.append(path)

    return py_files, js_files, src_dirs


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
            return _to_repo_rel(pkg_path, repo_root)
        # Try as module file
        mod_path = search_root / candidate_rel.with_suffix(".py")
        if mod_path.is_file():
            return _to_repo_rel(mod_path, repo_root)

    return None


def _parse_js_imports(path: Path, repo_root: Path) -> set[str]:
    """Extract imported module paths from a JS/TS file, resolved to repo-relative paths."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()

    src_rel = _to_repo_rel(path, repo_root)
    edges: set[str] = set()

    source = _strip_js_comments(source)
    specifiers = [
        *_iter_js_require_specifiers(source),
        *_iter_js_import_specifiers(source),
    ]

    for spec in specifiers:
        if not spec.startswith("."):
            continue  # skip bare module specifiers (node_modules etc.)
        resolved = _resolve_js_specifier(spec, path, repo_root)
        if resolved and resolved != src_rel:
            edges.add(resolved)

    return edges


def _strip_js_comments(source: str) -> str:
    """Remove JS comments without treating comment markers inside strings as comments."""
    output: list[str] = []
    i = 0
    quote: str | None = None
    escape = False
    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""
        if quote is not None:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            i += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
            output.append(char)
            i += 1
            continue
        if char == "/" and next_char == "/":
            while i < len(source) and source[i] != "\n":
                output.append(" ")
                i += 1
            continue
        if char == "/" and next_char == "*":
            output.extend((" ", " "))
            i += 2
            while i < len(source) - 1 and not (
                source[i] == "*" and source[i + 1] == "/"
            ):
                output.append("\n" if source[i] == "\n" else " ")
                i += 1
            if i < len(source) - 1:
                output.extend((" ", " "))
                i += 2
            continue
        output.append(char)
        i += 1
    return "".join(output)


def _iter_js_require_specifiers(source: str) -> list[str]:
    """Return require() specifiers that appear outside JS string literals."""
    specifiers: list[str] = []
    i = 0
    quote: str | None = None
    escape = False
    while i < len(source):
        char = source[i]
        if quote is not None:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            i += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            i += 1
            continue
        if not source.startswith("require", i):
            i += 1
            continue
        before = source[i - 1] if i > 0 else ""
        after = source[i + len("require")] if i + len("require") < len(source) else ""
        if before.isidentifier() or after.isidentifier():
            i += 1
            continue
        cursor = i + len("require")
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source) or source[cursor] != "(":
            i += 1
            continue
        cursor += 1
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source) or source[cursor] not in {"'", '"'}:
            i += 1
            continue
        spec_quote = source[cursor]
        cursor += 1
        start = cursor
        while cursor < len(source):
            if source[cursor] == "\\":
                cursor += 2
                continue
            if source[cursor] == spec_quote:
                specifiers.append(source[start:cursor])
                break
            cursor += 1
        i = max(cursor + 1, i + 1)
    return specifiers


def _iter_js_import_specifiers(source: str) -> list[str]:
    """Return static import specifiers that appear outside JS string literals."""
    specifiers: list[str] = []
    i = 0
    quote: str | None = None
    escape = False
    while i < len(source):
        char = source[i]
        if quote is not None:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            i += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            i += 1
            continue
        if not source.startswith("import", i):
            i += 1
            continue
        before = source[i - 1] if i > 0 else ""
        after = source[i + len("import")] if i + len("import") < len(source) else ""
        if before.isidentifier() or after.isidentifier():
            i += 1
            continue
        cursor = i + len("import")
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor < len(source) and source[cursor] == "(":
            i = cursor + 1
            continue
        if literal := _read_js_string_literal(source, cursor):
            specifier, end = literal
            specifiers.append(specifier)
            i = end
            continue
        from_pos = _find_js_keyword(source, "from", cursor)
        if from_pos is None:
            i += 1
            continue
        cursor = from_pos + len("from")
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if literal := _read_js_string_literal(source, cursor):
            specifier, end = literal
            specifiers.append(specifier)
            i = end
            continue
        i += 1
    return specifiers


def _read_js_string_literal(source: str, cursor: int) -> tuple[str, int] | None:
    """Read a quoted JavaScript string literal at cursor."""
    if cursor >= len(source) or source[cursor] not in {"'", '"'}:
        return None
    quote = source[cursor]
    cursor += 1
    start = cursor
    while cursor < len(source):
        if source[cursor] == "\\":
            cursor += 2
            continue
        if source[cursor] == quote:
            return source[start:cursor], cursor + 1
        cursor += 1
    return None


def _find_js_keyword(source: str, keyword: str, cursor: int) -> int | None:
    """Find a keyword before the next statement boundary, ignoring strings."""
    quote: str | None = None
    escape = False
    while cursor < len(source):
        char = source[cursor]
        if quote is not None:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            cursor += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            cursor += 1
            continue
        if char == ";":
            return None
        if source.startswith(keyword, cursor):
            before = source[cursor - 1] if cursor > 0 else ""
            after = (
                source[cursor + len(keyword)]
                if cursor + len(keyword) < len(source)
                else ""
            )
            if not before.isidentifier() and not after.isidentifier():
                return cursor
        cursor += 1
    return None


def _resolve_js_specifier(
    spec: str, importing_file: Path, repo_root: Path
) -> str | None:
    """Resolve a relative JS import specifier to a repo-relative path."""
    import_dir = importing_file.parent
    candidate = (import_dir / spec).resolve()

    attempts = [candidate]
    attempts.extend(candidate.with_suffix(ext) for ext in _JS_EXTS)
    attempts.extend(candidate / f"index{ext}" for ext in _JS_EXTS)

    for attempt in attempts:
        if attempt.is_file():
            try:
                return _to_repo_rel(attempt, repo_root)
            except ValueError:
                return None

    return None
