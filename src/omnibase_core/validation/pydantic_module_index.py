# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST module index and canonical module/path resolution helpers."""

import ast
from pathlib import Path

BINDING_IMPORT = "import"
BINDING_CLASS = "class"
BINDING_ASSIGN = "assign"
BINDING_OPAQUE = "opaque"

# (lineno, kind, module, name, node): an import binds ``module``/``name`` (``name`` is
# empty for a plain module import), a class or assignment binds ``node`` (the
# ``ast.ClassDef`` or the assigned value), and an opaque binding is any other rebinding
# whose value the scanner does not follow.
Binding = tuple[int, str, str, str, ast.AST | None]


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

    __slots__ = ("bindings", "classes", "imports", "module", "path")

    def __init__(self, path: Path, module: str, tree: ast.Module) -> None:
        self.path = path
        self.module = module
        self.classes: dict[str, ast.ClassDef] = {}
        self.imports: dict[str, tuple[str, str]] = {}
        self.bindings: dict[str, list[Binding]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.setdefault(node.name, node)

        package = module.rsplit(".", 1)[0] if "." in module else ""
        self._collect_bindings(tree.body, package)
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

    def binding_at(self, name: str, lineno: int) -> Binding | None:
        """Return the module-scope binding of *name* in force just before *lineno*."""
        latest: Binding | None = None
        for binding in self.bindings.get(name, ()):
            if binding[0] >= lineno:
                break
            latest = binding
        return latest

    def _bind(self, name: str, binding: Binding) -> None:
        self.bindings.setdefault(name, []).append(binding)

    def _collect_bindings(self, body: list[ast.stmt], package: str) -> None:
        """Record module-scope bindings in source order, straight through blocks."""
        for stmt in body:
            line = stmt.lineno
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.asname:
                        self._bind(
                            alias.asname,
                            (line, BINDING_IMPORT, alias.name, "", None),
                        )
                    else:
                        root = alias.name.split(".")[0]
                        self._bind(root, (line, BINDING_IMPORT, root, "", None))
            elif isinstance(stmt, ast.ImportFrom):
                source = _absolute_import_module(stmt, package)
                for alias in stmt.names:
                    if source is None or alias.name == "*":
                        continue
                    self._bind(
                        alias.asname or alias.name,
                        (line, BINDING_IMPORT, source, alias.name, None),
                    )
            elif isinstance(stmt, ast.ClassDef):
                self._bind(stmt.name, (line, BINDING_CLASS, "", "", stmt))
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self._bind(
                            target.id, (line, BINDING_ASSIGN, "", "", stmt.value)
                        )
                    else:
                        self._bind_opaque(target, line)
            elif isinstance(stmt, ast.AnnAssign):
                if stmt.value is not None and isinstance(stmt.target, ast.Name):
                    self._bind(
                        stmt.target.id, (line, BINDING_ASSIGN, "", "", stmt.value)
                    )
            elif isinstance(stmt, ast.AugAssign):
                self._bind_opaque(stmt.target, line)
            elif isinstance(stmt, ast.Delete):
                for target in stmt.targets:
                    self._bind_opaque(target, line)
            elif isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
                self._bind(stmt.name, (line, BINDING_OPAQUE, "", "", None))
            elif isinstance(stmt, ast.For | ast.AsyncFor):
                self._bind_opaque(stmt.target, line)
            elif isinstance(stmt, ast.With | ast.AsyncWith):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        self._bind_opaque(item.optional_vars, line)
            for block in _nested_blocks(stmt):
                self._collect_bindings(block, package)

    def _bind_opaque(self, target: ast.AST, lineno: int) -> None:
        for node in ast.walk(target):
            if isinstance(node, ast.Name):
                self._bind(node.id, (lineno, BINDING_OPAQUE, "", "", None))


def _nested_blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    """Return the statement blocks nested directly in a module-scope compound statement."""
    if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return []
    blocks: list[list[ast.stmt]] = []
    for field in ("body", "orelse", "finalbody"):
        block = getattr(stmt, field, None)
        if isinstance(block, list) and all(isinstance(n, ast.stmt) for n in block):
            blocks.append(block)
    blocks.extend(handler.body for handler in getattr(stmt, "handlers", ()))
    blocks.extend(case.body for case in getattr(stmt, "cases", ()))
    return blocks


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
