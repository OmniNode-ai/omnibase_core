# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Static AST resolver for effective Pydantic ``extra`` configuration."""

import ast
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.validation.model_extra_forbid_finding import (
    STATUS_EXPLICIT_ALLOW,
    STATUS_EXPLICIT_FORBID,
    STATUS_EXPLICIT_IGNORE,
    STATUS_IMPLICIT_DEFAULT,
    STATUS_UNRESOLVED,
)
from omnibase_core.validation.pydantic_module_index import (
    _ModuleIndex,
    module_for_path,
    parse_module,
)

_UNKNOWN_EXTRA = "<unknown>"
_PYDANTIC_MODEL_BASES: frozenset[str] = frozenset(
    {"BaseModel", "BaseSettings", "RootModel"}
)
_EXEMPT_BASES: frozenset[str] = frozenset({"RootModel"})
_STATUS_BY_EXTRA: dict[str, str] = {
    "forbid": STATUS_EXPLICIT_FORBID,
    "ignore": STATUS_EXPLICIT_IGNORE,
    "allow": STATUS_EXPLICIT_ALLOW,
}


class _StaticResolver:
    """Resolve a class's effective ``extra`` through its parsed base graph."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._by_module: dict[str, _ModuleIndex | None] = {}
        self._sys_roots: list[Path] = []
        for root in roots:
            resolved = root.resolve()
            base = resolved if resolved.is_dir() else resolved.parent
            _, sys_root = module_for_path(base / "__probe__.py")
            if sys_root not in self._sys_roots:
                self._sys_roots.append(sys_root)

    def index_for_path(self, path: Path) -> _ModuleIndex | None:
        module, sys_root = module_for_path(path)
        if sys_root not in self._sys_roots:
            self._sys_roots.append(sys_root)
        cached = self._by_module.get(module)
        if cached is not None:
            return cached
        index = parse_module(path, module)
        self._by_module[module] = index
        return index

    def _index_for_module(self, module: str) -> _ModuleIndex | None:
        if module not in self._by_module:
            self._by_module[module] = None
            path = self._locate(module)
            if path is not None:
                self._by_module[module] = parse_module(path, module)
        return self._by_module[module]

    def _locate(self, module: str) -> Path | None:
        relative = Path(*module.split("."))
        for root in self._sys_roots:
            candidate = root / relative.with_suffix(".py")
            if candidate.is_file():
                return candidate
            package_init = root / relative / "__init__.py"
            if package_init.is_file():
                return package_init
        return None

    def is_pydantic_model(self, module: str, node: ast.ClassDef) -> bool:
        return self._reaches_model_base(module, node, set())

    def is_exempt(self, module: str, node: ast.ClassDef) -> bool:
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _EXEMPT_BASES:
                return True
            if base_node is not None and self.is_exempt(base_module, base_node):
                return True
        return False

    def _reaches_model_base(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]]
    ) -> bool:
        key = (module, node.name)
        if key in seen:
            return False
        seen.add(key)
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                return True
            if base_node is not None and self._reaches_model_base(
                base_module, base_node, seen
            ):
                return True
        return False

    def resolve_extra(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]] | None = None
    ) -> tuple[str, str | None]:
        """Return ``(status, effective_extra)`` using MRO-like base order."""
        seen = seen if seen is not None else set()
        key = (module, node.name)
        if key in seen:
            return STATUS_UNRESOLVED, None
        seen.add(key)

        own = _extra_from_class(node)
        if own is not None:
            return _STATUS_BY_EXTRA.get(own, STATUS_UNRESOLVED), own

        unresolved_base = False
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                continue
            if base_node is None:
                unresolved_base = True
                continue
            status, extra = self.resolve_extra(base_module, base_node, seen)
            if extra is not None:
                return status, extra
            if status == STATUS_UNRESOLVED:
                unresolved_base = True

        if unresolved_base:
            return STATUS_UNRESOLVED, None
        return STATUS_IMPLICIT_DEFAULT, None

    def _bases(
        self, module: str, node: ast.ClassDef
    ) -> list[tuple[str, str, ast.ClassDef | None]]:
        """Return ``(defining_module, base_name, base_node)`` for each base."""
        out: list[tuple[str, str, ast.ClassDef | None]] = []
        index = self._by_module.get(module)
        for base in node.bases:
            name = _base_name(base)
            if name is None:
                continue
            simple = name.rsplit(".", maxsplit=1)[-1]
            if simple in _PYDANTIC_MODEL_BASES:
                out.append((module, simple, None))
                continue
            if simple in {"Generic", "ABC", "Protocol", "object"}:
                continue

            target_module: str | None = None
            target_name = simple
            if index is not None:
                binding = index.imports.get(simple)
                if binding is not None:
                    target_module, bound_name = binding
                    target_name = bound_name or simple
                elif simple in index.classes:
                    out.append((module, simple, index.classes[simple]))
                    continue

            if target_module is None:
                out.append((module, simple, None))
                continue
            if target_name in _PYDANTIC_MODEL_BASES:
                out.append((target_module, target_name, None))
                continue
            base_index = self._index_for_module(target_module)
            base_node = base_index.classes.get(target_name) if base_index else None
            out.append((target_module, target_name, base_node))
        return out


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _base_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return None


def _extra_from_class(node: ast.ClassDef) -> str | None:
    """Return a class's declared ``extra`` value, or None when absent."""
    for keyword in node.keywords:
        if keyword.arg == "extra":
            return _literal_str(keyword.value) or _UNKNOWN_EXTRA

    for stmt in node.body:
        value_node: ast.expr | None = None
        if (
            isinstance(stmt, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "model_config"
                for target in stmt.targets
            )
        ) or (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == "model_config"
        ):
            value_node = stmt.value
        if value_node is not None:
            extra = _extra_from_config_value(value_node)
            if extra is not None:
                return extra
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
            for inner in stmt.body:
                if isinstance(inner, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "extra"
                    for target in inner.targets
                ):
                    return _literal_str(inner.value) or _UNKNOWN_EXTRA
    return None


def _extra_from_config_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "extra":
                return _literal_str(keyword.value) or _UNKNOWN_EXTRA
        return None
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "extra":
                return _literal_str(value) or _UNKNOWN_EXTRA
    return None


def _literal_str(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None
