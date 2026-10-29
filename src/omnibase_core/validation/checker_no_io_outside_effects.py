# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker K4: I/O is permitted only in EFFECT nodes (OMN-21532, findings F28, F39, F40).

Facts in (one node contract and, optionally, one module found anywhere under the
contract's directory), ``ModelValidationIssue`` out: no file read, no clock, no
environment. A module is judged unless its nearest contract declares an exempt
archetype; a contract that names no recognised archetype is judged as non-EFFECT
(fail closed) and reported by ``package_scope``.

Every rule row of ``contracts/no_io_outside_effects.validation.yaml`` names one
surface through matcher parameters; this module holds none of them. A call, import or
subscript is reported once, under the first enabled row that matches it, in the order
of the contract. A row with no matcher, an unknown parameter, a mistyped value or a
pattern that does not compile is an invalid contract and raises
(``ModelOnexError``); it never passes.

Matcher parameters: ``import_roots``, ``import_modules``, ``callee_patterns`` (full
match against the dotted callee), ``method_names`` (attribute called on any base), any
key ending ``_class_patterns`` (full match against the last segment of the callee),
``command_executables`` with ``command_callee_patterns`` (the first command word of
a matching call), ``subscripts``, ``url_substrings`` (string arguments), and
``open_names`` with ``open_mode_chars`` and ``open_when`` (``write`` or ``read``).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from functools import cache
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_no_io_outside_effects_facts import (
    ModelNoIoOutsideEffectsFacts,
)
from omnibase_core.models.validation.model_no_io_outside_effects_matcher import (
    ModelNoIoOutsideEffectsMatcher,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
    rule_strings,
)

RULE_SCOPE = "package_scope"
RULE_CONTRACT_UNPARSEABLE = "contract_does_not_parse"
RULE_MODULE_UNPARSEABLE = "module_does_not_parse"

_CLASS_PATTERNS_SUFFIX = "_class_patterns"


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=f"no_io_outside_effects rule {rule.rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
    )


@cache
def _compiled(pattern: str) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern)
    except re.error:
        return None


def _regexes(rule: ModelValidatorRule, key: str) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for pattern in rule_strings(rule, key):
        regex = _compiled(pattern)
        if regex is None:
            raise _invalid(
                rule,
                f"parameters.{key} holds an invalid regular expression {pattern!r}",
            )
        compiled.append(regex)
    return tuple(compiled)


def _optional_strings(rule: ModelValidatorRule, key: str) -> tuple[str, ...]:
    return rule_strings(rule, key) if key in (rule.parameters or {}) else ()


def _matcher(rule: ModelValidatorRule) -> ModelNoIoOutsideEffectsMatcher:
    parameters = rule.parameters or {}
    rule_string(rule, "remediation")
    class_keys = [k for k in parameters if k.endswith(_CLASS_PATTERNS_SUFFIX)]
    known = {
        "remediation",
        "import_roots",
        "import_modules",
        "callee_patterns",
        "method_names",
        "command_executables",
        "command_callee_patterns",
        "subscripts",
        "url_substrings",
        "open_names",
        "open_mode_chars",
        "open_when",
    } | set(class_keys)
    unknown = sorted(set(parameters) - known)
    if unknown:
        raise _invalid(rule, f"unknown parameters {unknown}")
    classes = tuple(r for key in class_keys for r in _regexes(rule, key))
    executables = _optional_strings(rule, "command_executables")
    command_callees = (
        _regexes(rule, "command_callee_patterns")
        if "command_callee_patterns" in parameters
        else ()
    )
    if bool(executables) != bool(command_callees):
        raise _invalid(
            rule, "command_executables and command_callee_patterns go together"
        )
    open_names = frozenset(_optional_strings(rule, "open_names"))
    open_mode_chars = ""
    open_when = ""
    if open_names:
        open_mode_chars = rule_string(rule, "open_mode_chars")
        open_when = rule_string(rule, "open_when")
        if open_when not in {"write", "read"}:
            raise _invalid(rule, "parameters.open_when must be 'write' or 'read'")
    matcher = ModelNoIoOutsideEffectsMatcher(
        rule=rule,
        import_roots=frozenset(_optional_strings(rule, "import_roots")),
        import_modules=_optional_strings(rule, "import_modules"),
        callees=_regexes(rule, "callee_patterns")
        if "callee_patterns" in parameters
        else (),
        methods=frozenset(_optional_strings(rule, "method_names")),
        classes=classes,
        executables=executables,
        command_callees=command_callees,
        subscripts=frozenset(_optional_strings(rule, "subscripts")),
        url_substrings=_optional_strings(rule, "url_substrings"),
        open_names=open_names,
        open_mode_chars=open_mode_chars,
        open_when=open_when,
    )
    if not any(
        (
            matcher.import_roots,
            matcher.import_modules,
            matcher.callees,
            matcher.methods,
            matcher.classes,
            matcher.executables,
            matcher.subscripts,
            matcher.url_substrings,
            matcher.open_names,
        )
    ):
        raise _invalid(rule, "names no matcher parameter")
    return matcher


def _row(rules: Mapping[str, ModelValidatorRule], rule_id: str) -> ModelValidatorRule:
    row = rules.get(rule_id)
    if row is None:
        raise ModelOnexError(
            message=f"no_io_outside_effects contract has no rule row {rule_id!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return row


def _issue(
    row: ModelValidatorRule,
    path: str,
    message: str,
    line: int | None = None,
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=row.severity,
        message=message,
        code=row.rule_id,
        file_path=Path(path),
        line_number=line,
        rule_name=row.rule_id,
        suggestion=rule_string(row, "remediation"),
    )


def _archetype(data: object, scope: ModelValidatorRule) -> str | None:
    """The first declared archetype that the scope row recognises, else None."""
    known = {a.lower() for a in rule_strings(scope, "known_archetypes")}
    for field in rule_strings(scope, "archetype_fields"):
        value: object = data
        for part in field.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, str) and value.strip().lower() in known:
            return value.strip().lower()
    return None


def _dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _command_word(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        words = first.value.split()
        return words[0] if words else None
    if isinstance(first, ast.List | ast.Tuple) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    return None


def _open_mode(call: ast.Call) -> str:
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        value = call.args[1].value
        return value if isinstance(value, str) else ""
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            value = keyword.value.value
            return value if isinstance(value, str) else ""
    return ""


class _Scan(ast.NodeVisitor):
    """Walk one module; each node is reported under the first row that matches it."""

    def __init__(
        self, path: str, matchers: list[ModelNoIoOutsideEffectsMatcher]
    ) -> None:
        self._path = path
        self._matchers = matchers
        self.issues: list[ModelValidationIssue] = []

    def _report(
        self,
        node: ast.expr | ast.stmt,
        matcher: ModelNoIoOutsideEffectsMatcher,
        detail: str,
    ) -> None:
        self.issues.append(
            _issue(
                matcher.rule,
                self._path,
                f"{self._path}:{node.lineno}: {detail} in a non-EFFECT node package "
                f"(rule {matcher.rule.rule_id}): {matcher.rule.description}",
                node.lineno,
            )
        )

    def _import(self, node: ast.stmt, module: str) -> None:
        root = module.split(".", 1)[0]
        for matcher in self._matchers:
            if root in matcher.import_roots or any(
                module == m or module.startswith(f"{m}.")
                for m in matcher.import_modules
            ):
                self._report(node, matcher, f"import of {module}")
                return

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._import(node, alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is not None and node.level == 0:
            self._import(node, node.module)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        target = _dotted(node.value)
        if target is not None:
            for matcher in self._matchers:
                if target in matcher.subscripts:
                    self._report(node, matcher, f"{target}[...]")
                    break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._call(node)
        self.generic_visit(node)

    def _call(self, node: ast.Call) -> None:
        func = node.func
        dotted = _dotted(func)
        attr = func.attr if isinstance(func, ast.Attribute) else None
        last = dotted.rsplit(".", 1)[-1] if dotted else attr
        for matcher in self._matchers:
            if self._call_matches(node, matcher, dotted, attr, last):
                self._report(node, matcher, f"{dotted or attr or 'call'}(...)")
                return

    @staticmethod
    def _call_matches(
        node: ast.Call,
        matcher: ModelNoIoOutsideEffectsMatcher,
        dotted: str | None,
        attr: str | None,
        last: str | None,
    ) -> bool:
        if dotted is not None and any(p.fullmatch(dotted) for p in matcher.callees):
            return True
        if attr is not None and attr in matcher.methods:
            return True
        if last is not None and any(p.fullmatch(last) for p in matcher.classes):
            return True
        if (
            dotted is not None
            and matcher.executables
            and any(p.fullmatch(dotted) for p in matcher.command_callees)
        ):
            word = _command_word(node)
            if word is not None and any(
                word == e or word.endswith(f"/{e}") for e in matcher.executables
            ):
                return True
        if matcher.url_substrings and any(
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and any(s in arg.value for s in matcher.url_substrings)
            for arg in node.args
        ):
            return True
        if isinstance(node.func, ast.Name) and node.func.id in matcher.open_names:
            writes = any(c in _open_mode(node) for c in matcher.open_mode_chars)
            return writes == (matcher.open_when == "write")
        return False


def check_no_io_outside_effects(
    facts: ModelNoIoOutsideEffectsFacts,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one contract alone, or for one module judged in its contract's package."""
    scope = _row(rules, RULE_SCOPE)
    contract = facts.contract
    try:
        data = load_yaml_mapping_no_duplicates(contract.source, source=contract.path)
    except (yaml.YAMLError, ValueError) as exc:
        row = _row(rules, RULE_CONTRACT_UNPARSEABLE)
        if facts.module is None and row.enabled:
            return (
                _issue(
                    row,
                    contract.path,
                    f"{contract.path}: contract does not parse: {exc}",
                ),
            )
        return ()
    archetype = _archetype(data, scope)
    if facts.module is None:
        if archetype is None and scope.enabled:
            return (
                _issue(
                    scope,
                    contract.path,
                    f"{contract.path}: names no recognised archetype "
                    f"(rule {RULE_SCOPE}): {scope.description}",
                ),
            )
        return ()
    exempt = {a.lower() for a in rule_strings(scope, "exempt_archetypes")}
    if archetype in exempt:
        return ()
    matchers = [
        _matcher(row)
        for rule_id, row in rules.items()
        if row.enabled
        and rule_id
        not in {RULE_SCOPE, RULE_CONTRACT_UNPARSEABLE, RULE_MODULE_UNPARSEABLE}
    ]
    module = facts.module
    try:
        tree = ast.parse(module.source, filename=module.path)
    except SyntaxError as exc:
        row = _row(rules, RULE_MODULE_UNPARSEABLE)
        if not row.enabled:
            return ()
        return (
            _issue(row, module.path, f"{module.path}: module does not parse: {exc}"),
        )
    scan = _Scan(module.path, matchers)
    scan.visit(tree)
    return tuple(scan.issues)


__all__ = [
    "RULE_CONTRACT_UNPARSEABLE",
    "RULE_MODULE_UNPARSEABLE",
    "RULE_SCOPE",
    "check_no_io_outside_effects",
]
