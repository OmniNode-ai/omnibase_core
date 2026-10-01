# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One Python file: its imports, its functions and their local events (OMN-20295)."""

from __future__ import annotations

import ast
import posixpath
from collections.abc import Iterator, Sequence

from omnibase_core.nodes.node_direct_model_call_check_compute._constants import (
    _HTTP_CLIENT_MODULES,
    _Event,
)


def _module_name(path: str) -> str:
    stem = path.removesuffix(".pyi").removesuffix(".py")
    if stem.startswith("src/"):
        stem = stem[4:]
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem.replace("/", ".")


def _param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args)]
    if args.vararg is not None:
        names.append("*" + args.vararg.arg)
    names.extend(a.arg for a in args.kwonlyargs)
    return tuple(names)


class _Module:
    """One Python file: its imports, its functions and their environments."""

    def __init__(
        self,
        path: str,
        tree: ast.Module,
        index: dict[str, str],
        siblings: dict[str, dict[str, str]],
    ) -> None:
        self.path = path
        self.tree = tree
        self.name = _module_name(path)
        self.imports: dict[str, str] = {}
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.classes: set[str] = set()
        self.owner: dict[str, str] = {}
        self.decorators: set[int] = set()
        self.http_client = False
        self.aliases: dict[str, str] = {}
        self._index = index
        self._siblings = siblings
        self._collect(tree.body, prefix="", owner_class=None)
        self._collect_imports()
        roots = {v.split(".", 1)[0] for v in self.imports.values()}
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                name_node, value = stmt.targets[0], stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                name_node, value = stmt.target, stmt.value
            else:
                continue
            if not isinstance(name_node, ast.Name):
                continue
            if isinstance(value, ast.Name) and value.id in self.functions:
                self.aliases[name_node.id] = value.id
            elif isinstance(value, (ast.Name, ast.Attribute)):
                dotted = self.dotted(value)
                if dotted is not None and dotted.split(".", 1)[0] in roots:
                    self.imports.setdefault(name_node.id, dotted)
        self.http_client = any(
            target == client or target.startswith(client + ".")
            for target in self.imports.values()
            for client in _HTTP_CLIENT_MODULES
        )

    def _collect(
        self, body: Sequence[ast.stmt], prefix: str, owner_class: str | None
    ) -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefix + stmt.name
                self.functions[qual] = stmt
                if owner_class is not None:
                    self.owner[qual] = owner_class
                self._collect(stmt.body, qual + ".", None)
            elif isinstance(stmt, ast.ClassDef):
                qual = prefix + stmt.name
                self.classes.add(qual)
                self._collect(stmt.body, qual + ".", qual)
            elif isinstance(stmt, (ast.If, ast.Try, ast.With, ast.AsyncWith)):
                for block in _blocks(stmt):
                    self._collect(block, prefix, owner_class)

    def _resolve_import(self, dotted: str) -> str:
        head = dotted.split(".", 1)[0]
        if dotted in self._index or head in self._index:
            return dotted
        sibling = self._siblings.get(posixpath.dirname(self.path), {}).get(head)
        if sibling is not None:
            tail = dotted[len(head) :]
            return _module_name(sibling) + tail
        return dotted

    def _collect_imports(self) -> None:
        package = self.name.split(".")
        if not self.path.endswith("__init__.py"):
            package = package[:-1]
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.decorators.update(
                    id(d) for d in node.decorator_list if isinstance(d, ast.Call)
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = self._resolve_import(alias.name)
                    if alias.asname:
                        self.imports[alias.asname] = target
                    else:
                        head = alias.name.split(".", 1)[0]
                        self.imports.setdefault(head, self._resolve_import(head))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = package[: len(package) - (node.level - 1)]
                    base = ".".join(
                        [*base_parts, node.module] if node.module else base_parts
                    )
                else:
                    base = self._resolve_import(node.module or "")
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = f"{base}.{alias.name}"

    def dotted(self, expr: ast.expr) -> str | None:
        """The import-resolved dotted name of a Name/Attribute chain."""
        parts: list[str] = []
        node: ast.expr = expr
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        root = self.imports.get(node.id, node.id)
        return ".".join([root, *reversed(parts)])


def _blocks(stmt: ast.stmt) -> list[Sequence[ast.stmt]]:
    if isinstance(stmt, ast.If):
        return [stmt.body, stmt.orelse]
    if isinstance(stmt, ast.Try):
        return [
            stmt.body,
            *(h.body for h in stmt.handlers),
            stmt.orelse,
            stmt.finalbody,
        ]
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return [stmt.body]
    return []


def _own_nodes(root: ast.AST) -> Iterator[ast.AST]:
    """Walk ``root`` without entering nested function or class bodies."""
    stack: list[ast.AST] = list(ast.iter_child_nodes(root))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Lambda):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _events(statements: Sequence[ast.stmt]) -> dict[str, list[_Event]]:
    """Every assignment and mutation of each local name, in source order."""
    events: dict[str, list[_Event]] = {}

    def add(name: str, event: _Event) -> None:
        events.setdefault(name, []).append(event)

    for stmt in statements:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            if stmt.value is None:
                continue
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    add(target.id, ("assign", stmt.value))
                elif (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                ):
                    add(target.value.id, ("key", target.slice.value))
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        if isinstance(element, ast.Name):
                            add(element.id, ("opaque", None))
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            add(stmt.target.id, ("aug", stmt.value))
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if isinstance(item.optional_vars, ast.Name):
                    add(item.optional_vars.id, ("assign", item.context_expr))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                kind = {
                    "append": "append",
                    "extend": "extend",
                    "update": "keys",
                    "setdefault": "keys",
                }.get(func.attr)
                if kind is not None:
                    add(func.value.id, (kind, stmt.value))
    return events
