# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Imperative contract guard of one repository (OMN-20918).

Ported from onex_change_control ``scripts.check_imperative_contracts`` at 725d2967 for
OCC retirement step S8. For one repository the guard

- audits every handler of every ``node_*`` directory against its node's contract (the
  decisions of :class:`HandlerArchHandlerContractCompliance`), and
- when ``scan_freestanding`` is set, audits every ``src/`` module outside node
  handlers for imperative IO (:class:`HandlerFreestandingImperativeIo`),

then classifies each freestanding module LIVE, DEAD or TEST_HARNESS from the import
graph rooted at the repository's entrypoints: handler modules declared in a
``contract.yaml``, the ``node.py`` beside it, and every ``pyproject.toml`` script and
entry-point target. A violation that is not allowlisted blocks only when LIVE.

The handler is pure over the supplied sources (:class:`ModelImperativeContractGuardInput`);
the tree read, the allowlist and the report rendering live in
``handler_imperative_contract_guard_cli``.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import PurePosixPath
from typing import Final

import yaml

from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.handlers.handler_arch_handler_contract_compliance import (
    HandlerArchHandlerContractCompliance,
    _load_yaml_text,
)
from omnibase_core.handlers.handler_freestanding_imperative_io import (
    HandlerFreestandingImperativeIo,
)
from omnibase_core.models.governance.model_freestanding_imperative_result import (
    ModelFreestandingImperativeResult,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_input import (
    ModelHandlerContractComplianceInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_freestanding_scan_input import (
    ModelFreestandingScanInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_module_source import (
    ModelGuardModuleSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_contract_guard_input import (
    ModelImperativeContractGuardInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_contract_guard_report import (
    ModelImperativeContractGuardReport,
)

# Directory names that are never freestanding source (vendored, cached, tests).
_FREESTANDING_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".repowise",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "tests",
        "test",
    }
)

_SRC: Final = PurePosixPath("src")


def _is_node_governed_module(python_file: PurePosixPath) -> bool:
    """Return True if the node-contract scanner already governs the file.

    That scanner audits handler modules under ``node_*/handlers/`` and the
    declarative ``node.py`` directly under a ``node_*`` directory. Both are excluded
    from the freestanding scan to avoid double-counting.
    """
    parts = python_file.parts
    for index, part in enumerate(parts[:-1]):
        if part == "handlers" and index >= 1 and parts[index - 1].startswith("node_"):
            return True
    if python_file.name != "node.py":
        return False
    return python_file.parent.name.startswith("node_")


def _find_freestanding_modules(
    modules: list[ModelGuardModuleSource],
) -> list[ModelGuardModuleSource]:
    """Select the ``src/**/*.py`` modules the node scanner is structurally blind to."""
    selected: list[ModelGuardModuleSource] = []
    for module in modules:
        path = PurePosixPath(module.path)
        if path.name == "__init__.py":
            continue
        if any(part in _FREESTANDING_SKIP_DIRS for part in path.parts):
            continue
        if _is_node_governed_module(path):
            continue
        selected.append(module)
    return sorted(selected, key=lambda module: PurePosixPath(module.path))


def _module_name_for_file(path: PurePosixPath) -> str | None:
    """Return the importable module name for a Python file under ``src``."""
    try:
        rel = path.relative_to(_SRC)
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _is_test_harness_path(path: PurePosixPath) -> bool:
    return "tests" in set(path.parts) or path.name.startswith("test_")


def _resolve_from_import_base(
    *,
    current_package: str,
    module: str | None,
    level: int,
) -> str | None:
    """Resolve an ``ast.ImportFrom`` base module."""
    if level == 0:
        return module
    package_parts = current_package.split(".") if current_package else []
    if level > len(package_parts) + 1:
        return module
    base_parts = package_parts[: len(package_parts) - level + 1]
    if module:
        base_parts.extend(module.split("."))
    return ".".join(part for part in base_parts if part)


def _extract_imports(
    tree: ast.AST,
    *,
    current_module: str,
    is_package: bool = False,
) -> set[str]:
    """Extract absolute import targets from a module AST."""
    imports: set[str] = set()
    current_package = (
        current_module
        if is_package
        else current_module.rsplit(".", 1)[0]
        if "." in current_module
        else ""
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_import_base(
                current_package=current_package,
                module=node.module,
                level=node.level,
            )
            if not base:
                continue
            imports.add(base)
            imports.update(f"{base}.{alias.name}" for alias in node.names)
    return imports


def _resolve_import_target(
    imported: str,
    module_by_name: dict[str, ModelGuardModuleSource],
) -> set[str]:
    """Map an import string onto known repo modules."""
    if imported in module_by_name:
        return {imported}
    parts = imported.split(".")
    for end in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in module_by_name:
            return {candidate}
    return set()


def _build_import_graph(
    module_by_name: dict[str, ModelGuardModuleSource],
) -> dict[str, set[str]]:
    """Build an intra-repo import graph keyed by importable module name."""
    graph: dict[str, set[str]] = {name: set() for name in module_by_name}
    for module_name, module in module_by_name.items():
        try:
            tree = ast.parse(module.source)
        except SyntaxError:
            continue
        imports = _extract_imports(
            tree,
            current_module=module_name,
            is_package=PurePosixPath(module.path).name == "__init__.py",
        )
        graph[module_name].update(
            target
            for imported in imports
            for target in _resolve_import_target(imported, module_by_name)
        )
    return graph


def _contract_entrypoint_modules(contract_text: str) -> set[str]:
    """Extract handler modules declared by a node contract."""
    try:
        data = _load_yaml_text(contract_text) or {}
    except yaml.YAMLError:
        return set()
    modules: set[str] = set()
    routing = data.get("handler_routing")
    if isinstance(routing, dict):
        handlers = routing.get("handlers")
        if isinstance(handlers, list):
            for entry in handlers:
                if not isinstance(entry, dict):
                    continue
                handler = entry.get("handler")
                if isinstance(handler, dict) and isinstance(handler.get("module"), str):
                    modules.add(handler["module"])
    return modules


def _entrypoint_spec_module(spec: object) -> str:
    if not isinstance(spec, str):
        return ""
    return spec.split(":", 1)[0].strip()


def _pyproject_entrypoint_modules(pyproject_text: str | None) -> set[str]:
    """Extract module roots from pyproject scripts and entry-points."""
    if pyproject_text is None:
        return set()
    try:
        data = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError:
        return set()
    project = data.get("project")
    if not isinstance(project, dict):
        return set()
    modules: set[str] = set()
    scripts = project.get("scripts")
    if isinstance(scripts, dict):
        modules.update(_entrypoint_spec_module(spec) for spec in scripts.values())
    entry_points = project.get("entry-points")
    if isinstance(entry_points, dict):
        for group in entry_points.values():
            if isinstance(group, dict):
                modules.update(_entrypoint_spec_module(spec) for spec in group.values())
    return {module for module in modules if module}


def _collect_entrypoint_modules(request: ModelImperativeContractGuardInput) -> set[str]:
    """Collect contract and project-script entrypoints for live reachability."""
    entrypoints: set[str] = set()
    for contract in request.contracts:
        entrypoints.update(_contract_entrypoint_modules(contract.text))
        node_module = _module_name_for_file(
            PurePosixPath(contract.path).parent / "node.py"
        )
        if contract.has_node_py and node_module is not None:
            entrypoints.add(node_module)
    entrypoints.update(_pyproject_entrypoint_modules(request.pyproject_text))
    return entrypoints


def _reachable_modules(
    entrypoints: set[str],
    graph: dict[str, set[str]],
    module_by_name: dict[str, ModelGuardModuleSource],
) -> set[str]:
    """Return modules reachable from known entrypoints."""
    roots = {
        target
        for entrypoint in entrypoints
        for target in _resolve_import_target(entrypoint, module_by_name)
    }
    reachable: set[str] = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        stack.extend(sorted(graph.get(current, set()) - reachable))
    return reachable


def _classify_module_reachability(
    request: ModelImperativeContractGuardInput,
    modules: list[ModelGuardModuleSource],
) -> dict[str, EnumReachability]:
    """Classify freestanding modules (by path) from repo entrypoint import reachability."""
    all_modules_by_name: dict[str, ModelGuardModuleSource] = {}
    for module in request.modules:
        if "__pycache__" in PurePosixPath(module.path).parts:
            continue
        name = _module_name_for_file(PurePosixPath(module.path))
        if name is not None:
            all_modules_by_name[name] = module
    graph = _build_import_graph(all_modules_by_name)
    reachable_names = _reachable_modules(
        _collect_entrypoint_modules(request), graph, all_modules_by_name
    )
    classified: dict[str, EnumReachability] = {}
    for module in modules:
        path = PurePosixPath(module.path)
        name = _module_name_for_file(path)
        if name is None:
            continue
        if _is_test_harness_path(path):
            classified[module.path] = EnumReachability.TEST_HARNESS
        elif name in reachable_names:
            classified[module.path] = EnumReachability.LIVE
        else:
            classified[module.path] = EnumReachability.DEAD
    return classified


def _scan_freestanding(
    request: ModelImperativeContractGuardInput,
) -> tuple[int, list[ModelFreestandingImperativeResult]]:
    """Audit every freestanding module and return (count, results)."""
    modules = _find_freestanding_modules(request.modules)
    reachability = _classify_module_reachability(request, modules)
    allowlisted = frozenset(request.allowlisted_paths)
    scanner = HandlerFreestandingImperativeIo()
    return len(modules), [
        scanner.handle(
            ModelFreestandingScanInput(
                module=module,
                repo=request.repo,
                allowlisted=module.path in allowlisted,
                reachability=reachability.get(module.path, EnumReachability.DEAD),
            )
        )
        for module in modules
    ]


class HandlerImperativeContractGuard:
    """Decide which imperative contract violations a repository carries."""

    def handle(
        self, request: ModelImperativeContractGuardInput
    ) -> ModelImperativeContractGuardReport:
        """Return node results and, when asked, freestanding results."""
        node_report = HandlerArchHandlerContractCompliance().handle(
            ModelHandlerContractComplianceInput(
                repo=request.repo,
                nodes=request.nodes,
                allowlisted_paths=request.allowlisted_paths,
            )
        )
        module_count = 0
        freestanding: list[ModelFreestandingImperativeResult] = []
        if request.scan_freestanding:
            module_count, freestanding = _scan_freestanding(request)
        return ModelImperativeContractGuardReport(
            node_count=len(request.nodes),
            results=node_report.results,
            freestanding_scanned=request.scan_freestanding,
            freestanding_module_count=module_count,
            freestanding_results=freestanding,
        )
