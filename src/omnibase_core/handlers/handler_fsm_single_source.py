# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerFsmSingleSource -- the contract is the only source of a state machine (OMN-21513).

Pure, contract-driven detection of a second state machine in Python source: a mapping, set,
list, tuple or enum that holds two or more of the contract's state names, a chain of branches
on state literals, and a reducer whose sources never call the core executor. Every rule value
is the validator contract's (``fsm_single_source.validation.yaml``), never a constant here.
No filesystem, no clock, no environment.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_fsm_single_source_request import (
    ModelFsmSingleSourceRequest,
)
from omnibase_core.models.validation.model_fsm_single_source_result import (
    ModelFsmSingleSourceResult,
)
from omnibase_core.models.validation.model_fsm_single_source_rules import (
    ModelFsmSingleSourceRules,
)
from omnibase_core.models.validation.model_fsm_source_text import ModelFsmSourceText
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["HandlerFsmSingleSource"]


def _issue(
    rules: ModelFsmSingleSourceRules,
    rule_id: str,
    source: str | None,
    message: str,
    line: int | None = None,
) -> Iterator[ModelValidationIssue]:
    severity = rules.severity_of(rule_id)
    if severity is not None:
        yield ModelValidationIssue(
            code=rule_id,
            rule_name=rule_id,
            severity=severity,
            file_path=Path(source) if source is not None else None,
            line_number=line,
            message=message,
        )


def _items(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _state_names(
    machine: dict[str, object], rules: ModelFsmSingleSourceRules
) -> tuple[str, ...]:
    names: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value and value not in names:
            names.append(value)

    for state in _items(machine.get(rules.state_list_key)):
        if isinstance(state, dict):
            add(state.get(rules.state_name_key))
    for key in rules.state_scalar_keys:
        add(machine.get(key))
    for key in rules.state_list_keys:
        for value in _items(machine.get(key)):
            add(value)
    for transition in _items(machine.get(rules.transition_list_key)):
        if isinstance(transition, dict):
            for key in rules.transition_state_keys:
                add(transition.get(key))
    return tuple(names)


def _read_state_names(
    source: ModelFsmSourceText,
    rules: ModelFsmSingleSourceRules,
    issues: list[ModelValidationIssue],
) -> tuple[str, ...]:
    try:
        document = load_yaml_mapping_no_duplicates(source.text, source=source.name)
    except (yaml.YAMLError, ValueError) as error:
        issues.extend(
            _issue(
                rules,
                "contract_unreadable",
                source.name,
                f"{source.name}: not valid YAML ({type(error).__name__})",
            )
        )
        return ()
    machine = document.get(rules.state_machine_key)
    names = _state_names(machine, rules) if isinstance(machine, dict) else ()
    if not names:
        issues.extend(
            _issue(
                rules,
                "state_machine_missing",
                source.name,
                f"{source.name}: declares no {rules.state_machine_key} with {rules.state_list_key}",
            )
        )
    return names


def _literal_states(node: ast.AST, states: frozenset[str]) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and child.value in states
    }


def _is_enum_class(node: ast.ClassDef, rules: ModelFsmSingleSourceRules) -> bool:
    for base in node.bases:
        name = (
            base.id
            if isinstance(base, ast.Name)
            else base.attr
            if isinstance(base, ast.Attribute)
            else ""
        )
        if name.endswith(rules.enum_base_suffixes):
            return True
    return False


def _enum_states(node: ast.ClassDef, states: frozenset[str]) -> set[str]:
    found: set[str] = set()
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            targets = [t.id for t in statement.targets if isinstance(t, ast.Name)]
            value: ast.AST | None = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            targets = [statement.target.id]
            value = statement.value
        else:
            continue
        found.update(name.lower() for name in targets if name.lower() in states)
        if value is not None:
            found.update(_literal_states(value, states))
    return found


def _table_issues(
    tree: ast.AST,
    source: str,
    states: frozenset[str],
    rules: ModelFsmSingleSourceRules,
) -> Iterator[ModelValidationIssue]:
    if rules.severity_of("state_table") is None:
        return
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        held: set[str] = set()
        kind = ""
        if isinstance(node, rules.collection_nodes):
            held = _literal_states(node, states)
            kind = type(node).__name__.lower()
        elif isinstance(node, ast.ClassDef) and _is_enum_class(node, rules):
            held = _enum_states(node, states)
            kind = "enum"
        if len(held) >= rules.min_table_states and isinstance(
            node, (*rules.collection_nodes, ast.ClassDef)
        ):
            line = cast(ast.expr | ast.stmt, node).lineno
            yield from _issue(
                rules,
                "state_table",
                source,
                f"{source} line {line}: a {kind} holds the states "
                f"{', '.join(sorted(held))} of the contract's state machine; "
                f"ask {rules.executor_name} instead of keeping a second table",
                line,
            )
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Visit one scope without entering nested functions."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stack.extend(ast.iter_child_nodes(node))


def _compared_states(
    test: ast.AST, states: frozenset[str], rules: ModelFsmSingleSourceRules
) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(test):
        if isinstance(child, ast.Compare) and all(
            isinstance(op, rules.compare_operators) for op in child.ops
        ):
            found |= _literal_states(child, states)
    return found


def _branch_issues(
    tree: ast.AST,
    source: str,
    states: frozenset[str],
    rules: ModelFsmSingleSourceRules,
) -> Iterator[ModelValidationIssue]:
    if rules.severity_of("state_branch_chain") is None:
        return
    for scope in ast.walk(tree):
        if not isinstance(scope, rules.scope_nodes):
            continue
        branches: list[tuple[int, set[str]]] = []
        for node in _scope_nodes(scope):
            if isinstance(node, ast.If):
                compared = _compared_states(node.test, states, rules)
                if compared:
                    branches.append((node.lineno, compared))
            elif isinstance(node, ast.Match):
                cases = {
                    pattern.value.value
                    for case in node.cases
                    for pattern in ast.walk(case.pattern)
                    if isinstance(pattern, ast.MatchValue)
                    and isinstance(pattern.value, ast.Constant)
                    and isinstance(pattern.value.value, str)
                    and pattern.value.value in states
                }
                if cases:
                    branches.append((node.lineno, cases))
        distinct: set[str] = set().union(*(held for _, held in branches))
        if (
            len(branches) >= rules.min_branches
            and len(distinct) >= rules.min_branch_states
        ):
            line = min(lineno for lineno, _ in branches)
            yield from _issue(
                rules,
                "state_branch_chain",
                source,
                f"{source} line {line}: a chain of branches compares the states "
                f"{', '.join(sorted(distinct))}; the contract decides the "
                f"transition, ask {rules.executor_name}",
                line,
            )


def _calls_executor(tree: ast.AST, rules: ModelFsmSingleSourceRules) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Name) and func.id == rules.executor_name) or (
                isinstance(func, ast.Attribute) and func.attr == rules.executor_name
            ):
                return True
    return False


class HandlerFsmSingleSource:
    """COMPUTE handler: a reducer contract's text and its sources' text in, issues out."""

    def handle(
        self, request: ModelFsmSingleSourceRequest
    ) -> ModelFsmSingleSourceResult:
        """Definition-B canonical entry-point: typed request in, typed result out."""
        return _check(request.contract_source, request.sources, request.rules)


def _check(
    contract_source: ModelFsmSourceText,
    sources: tuple[ModelFsmSourceText, ...],
    rules: ModelFsmSingleSourceRules,
) -> ModelFsmSingleSourceResult:
    issues: list[ModelValidationIssue] = []
    names = _read_state_names(contract_source, rules, issues)
    states = frozenset(names)
    parsed: list[tuple[str, ast.AST]] = []
    for source in sources:
        try:
            parsed.append((source.name, ast.parse(source.text)))
        except SyntaxError as error:
            issues.extend(
                _issue(
                    rules,
                    "source_unparseable",
                    source.name,
                    f"{source.name}: not valid Python ({error.msg})",
                    error.lineno,
                )
            )
    for name, tree in parsed:
        if not states:
            break
        found = [
            *_table_issues(tree, name, states, rules),
            *_branch_issues(tree, name, states, rules),
        ]
        issues.extend(sorted(found, key=lambda issue: issue.line_number or 0))
    all_parsed = len(parsed) == len(sources)
    if (
        rules.severity_of("execute_transition_missing") is not None
        and all_parsed
        and not any(_calls_executor(tree, rules) for _, tree in parsed)
    ):
        issues.extend(
            _issue(
                rules,
                "execute_transition_missing",
                sources[0].name if sources else None,
                f"no source calls {rules.executor_name}: the reducer's handler "
                "must run its transitions through core's executor",
            )
        )
    return ModelFsmSingleSourceResult(issues=tuple(issues), state_names=names)
