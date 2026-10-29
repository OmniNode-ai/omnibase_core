# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolve contract bindings; delegate every shape decision to the generic checker."""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.flip_bundle.model_flip_binding_document import (
    ModelFlipBindingDocument,
)
from omnibase_core.models.flip_bundle.model_handler_shape_finding import (
    ModelHandlerShapeFinding,
)
from omnibase_core.validation.checker_handler_shape import check_handler_shape
from omnibase_core.validation.validator_flip_scope import SCOPE
from omnibase_core.validation.validator_handler_shape import (
    ValidatorHandlerShape,
    module_facts,
)


def _module_to_files(module: str) -> list[Path]:
    """Candidate source files for a dotted handler module (module or package)."""
    rel = module.replace(".", "/")
    files: list[Path] = []
    exact = SCOPE.src_root / f"{rel}.py"
    if exact.exists():
        files.append(exact)
    pdir = SCOPE.src_root / rel
    if pdir.is_dir():
        files.extend(sorted(pdir.glob("*.py")))
        files.extend(sorted(pdir.glob("handlers/*.py")))
    # de-dupe, push __init__ last so a real handler module wins
    uniq: list[Path] = []
    for f in files:
        if f not in uniq:
            uniq.append(f)
    uniq.sort(key=lambda f: (f.name == "__init__.py", str(f)))
    return uniq


def _node_package(contract_path: Path) -> str:
    """Dotted package for the node dir holding ``contract.yaml``."""
    rel = contract_path.parent.relative_to(SCOPE.src_root)
    return ".".join(rel.parts)


def _contract_bindings(data: dict[str, object]) -> list[tuple[str, str | None]]:
    """Return declared (module, class_or_None) handler bindings, primary first."""
    out: list[tuple[str, str | None]] = []
    handler = data.get("handler")
    if isinstance(handler, dict) and handler.get("module"):
        out.append((str(handler["module"]), handler.get("class")))
    routing = data.get("handler_routing")
    if isinstance(routing, dict):
        default = routing.get("default_handler")
        if isinstance(default, str) and default:
            # form "handler:ClassName" | "module.path:ClassName" | "ClassName"
            left, _, right = default.partition(":")
            cls = right or left
            module = left if ("." in left and right) else None
            out.append((module or "", cls or None))
        for entry in routing.get("handlers", []) or []:
            if isinstance(entry, dict):
                h = entry.get("handler")
                if isinstance(h, dict) and h.get("module"):
                    out.append((str(h["module"]), h.get("class")))
    seen: set[tuple[str, str | None]] = set()
    ded: list[tuple[str, str | None]] = []
    for m, c in out:
        if (m, c) not in seen:
            seen.add((m, c))
            ded.append((m, c))
    return ded


def _classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [n for n in tree.body if isinstance(n, ast.ClassDef)]


def _handle_method(cls: ast.ClassDef) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for m in cls.body:
        if (
            isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
            and m.name == "handle"
        ):
            return m
    return None


def _base_class_names(cls: ast.ClassDef) -> list[str]:
    """Extract simple and qualified base names in declaration order."""
    return [
        base.id if isinstance(base, ast.Name) else base.attr
        for base in cls.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    ]


def _resolve_class_by_name(
    name: str,
    parsed: list[tuple[Path, ast.Module]],
    seen_files: set[Path],
) -> tuple[ast.ClassDef | None, Path | None, list[tuple[Path, ast.Module]]]:
    """Find a local or imported base, retaining newly parsed source files."""
    for path, tree in parsed:
        for cls in _classes(tree):
            if cls.name == name:
                return cls, path, parsed
    for path, tree in list(parsed):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            module = node.module
            if node.level:
                try:
                    parts = path.parent.relative_to(SCOPE.src_root).parts
                except ValueError:
                    continue
                if node.level > len(parts):
                    continue
                module = ".".join((*parts[: len(parts) - node.level + 1], module))
            for alias in node.names:
                if (alias.asname or alias.name) != name:
                    continue
                for target in _module_to_files(module):
                    if target not in seen_files:
                        seen_files.add(target)
                        try:
                            imported = ast.parse(target.read_text(encoding="utf-8"))
                        except (OSError, SyntaxError):
                            continue
                        parsed.append((target, imported))
                    for cached_path, imported in parsed:
                        if cached_path != target:
                            continue
                        for cls in _classes(imported):
                            if cls.name == alias.name:
                                return cls, target, parsed
    return None, None, parsed


def _handle_via_mro(
    cls: ast.ClassDef,
    parsed: list[tuple[Path, ast.Module]],
    *,
    max_depth: int = 8,
    sources: set[Path] | None = None,
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Search ancestors breadth-first, bounded by depth and visited class names."""
    parsed = list(parsed)
    seen_files = {path for path, _tree in parsed}
    visited = {cls.name}
    pending = deque((name, 1) for name in _base_class_names(cls))
    while pending:
        name, depth = pending.popleft()
        if depth > max_depth or name in visited:
            continue
        visited.add(name)
        base, path, parsed = _resolve_class_by_name(name, parsed, seen_files)
        if sources is not None:
            sources.update(path for path, _tree in parsed)
        if base is None:
            continue
        fn = _handle_method(base)
        if fn is not None:
            return fn, base, path
        pending.extend((name, depth + 1) for name in _base_class_names(base))
    return None, None, None


def _operation_methods(cls: ast.ClassDef) -> list[str]:
    out: list[str] = []
    for m in cls.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if m.name.startswith("_") or m.name in (
                "handle",
                "initialize",
                "is_initialized",
            ):
                continue
            pos = [a for a in m.args.args if a.arg != "self"]
            if pos or m.args.kwarg:
                out.append(m.name)
    return out


def _follow_reexport(
    parsed: list[tuple[Path, ast.Module]],
    cls_name: str,
    *,
    sources: set[Path] | None = None,
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Resolve a class re-exported via ``from <mod> import <Real> as <cls_name>``.

    Core nodes commonly re-export the concrete handler under the contract's class
    name (e.g. ``handler.py`` re-exports ``HandlerBackendSecretDisciplineCompute``
    as ``NodeBackendSecretDisciplineCompute``). Follow that import to the defining
    module so the shape is classified on the real class, not marked phantom.
    """
    # Resolve a module-level assignment alias first
    # (``NodeX = HandlerX``), so the import-follow targets the real class name.
    effective = cls_name
    for _f, tree in parsed:
        for stmt in tree.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == cls_name
                and isinstance(stmt.value, ast.Name)
            ):
                effective = stmt.value.id
    for _f, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            for alias in node.names:
                if (alias.asname or alias.name) == effective:
                    for target in _module_to_files(node.module):
                        if sources is not None:
                            sources.add(target)
                        try:
                            t2 = ast.parse(target.read_text(encoding="utf-8"))
                        except (OSError, SyntaxError):
                            continue
                        for c in _classes(t2):
                            if c.name == alias.name:
                                fn = _handle_method(c)
                                if fn is None:
                                    inherited = _handle_via_mro(
                                        c, [(target, t2), *parsed], sources=sources
                                    )
                                    if inherited[0] is not None:
                                        return inherited
                                return fn, c, target
    return None, None, None


def _resolve_handler(
    files: list[Path], cls_name: str | None, *, sources: set[Path] | None = None
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Find (handle_fn, class, file) for a binding, preferring the named class."""
    parsed: list[tuple[Path, ast.Module]] = []
    for f in files:
        try:
            parsed.append((f, ast.parse(f.read_text(encoding="utf-8"))))
        except (OSError, SyntaxError):
            continue
    # named class with a handle
    if cls_name:
        for f, tree in parsed:
            for c in _classes(tree):
                if c.name == cls_name:
                    fn = _handle_method(c)
                    if fn is None:
                        inherited = _handle_via_mro(c, parsed, sources=sources)
                        if inherited[0] is not None:
                            return inherited
                    if fn or _operation_methods(c):
                        return fn, c, f
    # any class with a handle
    for f, tree in parsed:
        for c in _classes(tree):
            fn = _handle_method(c)
            if fn is not None:
                return fn, c, f
            inherited = _handle_via_mro(c, parsed, sources=sources)
            if inherited[0] is not None:
                return inherited
    # named class re-exported from another module (follow the import)
    if cls_name:
        rfn, rc, rf = _follow_reexport(parsed, cls_name, sources=sources)
        if rc is not None:
            return rfn, rc, rf
        # named class defined locally but without a handle (report op/empty)
        for f, tree in parsed:
            for c in _classes(tree):
                if c.name == cls_name:
                    return None, c, f
    # any Handler*/Node* class
    for f, tree in parsed:
        for c in _classes(tree):
            if c.name.startswith(("Handler", "Node")):
                inherited = _handle_via_mro(c, parsed, sources=sources)
                if inherited[0] is not None:
                    return inherited
                return None, c, f
    return None, None, None


def _binding_issues(
    files: list[Path], resolved: Path | None
) -> tuple[ModelValidationIssue, ...]:
    """Judge defining and declaring modules, including inherited handler state."""
    rules = ValidatorHandlerShape().contract.rules
    issues: list[ModelValidationIssue] = []
    for path in dict.fromkeys(([resolved] if resolved is not None else []) + files):
        try:
            facts = module_facts(path.as_posix(), path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            # The resolver treats unreadable candidate files as absent as well.
            continue
        issues.extend(check_handler_shape(facts, rules))
    return tuple(issues)


def _binding_finding(
    module: str, cls: str | None, node_pkg: str, *, bound: bool = True
) -> ModelHandlerShapeFinding:
    """Resolve the binding structurally and apply the contract's current rules."""
    module = module or node_pkg
    files = _module_to_files(module)
    sources = set(files)
    fn, cdef, path = _resolve_handler(files, cls, sources=sources)
    issues = _binding_issues(sorted(sources), path)
    if issues:
        return ModelHandlerShapeFinding(
            node_id=node_pkg,
            category=issues[0].code or "shape",
            is_canonical=False,
            handler_module=module,
            detail="; ".join(f"{i.code}: {i.message}" for i in issues),
        )
    if cdef is None:
        return ModelHandlerShapeFinding(
            node_id=node_pkg,
            category="phantom" if bound else "no_binding",
            is_canonical=False,
            handler_module=module,
            detail=f"class {cls or '<any>'} not found"
            if bound
            else "contract declares no handler",
        )
    if fn is None:
        methods = _operation_methods(cdef)
        return ModelHandlerShapeFinding(
            node_id=node_pkg,
            category="op_method" if methods else "empty",
            is_canonical=False,
            handler_module=module,
            detail=f"no handle(); op-methods={methods[:4]}"
            if methods
            else "no handle() and no methods",
        )
    return ModelHandlerShapeFinding(
        node_id=node_pkg,
        category="canonical",
        is_canonical=True,
        handler_module=module,
        detail="resolved handle; handler-shape rules passed",
    )


def classify_binding(module: str, cls: str | None, node_pkg: str) -> tuple[bool, str]:
    """The seam gate's verdict for one explicit contract binding."""
    finding = _binding_finding(module, cls, node_pkg)
    return (
        finding.is_canonical,
        f"{module or node_pkg}:{cls or '<any>'} [{finding.category}] {finding.detail}",
    )


def classify_node(contract_path: Path) -> ModelHandlerShapeFinding:
    """Classify a node using binding resolution and the generic shape rules."""
    node_id = _node_package(contract_path)
    try:
        data = load_binding_document(contract_path.read_text(encoding="utf-8"))
    except (OSError, ModelOnexError) as exc:
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="phantom",
            is_canonical=False,
            detail=f"unparseable contract: {exc}",
        )
    if not isinstance(data, dict):
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="phantom",
            is_canonical=False,
            detail="contract is not a mapping",
        )
    bindings = _contract_bindings(data)
    module, cls = bindings[0] if bindings else (node_id, None)
    return _binding_finding(module, cls, node_id, bound=bool(bindings))


def load_binding_document(source: str) -> dict[str, object] | None:
    """Parse a contract through the shared typed loader for structural inspection."""
    return ModelFlipBindingDocument.from_yaml(source).mapping
