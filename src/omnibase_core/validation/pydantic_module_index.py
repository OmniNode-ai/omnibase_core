# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST module index and canonical module/path resolution helpers."""

import ast
from pathlib import Path


def module_for_path(path: Path) -> tuple[str, Path]:
    """Return the dotted module name for *path* and its ``sys.path`` root."""
    resolved = path.resolve()
    parts_list = resolved.parts
    src_indices = [i for i, part in enumerate(parts_list) if part == "src"]

    if src_indices:
        root = Path(*parts_list[: src_indices[-1] + 1])
        parts = list(parts_list[src_indices[-1] + 1 : -1])
    else:
        parts = []
        directory = resolved.parent
        while (directory / "__init__.py").exists():
            parts.insert(0, directory.name)
            directory = directory.parent
        root = directory

    stem = resolved.stem
    if stem != "__init__":
        parts.append(stem)
    return ".".join(parts), root


class _ModuleIndex:
    """Parsed view of one module: its classes and imported class bindings."""

    __slots__ = ("classes", "imports", "module", "path")

    def __init__(self, path: Path, module: str, tree: ast.Module) -> None:
        self.path = path
        self.module = module
        self.classes: dict[str, ast.ClassDef] = {}
        self.imports: dict[str, tuple[str, str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.setdefault(node.name, node)

        package = module.rsplit(".", 1)[0] if "." in module else ""
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[alias.asname or alias.name.split(".")[0]] = (
                        alias.name,
                        "",
                    )
            elif isinstance(node, ast.ImportFrom):
                source = _absolute_import_module(node, package)
                if source is None:
                    continue
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = (source, alias.name)


def _absolute_import_module(node: ast.ImportFrom, package: str) -> str | None:
    """Resolve a possibly relative import to an absolute dotted module."""
    if not node.level:
        return node.module
    parts = package.split(".") if package else []
    if node.level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (node.level - 1)]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base) if base else None


def parse_module(path: Path, module: str) -> _ModuleIndex | None:
    """Parse a module into its AST index, returning None for unreadable input."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return None
    return _ModuleIndex(path, module, tree)
