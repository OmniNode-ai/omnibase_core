# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail closed on raw process-environment access outside typed bootstrap.

The validator deliberately follows aliases through module and function scopes.
It treats ``os.environ``, ``os.getenv``, aliases of either, and literal or
dynamic ``getattr`` access as raw process-environment access. There are no
allowlists, path exclusions, or inline suppressions.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

from omnibase_core.models.validation.model_env_read_finding import (
    ModelEnvReadFinding,
)
from omnibase_core.validators.environment_reader_inventory import (
    READER_INVENTORY_BY_PATH,
    inventory_key,
    stale_inventory_paths,
    unassigned_reader_paths,
)
from omnibase_core.validators.no_new_os_environ_function_context import (
    _FunctionContext,
)
from omnibase_core.validators.no_new_os_environ_local_names import (
    _LocalNameCollector,
)
from omnibase_core.validators.no_new_os_environ_scope import _BindingKind, _Scope

_BOOTSTRAP_MODULE = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "bootstrap"
    / "model_environment_bootstrap.py"
).resolve()
_DEFAULT_ROOTS: tuple[Path, ...] = (
    Path("src"),
    Path("tests"),
    Path("examples"),
    Path("scripts"),
)
_ENVIRONMENT_ATTRIBUTES: frozenset[str] = frozenset({"environ", "environb"})
_ENVIRONMENT_FUNCTIONS: frozenset[str] = frozenset({"getenv", "putenv", "unsetenv"})


class _RawEnvironmentAccessVisitor(ast.NodeVisitor):
    """Find process-environment access through direct and aliased expressions."""

    def __init__(self, *, allow_bootstrap_capture: bool) -> None:
        self._scope = _Scope(parent=None)
        self._allow_bootstrap_capture = allow_bootstrap_capture
        self._allowed_nodes: set[int] = set()
        self._class_names: list[str] = []
        self._function_contexts: list[_FunctionContext] = []
        self.findings: list[tuple[int, int]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            self._scope.bind(name, "os-module" if alias.name == "os" else None)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != "os":
            for alias in node.names:
                self._scope.bind(alias.asname or alias.name, None)
            return
        for alias in node.names:
            if alias.name == "*":
                self._add(node)
                continue
            self._scope.bind(
                alias.asname or alias.name, self._kind_for_os_attribute(alias.name)
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        kind = self._kind_for(node.value)
        for target in node.targets:
            self.visit(target)
            self._bind_target(target, kind)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
            kind = self._kind_for(node.value)
        else:
            kind = None
        self.visit(node.target)
        self._bind_target(node.target, kind)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)
        self._bind_target(node.target, None)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._bind_target(node.target, self._kind_for(node.value))

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._bind_target(node.target, None)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)
        self._bind_target(node.target, None)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._bind_target(item.optional_vars, None)
        for statement in node.body:
            self.visit(statement)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._bind_target(item.optional_vars, None)
        for statement in node.body:
            self.visit(statement)

    def visit_Global(self, node: ast.Global) -> None:
        self._scope.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._scope.nonlocal_names.update(node.names)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        previous = self._scope
        self._scope = _Scope(parent=previous, local_names=_argument_names(node.args))
        self.visit(node.body)
        self._scope = previous

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self._scope.bind(node.name, None)
        previous = self._scope
        self._scope = _Scope(parent=previous)
        self._class_names.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self._class_names.pop()
        self._scope = previous

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_allowed_capture_call(node):
            self._allowed_nodes.add(id(node.args[0]))
        elif self._getattr_kind(node) is not None or self._is_dynamic_getattr(node):
            self._add(node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if id(node) not in self._allowed_nodes and self._is_raw_attribute(node):
            self._add(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and self._kind_for(node) in {
            "environment-mapping",
            "environment-function",
        }:
            self._add(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        self._scope.bind(node.name, None)
        collector = _LocalNameCollector()
        for statement in node.body:
            collector.visit(statement)
        local_names = _argument_names(node.args) | collector.names
        local_names.difference_update(collector.global_names | collector.nonlocal_names)
        previous = self._scope
        self._scope = _Scope(
            parent=previous,
            local_names=local_names,
            global_names=collector.global_names,
            nonlocal_names=collector.nonlocal_names,
        )
        self._function_contexts.append(
            _FunctionContext(
                name=node.name,
                is_classmethod=any(
                    self._is_classmethod_decorator(decorator)
                    for decorator in node.decorator_list
                ),
            )
        )
        for statement in node.body:
            self.visit(statement)
        self._function_contexts.pop()
        self._scope = previous

    def _bind_target(self, target: ast.expr, kind: _BindingKind | None) -> None:
        if isinstance(target, ast.Name):
            self._scope.bind(target.id, kind)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._bind_target(item, None)

    def _kind_for(self, node: ast.expr) -> _BindingKind | None:
        if isinstance(node, ast.Name):
            return self._scope.resolve(node.id)
        if isinstance(node, ast.Attribute):
            if self._kind_for(node.value) == "os-module":
                return self._kind_for_os_attribute(node.attr)
            return None
        if isinstance(node, ast.Call):
            return self._getattr_kind(node)
        return None

    def _kind_for_os_attribute(self, attribute: str) -> _BindingKind | None:
        if attribute in _ENVIRONMENT_ATTRIBUTES:
            return "environment-mapping"
        if attribute in _ENVIRONMENT_FUNCTIONS:
            return "environment-function"
        return None

    def _getattr_kind(self, node: ast.Call) -> _BindingKind | None:
        if not self._is_getattr_call(node) or len(node.args) != 2:
            return None
        base_kind = self._kind_for(node.args[0])
        attribute = _literal_string(node.args[1])
        if base_kind == "os-module" and attribute is not None:
            return self._kind_for_os_attribute(attribute)
        return None

    def _is_dynamic_getattr(self, node: ast.Call) -> bool:
        if not self._is_getattr_call(node) or len(node.args) != 2:
            return False
        base_kind = self._kind_for(node.args[0])
        return base_kind in {"os-module", "environment-mapping"} and (
            _literal_string(node.args[1]) is None
            or self._getattr_kind(node) is not None
        )

    def _is_raw_attribute(self, node: ast.Attribute) -> bool:
        return (
            self._kind_for(node.value) == "os-module"
            and self._kind_for_os_attribute(node.attr) is not None
        )

    def _is_allowed_capture_call(self, node: ast.Call) -> bool:
        if not self._allow_bootstrap_capture:
            return False
        if self._class_names != ["ModelEnvironmentBootstrap"]:
            return False
        if len(self._function_contexts) != 1:
            return False
        context = self._function_contexts[0]
        if context.name != "capture_process_environment" or not context.is_classmethod:
            return False
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "from_mapping":
            return False
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "cls":
            return False
        if len(node.args) != 1 or len(node.keywords) != 1:
            return False
        if node.keywords[0].arg != "declared_keys":
            return False
        argument = node.args[0]
        return (
            isinstance(argument, ast.Attribute)
            and isinstance(argument.value, ast.Name)
            and argument.value.id == "os"
            and argument.attr == "environ"
        )

    @staticmethod
    def _is_getattr_call(node: ast.Call) -> bool:
        return isinstance(node.func, ast.Name) and node.func.id == "getattr"

    @staticmethod
    def _is_classmethod_decorator(node: ast.expr) -> bool:
        return isinstance(node, ast.Name) and node.id == "classmethod"

    def _add(self, node: ast.AST) -> None:
        location_node = cast(ast.expr, node)
        finding = (location_node.lineno, location_node.col_offset)
        if finding not in self.findings:
            self.findings.append(finding)


def _argument_names(arguments: ast.arguments) -> set[str]:
    """Return every name that shadows module aliases in a function scope."""
    names = {argument.arg for argument in arguments.posonlyargs}
    names.update(argument.arg for argument in arguments.args)
    names.update(argument.arg for argument in arguments.kwonlyargs)
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return names


def _literal_string(node: ast.expr) -> str | None:
    """Return a literal getattr attribute name without evaluating source code."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _character_column(source_line: str, byte_offset: int) -> int:
    """Convert Python AST's UTF-8 byte offset to a character column."""
    return len(source_line.encode("utf-8")[:byte_offset].decode("utf-8"))


def validate_file(path: Path) -> list[ModelEnvReadFinding]:
    """Return raw environment findings, allowing only the exact capture expression."""
    if path.suffix != ".py":
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [
            ModelEnvReadFinding(
                path=path,
                line=0,
                col=0,
                var_name="<unreadable>",
                raw_line=str(error),
            )
        ]
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return [
            ModelEnvReadFinding(
                path=path,
                line=error.lineno or 0,
                col=error.offset or 0,
                var_name="<syntax-error>",
                raw_line=error.msg,
            )
        ]
    lines = source.splitlines()
    visitor = _RawEnvironmentAccessVisitor(
        allow_bootstrap_capture=path.resolve() == _BOOTSTRAP_MODULE,
    )
    visitor.visit(tree)
    return [
        ModelEnvReadFinding(
            path=path,
            line=line,
            col=_character_column(lines[line - 1], col),
            var_name="<direct-process-environment>",
            raw_line=lines[line - 1],
        )
        for line, col in visitor.findings
    ]


def validate_paths(paths: Sequence[Path]) -> list[ModelEnvReadFinding]:
    """Validate all supplied Python paths without tests/tooling/example exclusions."""
    findings: list[ModelEnvReadFinding] = []
    for path in _iter_python_files(paths):
        findings.extend(validate_file(path))
    return findings


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    for path in paths:
        if path.suffix == ".py" and not path.is_dir():
            yield path
        elif path.is_dir():
            yield from sorted(
                child
                for child in path.rglob("*.py")
                if "__pycache__" not in child.parts
            )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Permit raw process-environment access only in typed bootstrap."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    paths = _DEFAULT_ROOTS if args.all else args.paths
    if not paths:
        return 0
    findings = validate_paths(paths)
    if args.inventory:
        _write_inventory_report(findings)
    if not findings:
        return 0
    sys.stderr.write(
        "raw process-environment access is permitted only in the typed bootstrap "
        "capture operation\n"
    )
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n    {finding.raw_line.strip()}\n")
    return 1


def _write_inventory_report(findings: Sequence[ModelEnvReadFinding]) -> None:
    """Render the checked reader-to-owner/disposition mapping for review."""
    finding_paths = {finding.path for finding in findings}
    unassigned = unassigned_reader_paths(finding_paths)
    stale = stale_inventory_paths(finding_paths)
    sys.stdout.write(
        "environment-reader-inventory: "
        f"findings={len(findings)} paths={len(finding_paths)} "
        f"unassigned={len(unassigned)} stale={len(stale)}\n"
    )
    for path in sorted(finding_paths, key=inventory_key):
        key = inventory_key(path)
        assignment = READER_INVENTORY_BY_PATH.get(key)
        if assignment is None:
            sys.stdout.write(f"  {key}: UNASSIGNED\n")
            continue
        sys.stdout.write(
            f"  {key}: owner={assignment.owner} disposition={assignment.disposition}\n"
        )
    for stale_path in stale:
        sys.stdout.write(f"  {stale_path}: STALE-INVENTORY\n")


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: validator CLI process exit
