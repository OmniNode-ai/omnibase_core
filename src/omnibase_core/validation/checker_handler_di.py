# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for K1 ``handler_di`` (OMN-21531, replacing the old handler DI gate).

A handler or node acquires every dependency from the container it is given. Facts in
(one module's posix path and source), ``ModelValidationIssue`` out: no file read, no
clock, no environment. Every class-name pattern, callee pattern, name list and
remediation text is a ``parameters`` entry (or the ``description``) of the matching rule
row in ``contracts/handler_di.validation.yaml``.

Rules: constructor_signature, direct_construction, call_site_construction,
fallback_construction, reflective_construction, optional_port_default,
contract_self_load, module_singleton, sibling_handler_import, contract_value_literal.

A rule whose row is absent or disabled is not run; an enabled row with a missing or
mistyped parameter raises, so a broken contract fails to load instead of passing every file.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_handler_di_module_fact import (
    ModelHandlerDiModuleFact,
)
from omnibase_core.validation.checker_baseline_moves import carry_baseline
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_CONSTRUCTOR = "constructor_signature"
RULE_DIRECT = "direct_construction"
RULE_CALL_SITE = "call_site_construction"
RULE_FALLBACK = "fallback_construction"
RULE_REFLECTIVE = "reflective_construction"
RULE_NONE_DEFAULT = "optional_port_default"
RULE_CONTRACT_LOAD = "contract_self_load"
RULE_SINGLETON = "module_singleton"
RULE_SIBLING = "sibling_handler_import"
RULE_VALUE_LITERAL = "contract_value_literal"
RULE_BASELINE = "baseline_ratchet"

FORM_OR = "boolean_or"
FORM_TERNARY = "conditional_expression"
FORM_GUARD = "none_guard"


def _issue(
    row: ModelValidatorRule, path: Path, line: int, subject: str
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=row.severity,
        message=f"{subject}: {row.description}",
        code=row.rule_id,
        file_path=path,
        line_number=line,
        rule_name=row.rule_id,
    )


def _pattern(row: ModelValidatorRule, key: str) -> re.Pattern[str]:
    try:
        return re.compile(rule_string(row, key))
    except re.error as exc:
        raise ModelOnexError(
            message=f"rule {row.rule_id!r} holds an invalid regular expression under parameters.{key}: {exc}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        ) from exc


def _patterns(row: ModelValidatorRule, key: str) -> tuple[re.Pattern[str], ...]:
    try:
        return tuple(re.compile(p) for p in rule_strings(row, key))
    except re.error as exc:
        raise ModelOnexError(
            message=f"rule {row.rule_id!r} holds an invalid regular expression under parameters.{key}: {exc}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        ) from exc


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _dotted(func: ast.expr) -> str:
    return ast.unparse(func)


def _classes(tree: ast.Module, name_pattern: re.Pattern[str]) -> Iterator[ast.ClassDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and name_pattern.search(node.name):
            yield node


def _methods(
    cls: ast.ClassDef,
) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for item in cls.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            yield item


def _optional_parameters(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.arg]:
    """Parameters of ``func`` whose default is the literal ``None``."""
    positional = [*func.args.posonlyargs, *func.args.args]
    defaults: list[ast.expr | None] = [
        *([None] * (len(positional) - len(func.args.defaults))),
        *func.args.defaults,
    ]
    pairs = [*zip(positional, defaults, strict=True)]
    pairs.extend(zip(func.args.kwonlyargs, func.args.kw_defaults, strict=True))
    return [
        arg
        for arg, default in pairs
        if isinstance(default, ast.Constant) and default.value is None
    ]


# --- constructor_signature -----------------------------------------------------


def _check_constructor_signature(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    classes = _pattern(row, "class_name_pattern")
    init_name = rule_string(row, "init_name")
    self_name = rule_string(row, "self_parameter")
    container = rule_string(row, "container_parameter")
    issues: list[ModelValidationIssue] = []
    for cls in _classes(tree, classes):
        for item in cls.body:
            if not (isinstance(item, ast.FunctionDef) and item.name == init_name):
                continue
            params = [a.arg for a in item.args.args]
            if params and params[0] == self_name:
                params = params[1:]
            if not params or params == [container]:
                continue
            issues.append(
                _issue(
                    row,
                    path,
                    item.lineno,
                    f"class {cls.name!r} {init_name} params ({', '.join(params)})",
                )
            )
    return issues


# --- direct_construction -------------------------------------------------------


def _check_direct_construction(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    classes = _pattern(row, "class_name_pattern")
    init_name = rule_string(row, "init_name")
    receiver = rule_string(row, "receiver_name")
    resolution = rule_strings(row, "resolution_attrs")
    issues: list[ModelValidationIssue] = []
    for cls in _classes(tree, classes):
        for item in cls.body:
            if not (isinstance(item, ast.FunctionDef) and item.name == init_name):
                continue
            for stmt in ast.walk(item):
                if not (
                    isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call)
                ):
                    continue
                on_receiver = any(
                    isinstance(t, ast.Attribute)
                    and isinstance(t.value, ast.Name)
                    and t.value.id == receiver
                    for t in stmt.targets
                )
                func = stmt.value.func
                resolved = isinstance(func, ast.Attribute) and func.attr in resolution
                if on_receiver and not resolved:
                    issues.append(
                        _issue(
                            row,
                            path,
                            stmt.lineno,
                            f"class {cls.name!r} directly constructs {_dotted(func)!r} in {init_name}",
                        )
                    )
    return issues


# --- call_site_construction ----------------------------------------------------


def _check_call_site_construction(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    constructed = _pattern(row, "constructed_name_pattern")
    invoked = rule_strings(row, "invoked_methods")
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in invoked
            and isinstance(node.func.value, ast.Call)
        ):
            continue
        name = _callee_name(node.func.value.func)
        if name is not None and constructed.search(name):
            issues.append(
                _issue(
                    row,
                    path,
                    node.lineno,
                    f"{name}(...).{node.func.attr}(...) builds the handler at the call site",
                )
            )
    return issues


# --- fallback_construction -----------------------------------------------------


def _loader_call(nodes: list[ast.expr], loader: re.Pattern[str]) -> ast.Call | None:
    for root in nodes:
        for node in ast.walk(root):
            if isinstance(node, ast.Call):
                name = _callee_name(node.func)
                if name is not None and loader.search(name):
                    return node
    return None


def _names_in(node: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _fallback_call(
    node: ast.AST, optional: set[str], loader: re.Pattern[str], forms: tuple[str, ...]
) -> ast.Call | None:
    """The loader or constructor call that ``node`` substitutes for an omitted parameter."""
    if (
        FORM_OR in forms
        and isinstance(node, ast.BoolOp)
        and isinstance(node.op, ast.Or)
        and isinstance(node.values[0], ast.Name)
        and node.values[0].id in optional
    ):
        return _loader_call(list(node.values[1:]), loader)
    if (
        FORM_TERNARY in forms
        and isinstance(node, ast.IfExp)
        and _names_in(node.test) & optional
    ):
        return _loader_call([node.body, node.orelse], loader)
    if (
        FORM_GUARD in forms
        and isinstance(node, ast.If)
        and _names_in(node.test) & optional
    ):
        return _loader_call(
            [
                s.value
                for s in node.body
                if isinstance(s, ast.Assign | ast.Return) and s.value is not None
            ],
            loader,
        )
    return None


def _check_fallback_construction(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    classes = _pattern(row, "class_name_pattern")
    loader = _pattern(row, "loader_name_pattern")
    forms = rule_strings(row, "fallback_forms")
    issues: list[ModelValidationIssue] = []
    seen: set[int] = set()
    for cls in _classes(tree, classes):
        for func in _methods(cls):
            optional = {a.arg for a in _optional_parameters(func)}
            if not optional:
                continue
            for node in ast.walk(func):
                call = _fallback_call(node, optional, loader, forms)
                if call is not None and id(call) not in seen:
                    seen.add(id(call))
                    issues.append(
                        _issue(
                            row,
                            path,
                            call.lineno,
                            f"{_dotted(call.func)}() builds the dependency a caller left as None",
                        )
                    )
    return issues


# --- reflective_construction ---------------------------------------------------


def _check_reflective_construction(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    getters = rule_strings(row, "reflective_getters")
    tables = rule_strings(row, "lookup_tables")
    class_variable = _pattern(row, "class_variable_pattern")
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        subject: str | None = None
        if isinstance(func, ast.Call) and _callee_name(func.func) in getters:
            subject = (
                f"{_dotted(func.func)}(...)() constructs a class chosen at run time"
            )
        elif (
            isinstance(func, ast.Subscript)
            and isinstance(func.value, ast.Call)
            and _callee_name(func.value.func) in tables
        ):
            subject = f"{_dotted(func.value.func)}()[...]() constructs a class chosen at run time"
        elif isinstance(func, ast.Name) and class_variable.search(func.id):
            subject = f"{func.id}() constructs a class held in a variable"
        if subject is not None:
            issues.append(_issue(row, path, node.lineno, subject))
    return issues


# --- optional_port_default -----------------------------------------------------


def _check_optional_port_default(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    classes = _pattern(row, "class_name_pattern")
    port_name = _pattern(row, "port_name_pattern")
    port_annotation = _pattern(row, "port_annotation_pattern")
    issues: list[ModelValidationIssue] = []
    for cls in _classes(tree, classes):
        for method in _methods(cls):
            for arg in _optional_parameters(method):
                annotation = ast.unparse(arg.annotation) if arg.annotation else ""
                if port_name.search(arg.arg) or port_annotation.search(annotation):
                    issues.append(
                        _issue(
                            row,
                            path,
                            arg.lineno,
                            f"{cls.name}.{method.name} defaults port {arg.arg!r} to None",
                        )
                    )
    return issues


# --- contract_self_load --------------------------------------------------------


def _check_contract_self_load(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    self_references = rule_strings(row, "self_reference_names")
    contract_file = _pattern(row, "contract_file_pattern")
    statements = rule_strings(row, "statement_kinds")
    issues: list[ModelValidationIssue] = []
    for stmt in ast.walk(tree):
        if type(stmt).__name__ not in statements or not isinstance(stmt, ast.stmt):
            continue
        names = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)}
        literals = [
            n.value
            for n in ast.walk(stmt)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        if names & set(self_references) and any(
            contract_file.search(v) for v in literals
        ):
            issues.append(
                _issue(
                    row, path, stmt.lineno, "the module locates its own contract file"
                )
            )
    loaders = frozenset(rule_strings(row, "loader_call_names"))
    for cls in _classes(tree, _pattern(row, "loader_class_pattern")):
        for method in _methods(cls):
            issues.extend(
                _issue(
                    row,
                    path,
                    call.lineno,
                    f"{method.name} loads its own contract with {_callee_name(call.func)}()",
                )
                for call in ast.walk(method)
                if isinstance(call, ast.Call) and _callee_name(call.func) in loaders
            )
    return issues


# --- module_singleton ----------------------------------------------------------


def _check_module_singleton(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    kinds = rule_strings(row, "statement_kinds")
    return [
        _issue(
            row,
            path,
            node.lineno,
            f"global {', '.join(node.names)} rebinds module state",
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Global) and type(node).__name__ in kinds
    ]


# --- sibling_handler_import ----------------------------------------------------


def _check_sibling_handler_import(
    path: Path,
    fact: ModelHandlerDiModuleFact,
    tree: ast.Module,
    row: ModelValidatorRule,
) -> list[ModelValidationIssue]:
    importer = _pattern(row, "importer_path_pattern")
    not_importer = _pattern(row, "importer_exclude_pattern")
    imported = _pattern(row, "imported_module_pattern")
    if not importer.search(fact.posix_path) or not_importer.search(fact.posix_path):
        return []
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        else:
            continue
        for name in names:
            if imported.search(name.rsplit(".", 1)[-1]):
                issues.append(
                    _issue(row, path, node.lineno, f"imports handler module {name!r}")
                )
                break
    return issues


# --- contract_value_literal ----------------------------------------------------


def _docstring_nodes(tree: ast.Module) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                found.add(id(first.value))
    return found


def _check_contract_value_literal(
    path: Path, tree: ast.Module, row: ModelValidatorRule
) -> list[ModelValidationIssue]:
    constant_name = _pattern(row, "constant_name_pattern")
    value_patterns = _patterns(row, "value_patterns")
    issues: list[ModelValidationIssue] = []
    reported: set[int] = set()
    scopes: list[list[ast.stmt]] = [tree.body]
    scopes.extend(n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    for body in scopes:
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                targets, value = stmt.targets, stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                targets, value = [stmt.target], stmt.value
            else:
                continue
            if not (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str | int | float)
                and not isinstance(value.value, bool)
                and value.value != ""
            ):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and constant_name.search(target.id):
                    reported.add(id(value))
                    issues.append(
                        _issue(
                            row,
                            path,
                            stmt.lineno,
                            f"{target.id} holds a literal the contract or overlay owns",
                        )
                    )
                    break
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in reported
            and id(node) not in docstrings
            and any(p.fullmatch(node.value) for p in value_patterns)
        ):
            issues.append(
                _issue(
                    row,
                    path,
                    node.lineno,
                    f"literal {node.value!r} is a topic, URL or address the contract or overlay owns",
                )
            )
    return issues


# --- baseline_ratchet ----------------------------------------------------------


def parse_baseline(text: str | None) -> dict[str, int]:
    """Path -> number of findings, from ``<path> <count>`` lines; ``#`` lines are prose."""
    entries: dict[str, int] = {}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path, _, count = stripped.rpartition(" ")
        if path and count.isdigit():
            entries[path] = int(count)
    return entries


def apply_baseline(
    path: Path,
    issues: tuple[ModelValidationIssue, ...],
    baselined: int,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Hold a file to its baseline entry: no more findings than baselined, and none fewer unrecorded."""
    if not _active(rules, RULE_BASELINE):
        return issues
    row = rules[RULE_BASELINE]
    values = {"path": path.as_posix(), "count": len(issues), "baselined": baselined}
    if len(issues) > baselined:
        grown = (
            (_issue(row, path, 0, rule_string(row, "grew_message").format(**values)),)
            if baselined
            else ()
        )
        return (*issues, *grown)
    if len(issues) < baselined:
        return (
            _issue(row, path, 0, rule_string(row, "stale_message").format(**values)),
        )
    return ()


def baseline_growth(
    head: Mapping[str, int],
    base: Mapping[str, int],
    baseline_path: Path,
    rules: Mapping[str, ModelValidatorRule],
    moves: Mapping[str, str] | None = None,
) -> tuple[ModelValidationIssue, ...]:
    """Reject entries above their own or recorded origin's base allowance."""
    if not _active(rules, RULE_BASELINE):
        return ()
    row = rules[RULE_BASELINE]
    allowances = carry_baseline(head, base, moves or {})
    return tuple(
        _issue(
            row,
            baseline_path,
            0,
            rule_string(row, "growth_message").format(
                path=path, count=count, baselined=allowances[path]
            ),
        )
        for path, count in sorted(head.items())
        if count > allowances[path]
    )


def baseline_missing(
    head: Mapping[str, int],
    exists: Callable[[str], bool],
    baseline_path: Path,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Reject baseline entries whose files no longer exist."""
    if not _active(rules, RULE_BASELINE):
        return ()
    row = rules[RULE_BASELINE]
    return tuple(
        _issue(
            row,
            baseline_path,
            0,
            rule_string(row, "missing_message").format(path=path, count=count),
        )
        for path, count in sorted(head.items())
        if not exists(path)
    )


def _active(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> bool:
    row = rules.get(rule_id)
    return row is not None and row.enabled


def check_module(
    fact: ModelHandlerDiModuleFact, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one module under the enabled K1 rules, ordered by line."""
    try:
        tree = ast.parse(fact.source)
    except SyntaxError:
        return ()
    path = Path(fact.posix_path)
    issues: list[ModelValidationIssue] = []
    if _active(rules, RULE_CONSTRUCTOR):
        issues.extend(_check_constructor_signature(path, tree, rules[RULE_CONSTRUCTOR]))
    if _active(rules, RULE_DIRECT):
        issues.extend(_check_direct_construction(path, tree, rules[RULE_DIRECT]))
    if _active(rules, RULE_CALL_SITE):
        issues.extend(_check_call_site_construction(path, tree, rules[RULE_CALL_SITE]))
    if _active(rules, RULE_FALLBACK):
        issues.extend(_check_fallback_construction(path, tree, rules[RULE_FALLBACK]))
    if _active(rules, RULE_REFLECTIVE):
        issues.extend(
            _check_reflective_construction(path, tree, rules[RULE_REFLECTIVE])
        )
    if _active(rules, RULE_NONE_DEFAULT):
        issues.extend(
            _check_optional_port_default(path, tree, rules[RULE_NONE_DEFAULT])
        )
    if _active(rules, RULE_CONTRACT_LOAD):
        issues.extend(_check_contract_self_load(path, tree, rules[RULE_CONTRACT_LOAD]))
    if _active(rules, RULE_SINGLETON):
        issues.extend(_check_module_singleton(path, tree, rules[RULE_SINGLETON]))
    if _active(rules, RULE_SIBLING):
        issues.extend(
            _check_sibling_handler_import(path, fact, tree, rules[RULE_SIBLING])
        )
    if _active(rules, RULE_VALUE_LITERAL):
        issues.extend(
            _check_contract_value_literal(path, tree, rules[RULE_VALUE_LITERAL])
        )
    return tuple(sorted(issues, key=lambda i: (i.line_number or 0, i.code or "")))


__all__ = [
    "RULE_BASELINE",
    "RULE_CALL_SITE",
    "RULE_CONSTRUCTOR",
    "RULE_CONTRACT_LOAD",
    "RULE_DIRECT",
    "RULE_FALLBACK",
    "RULE_NONE_DEFAULT",
    "RULE_REFLECTIVE",
    "RULE_SIBLING",
    "RULE_SINGLETON",
    "RULE_VALUE_LITERAL",
    "ModelHandlerDiModuleFact",
    "apply_baseline",
    "baseline_growth",
    "baseline_missing",
    "check_module",
    "parse_baseline",
]
