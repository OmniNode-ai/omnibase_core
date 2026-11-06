# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker: a provider change removes nothing its consumers import (OMN-22478).

omnibase_infra#5683 moved a model and removed its old import path. Every test of
that repository passed, because no test there imports omnimarket, and omnimarket's
ledger writer loads that path at module scope. The venvs taking omnibase_infra from
a moving clone stopped writing ledger rows when the clone synced.

So this judges the difference a pull request makes: an import in a consumer's source
that resolves against the provider at the base revision and does not at the head is
refused. An import that was already broken at the base is not this change's doing and
stays out, so a consumer's own drift never holds a provider pull request.

Reading is static, so the provider's CI installs no consumer, and a consumer import
inside a function counts: it fails when called, not when loaded. Imports under a
type-checking guard do not count, having no runtime effect. Facts in, issues out: no
file read, no clock, no environment.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_provider_import_surface_input import (
    ModelProviderImportSurfaceInput,
)
from omnibase_core.models.validation.model_provider_module_fact import (
    ModelProviderModuleFact,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_string,
    rule_strings,
)

RULE_REMOVED = "consumer_import_removed"
RULE_UNPARSEABLE = "consumer_source_does_not_parse"
RULE_NOTHING_READ = "nothing_read"


def _is_guard(node: ast.If, guards: tuple[str, ...]) -> bool:
    test = node.test
    if isinstance(test, ast.Name):
        return test.id in guards
    return isinstance(test, ast.Attribute) and test.attr in guards


def _runtime_imports(
    tree: ast.AST, guards: tuple[str, ...]
) -> Iterator[ast.Import | ast.ImportFrom]:
    """Every import in ``tree`` outside the body of a type-checking guard."""
    for child in ast.iter_child_nodes(tree):
        if isinstance(child, ast.If) and _is_guard(child, guards):
            for orelse in child.orelse:
                if isinstance(orelse, ast.Import | ast.ImportFrom):
                    yield orelse
                else:
                    yield from _runtime_imports(orelse, guards)
            continue
        if isinstance(child, ast.Import | ast.ImportFrom):
            yield child
        yield from _runtime_imports(child, guards)


def _provider_imports(
    node: ast.Import | ast.ImportFrom, package: str
) -> Iterator[tuple[str, str | None]]:
    """(module, imported name) pairs of ``node`` that name ``package``."""
    prefix = f"{package}."
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name == package or alias.name.startswith(prefix):
                yield alias.name, None
        return
    module = node.module or ""
    if node.level or not (module == package or module.startswith(prefix)):
        return
    for alias in node.names:
        yield module, None if alias.name == "*" else alias.name


def provider_module_fact(module: str, source: str) -> ModelProviderModuleFact:
    """What ``source`` binds at its top level, read without importing it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ModelProviderModuleFact(module=module, opaque=True)
    names: set[str] = set()
    opaque = False
    pending: list[ast.stmt] = list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
            opaque = opaque or node.name == "__getattr__"
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                opaque = opaque or alias.name == "*"
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names.update(
                    item.id for item in ast.walk(target) if isinstance(item, ast.Name)
                )
        elif isinstance(node, ast.If | ast.Try | ast.With):
            # A name bound in a conditional branch counts as present in every branch.
            pending.extend(
                child
                for child in ast.iter_child_nodes(node)
                if isinstance(child, ast.stmt)
            )
            for handler in getattr(node, "handlers", ()):
                pending.extend(handler.body)
    return ModelProviderModuleFact(module=module, names=frozenset(names), opaque=opaque)


def _resolves(
    module: str, name: str | None, table: Mapping[str, ModelProviderModuleFact]
) -> bool:
    fact = table.get(module)
    if fact is None:
        return False
    return (
        name is None or fact.opaque or name in fact.names or f"{module}.{name}" in table
    )


def _issue(
    row: ModelValidatorRule, path: str, line: int | None, message: str
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


def check_provider_import_surface(
    request: ModelProviderImportSurfaceInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for each consumer source in ``request``."""
    head = {fact.module: fact for fact in request.head}
    base = {fact.module: fact for fact in request.base}
    removed = rules.get(RULE_REMOVED)
    unparseable = rules.get(RULE_UNPARSEABLE)
    issues: list[ModelValidationIssue] = []
    for consumer in request.consumers:
        try:
            tree = ast.parse(consumer.source)
        except SyntaxError as exc:
            if unparseable is not None and unparseable.enabled:
                issues.append(
                    _issue(
                        unparseable,
                        consumer.path,
                        exc.lineno,
                        f"{consumer.path} does not parse, so its imports cannot be judged.",
                    )
                )
            continue
        if removed is None or not removed.enabled:
            continue
        guards = rule_strings(removed, "type_checking_guards")
        for node in _runtime_imports(tree, guards):
            for module, name in _provider_imports(node, request.provider_package):
                if _resolves(module, name, base) and not _resolves(module, name, head):
                    target = module if name is None else f"{module}.{name}"
                    issues.append(
                        _issue(
                            removed,
                            consumer.path,
                            node.lineno,
                            f"{consumer.path} imports {target}, which the base revision "
                            "provides and this head removes.",
                        )
                    )
    return tuple(issues)


def check_something_read(
    request: ModelProviderImportSurfaceInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Refuse a run that read an empty tree: a check that sees nothing is not a pass."""
    row = rules.get(RULE_NOTHING_READ)
    if row is None or not row.enabled:
        return ()
    empty = (
        ("consumer source", not request.consumers),
        ("provider head", not request.head),
        ("provider base", not request.base),
    )
    return tuple(
        _issue(row, request.provider_package, None, f"No {what} was read.")
        for what, missing in empty
        if missing
    )
