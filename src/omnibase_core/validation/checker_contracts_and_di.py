# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure contracts-and-DI checker: facts in, ``ModelValidationIssue`` out (OMN-21623).

RULING 2026-10-29T01:06:13Z: every dependency is captured in contracts and contract
overlays, no value is hard-coded, and an in-memory default is only ever injected
through DI. This module judges one file's text against the rule rows of
``contracts/contracts_and_di.validation.yaml``. Every pattern, name list, glob,
threshold and remediation text is a ``parameters`` entry of a row; nothing here
names a host, a topic, a class or a path. The module performs no I/O: no file read,
no clock, no environment.

Rule row kinds (the ``kind`` parameter):

* ``code_literal`` (family a) -- in Python source, a string constant matching one of
  ``value_patterns``; a constant of ``value_kinds`` passed to a keyword or parameter
  whose name matches ``keyword_name_patterns``, assigned to a name matching
  ``target_name_patterns``, or passed positionally to a call matching
  ``call_name_patterns``, when its text matches one of ``named_value_patterns`` (an
  empty list admits any). Docstrings, values in ``allowed_values`` and constants
  under a keyword of ``ignore_keyword_names`` or a call of ``ignore_call_names``
  are not judged.
* ``repeated_block`` (family b) -- in a YAML document, two sibling blocks keyed by
  different identities (a sequence item whose first key is one of ``identity_keys``,
  or a child of a mapping under a key of ``container_keys``) whose flattened entries, less
  ``ignore_keys``, share at least ``min_shared_entries`` entries and at least
  ``min_overlap_ratio`` of the smaller block: a role hand-copied per principal or host.
* ``construction`` (family c) -- in Python source, a call of a class matching
  ``class_patterns`` (and no ``exclude_class_patterns``) outside ``allowed_site_globs``,
  unless the call is an argument of a registration call in ``registration_call_names``.
* ``first_party_pin`` (family d) -- in a file matching ``file_globs``, a match of one
  of ``patterns`` (``{org}`` replaced by ``github_org``; named groups ``repo`` and
  ``ref``) whose pinned repository declares a dev-merge tag source and whose site no
  advancer manifest declares (the facts).
* ``unparseable`` -- a target file that does not parse as Python or YAML, so no other
  row could judge it.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator, Sequence
from fnmatch import fnmatch
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_contracts_and_di_facts import (
    ModelContractsAndDiFacts,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_float,
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = [
    "check_contracts_and_di",
    "pin_fact_parameters",
    "validate_rows",
]


def _kind(rule: ModelValidatorRule) -> str:
    return rule_string(rule, "kind")


def _compile(rule: ModelValidatorRule, key: str) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for text in rule_strings(rule, key):
        try:
            compiled.append(re.compile(text))
        except re.error as exc:
            raise ModelOnexError(
                message=f"rule {rule.rule_id!r}: parameters.{key} entry {text!r} is not a regular expression: {exc}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            ) from exc
    return tuple(compiled)


def _invalid(rule: ModelValidatorRule, detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=f"rule {rule.rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
    )


def validate_rows(rules: Sequence[ModelValidatorRule]) -> None:
    """Read every parameter of every enabled row so a broken contract raises, never passes."""
    for rule in rules:
        if not rule.enabled:
            continue
        kind = _kind(rule)
        rule_string(rule, "remediation")
        if kind == "code_literal":
            for key in (
                "value_patterns",
                "keyword_name_patterns",
                "target_name_patterns",
                "call_name_patterns",
                "named_value_patterns",
            ):
                _compile(rule, key)
            kinds = set(rule_strings(rule, "value_kinds"))
            if not kinds or not kinds <= {"str", "int", "float"}:
                raise _invalid(
                    rule, "parameters.value_kinds must name str, int or float"
                )
            rule_strings(rule, "allowed_values")
            rule_strings(rule, "ignore_keyword_names")
            rule_strings(rule, "ignore_call_names")
        elif kind == "repeated_block":
            rule_strings(rule, "file_globs")
            rule_strings(rule, "identity_keys")
            rule_strings(rule, "container_keys")
            rule_strings(rule, "ignore_keys")
            if rule_int(rule, "min_shared_entries") < 1:
                raise _invalid(rule, "parameters.min_shared_entries must be positive")
            ratio = rule_float(rule, "min_overlap_ratio")
            if not 0.0 < ratio <= 1.0:
                raise _invalid(rule, "parameters.min_overlap_ratio must be in (0, 1]")
        elif kind == "construction":
            _compile(rule, "class_patterns")
            _compile(rule, "exclude_class_patterns")
            rule_strings(rule, "allowed_site_globs")
            rule_strings(rule, "registration_call_names")
        elif kind == "unparseable":
            pass
        elif kind == "first_party_pin":
            rule_strings(rule, "file_globs")
            rule_string(rule, "github_org")
            for pattern in _pin_patterns(rule):
                if not {"repo", "ref"} <= set(pattern.groupindex):
                    raise _invalid(
                        rule,
                        "every parameters.patterns entry needs groups repo and ref",
                    )
            pin_fact_parameters(rule)
        else:
            raise _invalid(rule, f"unknown kind {kind!r}")


def pin_fact_parameters(
    rule: ModelValidatorRule,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """A pin row's fact sources: tag source globs, advancer manifests, manifest keys.

    The manifest keys are, in order: the repository list, the repository name, the
    pin-site list, the pin-site path, the dependency-pin entry and its pyproject path
    with the default pyproject path after it.
    """
    keys = rule_strings(rule, "manifest_keys")
    if len(keys) != 7:
        raise _invalid(rule, "parameters.manifest_keys needs seven entries")
    manifests = rule_strings(rule, "advancer_manifests")
    for manifest in manifests:
        if ":" not in manifest:
            raise _invalid(
                rule, f"advancer manifest {manifest!r} is not '<repository>:<path>'"
            )
    return rule_strings(rule, "tag_source_globs"), manifests, keys


def _issue(
    rule: ModelValidatorRule, path: Path, detail: str, line: int | None
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{detail} -- {rule_string(rule, 'remediation')}",
        code=rule.rule_id,
        file_path=path,
        line_number=line,
        rule_name=rule.rule_id,
    )


def _matches_glob(path: Path, globs: Sequence[str]) -> bool:
    posix = path.as_posix()
    return any(fnmatch(posix, glob) or fnmatch(path.name, glob) for glob in globs)


# ---------------------------------------------------------------- family (a), (c)


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for element in node.elts for name in _target_names(element)]
    return []


def _docstring_ids(tree: ast.Module) -> set[int]:
    skipped: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            skipped.add(id(node.value))
    return skipped


def _ignored_ids(tree: ast.Module, keywords: set[str], calls: set[str]) -> set[int]:
    skipped: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _called_name(node) in calls:
            skipped.update(id(sub) for sub in ast.walk(node))
            continue
        for keyword in node.keywords:
            if keyword.arg in keywords:
                skipped.update(id(sub) for sub in ast.walk(keyword.value))
    return skipped


def _constant_kind(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
        return None
    if isinstance(node.value, str):
        return "str"
    if isinstance(node.value, int):
        return "int"
    if isinstance(node.value, float):
        return "float"
    return None


def _any_match(patterns: Sequence[re.Pattern[str]], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _parameter_defaults(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[tuple[str, ast.expr]]:
    positional = [*node.args.posonlyargs, *node.args.args]
    for arg, default in zip(
        positional[len(positional) - len(node.args.defaults) :],
        node.args.defaults,
        strict=True,
    ):
        yield arg.arg, default
    for arg, kw_default in zip(
        node.args.kwonlyargs, node.args.kw_defaults, strict=True
    ):
        if kw_default is not None:
            yield arg.arg, kw_default


def _named_literals(
    tree: ast.Module,
    keyword_patterns: Sequence[re.Pattern[str]],
    target_patterns: Sequence[re.Pattern[str]],
    call_patterns: Sequence[re.Pattern[str]],
) -> Iterator[tuple[ast.expr, str]]:
    """Each constant bound to a matching keyword, parameter, target or call, with that name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg and _any_match(keyword_patterns, keyword.arg):
                    yield keyword.value, keyword.arg
            name = _called_name(node)
            if name and _any_match(call_patterns, name):
                for arg in node.args:
                    yield arg, name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for name, default in _parameter_defaults(node):
                if _any_match(keyword_patterns, name):
                    yield default, name
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name in _target_names(target):
                    if _any_match(target_patterns, name):
                        yield node.value, name
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            for name in _target_names(node.target):
                if _any_match(target_patterns, name):
                    yield node.value, name


def _check_code_literal(
    rule: ModelValidatorRule, path: Path, tree: ast.Module
) -> list[ModelValidationIssue]:
    value_patterns = _compile(rule, "value_patterns")
    kinds = set(rule_strings(rule, "value_kinds"))
    allowed = set(rule_strings(rule, "allowed_values"))
    skipped = _docstring_ids(tree) | _ignored_ids(
        tree,
        set(rule_strings(rule, "ignore_keyword_names")),
        set(rule_strings(rule, "ignore_call_names")),
    )
    shapes = _compile(rule, "named_value_patterns")
    found: dict[int, tuple[ast.Constant, str]] = {}
    if value_patterns:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skipped
                and node.value not in allowed
                and _any_match(value_patterns, node.value)
            ):
                found[id(node)] = (node, "literal")
    for value, name in _named_literals(
        tree,
        _compile(rule, "keyword_name_patterns"),
        _compile(rule, "target_name_patterns"),
        _compile(rule, "call_name_patterns"),
    ):
        kind = _constant_kind(value)
        if (
            kind in kinds
            and isinstance(value, ast.Constant)
            and id(value) not in skipped
            and str(value.value) not in allowed
            and (not shapes or _any_match(shapes, str(value.value)))
        ):
            found.setdefault(id(value), (value, name))
    ordered = sorted(found.values(), key=lambda hit: (hit[0].lineno, hit[0].col_offset))
    return [
        _issue(
            rule,
            path,
            f"literal {node.value!r}"
            + ("" if name == "literal" else f" bound to {name!r}")
            + " is hard-coded in code",
            node.lineno,
        )
        for node, name in ordered
    ]


def _registration_argument_ids(tree: ast.Module, names: set[str]) -> set[int]:
    bound: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _called_name(node) in names:
            for arg in [*node.args, *(keyword.value for keyword in node.keywords)]:
                bound.add(id(arg))
    return bound


def _check_construction(
    rule: ModelValidatorRule, path: Path, tree: ast.Module
) -> list[ModelValidationIssue]:
    if _matches_glob(path, rule_strings(rule, "allowed_site_globs")):
        return []
    classes = _compile(rule, "class_patterns")
    excluded = _compile(rule, "exclude_class_patterns")
    registered = _registration_argument_ids(
        tree, set(rule_strings(rule, "registration_call_names"))
    )
    issues: list[ModelValidationIssue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in registered:
            continue
        name = _called_name(node)
        if (
            name
            and any(pattern.fullmatch(name) for pattern in classes)
            and not any(pattern.fullmatch(name) for pattern in excluded)
        ):
            issues.append(
                _issue(
                    rule,
                    path,
                    f"{name} is constructed by hand instead of resolved from the container",
                    node.lineno,
                )
            )
    return sorted(issues, key=lambda issue: issue.line_number or 0)


# ---------------------------------------------------------------- family (b)


def _canonical(node: yaml.Node) -> str:
    if isinstance(node, yaml.ScalarNode):
        return str(node.value)
    if isinstance(node, yaml.SequenceNode):
        return json.dumps([_canonical(item) for item in node.value])
    if isinstance(node, yaml.MappingNode):
        return json.dumps(
            {_canonical(key): _canonical(value) for key, value in node.value},
            sort_keys=True,
        )
    return ""


def _flatten(node: yaml.Node, prefix: str, ignore: set[str]) -> Iterator[str]:
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            name = _canonical(key)
            if name in ignore:
                continue
            yield from _flatten(value, f"{prefix}.{name}" if prefix else name, ignore)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield f"{prefix}[]={_canonical(item)}"
    else:
        yield f"{prefix}={_canonical(node)}"


def _blocks(
    root: yaml.Node, identity_keys: set[str], container_keys: set[str]
) -> Iterator[list[tuple[str, int, yaml.MappingNode]]]:
    """Each group of sibling identity blocks: (identity, line, block mapping)."""
    stack: list[yaml.Node] = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, yaml.SequenceNode):
            group = []
            for item in node.value:
                if not isinstance(item, yaml.MappingNode) or not item.value:
                    continue
                key, value = item.value[0]
                if _canonical(key) in identity_keys and isinstance(
                    value, yaml.ScalarNode
                ):
                    group.append((str(value.value), item.start_mark.line + 1, item))
            if len(group) > 1:
                yield group
            stack.extend(node.value)
        elif isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                if _canonical(key) in container_keys and isinstance(
                    value, yaml.MappingNode
                ):
                    group = [
                        (_canonical(child_key), child_key.start_mark.line + 1, child)
                        for child_key, child in value.value
                        if isinstance(child, yaml.MappingNode)
                    ]
                    if len(group) > 1:
                        yield group
                stack.append(value)


def _check_repeated_block(
    rule: ModelValidatorRule, path: Path, documents: Sequence[yaml.Node]
) -> list[ModelValidationIssue]:
    identity_keys = set(rule_strings(rule, "identity_keys"))
    ignore = set(rule_strings(rule, "ignore_keys")) | identity_keys
    min_shared = rule_int(rule, "min_shared_entries")
    min_ratio = rule_float(rule, "min_overlap_ratio")
    issues: list[ModelValidationIssue] = []
    for document in documents:
        for group in _blocks(
            document, identity_keys, set(rule_strings(rule, "container_keys"))
        ):
            entries = [set(_flatten(block, "", ignore)) for _, _, block in group]
            for later in range(1, len(group)):
                for earlier in range(later):
                    if group[earlier][0] == group[later][0]:
                        continue
                    shared = len(entries[later] & entries[earlier])
                    smaller = min(len(entries[later]), len(entries[earlier]))
                    if (
                        smaller
                        and shared >= min_shared
                        and shared / smaller >= min_ratio
                    ):
                        identity, line, _ = group[later]
                        issues.append(
                            _issue(
                                rule,
                                path,
                                f"block {identity!r} repeats {shared} of its "
                                f"{len(entries[later])} entries from block "
                                f"{group[earlier][0]!r}",
                                line,
                            )
                        )
                        break
    return sorted(issues, key=lambda issue: issue.line_number or 0)


# ---------------------------------------------------------------- family (d)


def _pin_patterns(rule: ModelValidatorRule) -> tuple[re.Pattern[str], ...]:
    org = re.escape(rule_string(rule, "github_org"))
    compiled: list[re.Pattern[str]] = []
    for text in rule_strings(rule, "patterns"):
        try:
            compiled.append(re.compile(text.replace("{org}", org), re.MULTILINE))
        except re.error as exc:
            raise _invalid(
                rule,
                f"parameters.patterns entry {text!r} is not a regular expression: {exc}",
            ) from exc
    return tuple(compiled)


def _check_first_party_pin(
    rule: ModelValidatorRule,
    path: Path,
    text: str,
    facts: ModelContractsAndDiFacts,
) -> list[ModelValidationIssue]:
    if not _matches_glob(path, rule_strings(rule, "file_globs")):
        return []
    issues: list[ModelValidationIssue] = []
    seen: set[int] = set()
    for pattern in _pin_patterns(rule):
        for match in pattern.finditer(text):
            start = match.start("ref")
            if start in seen:
                continue
            seen.add(start)
            pinned = match.group("repo").replace("-", "_")
            site = f"{pinned}>{facts.repository}:{path.as_posix()}"
            if (
                pinned
                in {name.replace("-", "_") for name in facts.tag_source_repositories}
                and site not in facts.advanced_sites
            ):
                issues.append(
                    _issue(
                        rule,
                        path,
                        f"{pinned} is pinned to the literal {match.group('ref')!r}, "
                        f"which no advancer moves although {pinned} declares a dev-merge tag source",
                        text.count("\n", 0, start) + 1,
                    )
                )
    return sorted(issues, key=lambda issue: issue.line_number or 0)


# ---------------------------------------------------------------- entry


def _unparseable(
    enabled: Sequence[ModelValidatorRule], path: Path, what: str, exc: Exception
) -> list[ModelValidationIssue]:
    """One issue per enabled ``unparseable`` row; with none enabled the file raises."""
    rows = [rule for rule in enabled if _kind(rule) == "unparseable"]
    if not rows:
        raise ModelOnexError(
            message=f"{path}: cannot parse as {what}: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    line = getattr(exc, "lineno", None)
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        line = mark.line + 1
    return [
        _issue(
            rule, path, f"the file does not parse as {what}, so no rule judged it", line
        )
        for rule in rows
    ]


def check_contracts_and_di(
    path: Path,
    text: str,
    rules: Sequence[ModelValidatorRule],
    facts: ModelContractsAndDiFacts,
) -> tuple[ModelValidationIssue, ...]:
    """Issues of one file, in rule order then line order.

    ``path`` is repository-relative, so the rows' globs match the same way in every
    clone. Raises ``ModelOnexError`` for an enabled row with an unreadable parameter.
    A file that does not parse is an issue of each enabled ``unparseable`` row, and
    raises when no such row is enabled, so it never passes unjudged.
    """
    enabled = [rule for rule in rules if rule.enabled]
    validate_rows(enabled)
    issues: list[ModelValidationIssue] = []
    tree: ast.Module | None = None
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return tuple(_unparseable(enabled, path, "Python", exc))
    block_rows = [
        rule
        for rule in enabled
        if _kind(rule) == "repeated_block"
        and _matches_glob(path, rule_strings(rule, "file_globs"))
    ]
    documents: list[yaml.Node] = []
    if block_rows:
        try:
            documents = [
                document
                for document in yaml.compose_all(text, Loader=yaml.SafeLoader)
                if document is not None
            ]
        except yaml.YAMLError as exc:
            issues.extend(_unparseable(enabled, path, "YAML", exc))
            block_rows = []
    for rule in enabled:
        kind = _kind(rule)
        if tree is not None and kind == "code_literal":
            issues.extend(_check_code_literal(rule, path, tree))
        elif tree is not None and kind == "construction":
            issues.extend(_check_construction(rule, path, tree))
        elif rule in block_rows:
            issues.extend(_check_repeated_block(rule, path, documents))
        elif kind == "first_party_pin":
            issues.extend(_check_first_party_pin(rule, path, text, facts))
    return tuple(issues)
