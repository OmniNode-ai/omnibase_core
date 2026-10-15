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
    BINDING_ASSIGN,
    BINDING_CLASS,
    BINDING_IMPORT,
    _ModuleIndex,
    module_for_path,
    parse_module,
)

_UNKNOWN_EXTRA = "<unknown>"
_PYDANTIC_MODEL_BASES: frozenset[str] = frozenset(
    {"BaseModel", "BaseSettings", "RootModel"}
)
_EXEMPT_BASES: frozenset[str] = frozenset({"RootModel"})
_STDLIB_BASE_NAMES: frozenset[str] = frozenset({"Generic", "ABC", "Protocol", "object"})
_STDLIB_BASE_ORIGINS: frozenset[tuple[str, str]] = frozenset(
    {
        ("typing", "Generic"),
        ("typing", "Protocol"),
        ("typing_extensions", "Generic"),
        ("typing_extensions", "Protocol"),
        ("abc", "ABC"),
        ("builtins", "object"),
    }
)
_MAX_ALIAS_DEPTH = 16
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
        # A RootModel on one branch cannot exempt an invalid sibling branch.
        if self._has_unresolved_ancestry(module, node, set()):
            return False
        return self._reaches_model_base(module, node, set(), _EXEMPT_BASES)

    def _reaches_model_base(
        self,
        module: str,
        node: ast.ClassDef,
        seen: set[tuple[str, str]],
        targets: frozenset[str] = _PYDANTIC_MODEL_BASES,
    ) -> bool:
        key = (module, node.name)
        if key in seen:
            return False
        seen = seen | {key}
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in targets:
                return True
            if base_node is not None and self._reaches_model_base(
                base_module, base_node, seen, targets
            ):
                return True
        return False

    def _has_unresolved_ancestry(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]]
    ) -> bool:
        """Reject cycles and unknown bases before granting a config or exemption."""
        key = (module, node.name)
        if key in seen:
            return True
        seen = seen | {key}
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                continue
            if base_node is None or self._has_unresolved_ancestry(
                base_module, base_node, seen
            ):
                return True
        return False

    def resolve_extra(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]] | None = None
    ) -> tuple[str, str | None]:
        """Return ``(status, effective_extra)`` using Pydantic's ordered config merge."""
        if seen is None and self._has_unresolved_ancestry(module, node, set()):
            return STATUS_UNRESOLVED, None
        seen = seen if seen is not None else set()
        key = (module, node.name)
        if key in seen:
            return STATUS_UNRESOLVED, None
        seen = seen | {key}

        own = _extra_from_class(node)
        if own is not None:
            return _STATUS_BY_EXTRA.get(own, STATUS_UNRESOLVED), own

        unresolved_base = False
        inherited: tuple[str, str | None] = (STATUS_IMPLICIT_DEFAULT, None)
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                continue
            if base_node is None:
                unresolved_base = True
                continue
            status, extra = self.resolve_extra(base_module, base_node, seen)
            if extra is not None:
                inherited = status, extra
            if status == STATUS_UNRESOLVED:
                unresolved_base = True

        if unresolved_base:
            return STATUS_UNRESOLVED, None
        return inherited

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
            resolved = self._resolve_base(module, index, name, node.lineno, 0)
            if resolved is not None:
                out.append(resolved)
        return out

    def _resolve_base(
        self,
        module: str,
        index: _ModuleIndex | None,
        dotted: str,
        lineno: int,
        depth: int,
    ) -> tuple[str, str, ast.ClassDef | None] | None:
        """Resolve a base name as bound just before *lineno*; None means exempt.

        The stdlib bases (``Protocol``, ``Generic``, ``ABC``, ``object``) are exempt by
        the origin their name is bound to at that point of the module, never by the
        name alone: a model class that happens to be called ``Protocol`` is followed.
        """
        simple = dotted.rsplit(".", maxsplit=1)[-1]
        if simple in _PYDANTIC_MODEL_BASES:
            return (module, simple, None)
        if depth > _MAX_ALIAS_DEPTH:
            return (module, simple, None)

        if "." in dotted:
            return self._resolve_attribute_base(module, index, dotted, lineno)

        binding = index.binding_at(simple, lineno) if index is not None else None
        if binding is None:
            if simple in _STDLIB_BASE_NAMES:
                return None
            if index is not None and simple in index.classes:
                return (module, simple, index.classes[simple])
            return (module, simple, None)

        _, kind, source, imported, target = binding
        if kind == BINDING_CLASS and isinstance(target, ast.ClassDef):
            return (module, simple, target)
        if kind == BINDING_ASSIGN and isinstance(target, ast.expr):
            alias = _base_name(target)
            if alias is None:
                return (module, simple, None)
            return self._resolve_base(module, index, alias, binding[0], depth + 1)
        if kind == BINDING_IMPORT and imported:
            return self._resolve_imported(source, imported)
        return (module, simple, None)

    def _resolve_attribute_base(
        self, module: str, index: _ModuleIndex | None, dotted: str, lineno: int
    ) -> tuple[str, str, ast.ClassDef | None] | None:
        """Resolve ``pkg.Name``: exempt when it names the stdlib base, else followed."""
        simple = dotted.rsplit(".", maxsplit=1)[-1]
        root, *middle = dotted.split(".")[:-1]
        binding = index.binding_at(root, lineno) if index is not None else None
        if binding is None or binding[1] != BINDING_IMPORT or binding[3]:
            return None if simple in _STDLIB_BASE_NAMES else (module, simple, None)
        origin = ".".join([binding[2], *middle])
        if (origin, simple) in _STDLIB_BASE_ORIGINS:
            return None
        if simple not in _STDLIB_BASE_NAMES:
            return (module, simple, None)
        return self._resolve_imported(origin, simple)

    def _resolve_imported(
        self, source: str, imported: str
    ) -> tuple[str, str, ast.ClassDef | None] | None:
        if (source, imported) in _STDLIB_BASE_ORIGINS:
            return None
        if imported in _PYDANTIC_MODEL_BASES:
            return (source, imported, None)
        base_index = self._index_for_module(source)
        base_node = base_index.classes.get(imported) if base_index else None
        return (source, imported, base_node)


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
