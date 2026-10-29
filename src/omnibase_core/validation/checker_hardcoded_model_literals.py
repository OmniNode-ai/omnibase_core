# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for K6 families O, G, F, P, S, H and B (OMN-21537).

Facts in (one file's path and text, a rule set), ``ModelValidationIssue`` out: no file
read, no clock, no environment. Every name, pattern, threshold and remediation text is a
``parameters`` entry of a rule row of ``contracts/hardcoded_model_literals.validation.yaml``;
a missing or mistyped entry raises while the rule set loads, so a broken contract fails
instead of passing every file. The three facts a repository supplies (the first-party
organisation, the registry repository names, the lab host names) are arguments of
``load_rule_set``.

* ``O``: an operational number bound to a name the row's patterns match, or passed to a call
  the row names.
* ``G``: a first-party repository URL (host plus the organisation fact), f-strings included.
* ``F``: a filesystem location in code.
* ``P``: a literal list of registry repository names.
* ``S``: a ruling stamp bound as a value.
* ``H``: a literal list of lab host names.
* ``B``: a numeric budget, cap, window or bound assigned to a module-level constant.

Python is judged on its syntax tree, so a comment is not there and a docstring is prose.
Other text forms are judged line by line with comments removed.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.validation.model_hardcoded_literal_rule_row import (
    ModelHardcodedLiteralRuleRow,
)
from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.validation.checker_hardcoded_model_views import (
    file_suffix,
    glob_regex,
    strip_comment,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

if TYPE_CHECKING:
    from omnibase_core.validation.hardcoded_model_config.models import LiteralFamily

Hit = tuple[int, "LiteralFamily", str]

_FAMILY_KEY = "family"
_REMEDIATION_KEY = "remediation"


def _row(rule: ModelValidatorRule) -> ModelHardcodedLiteralRuleRow:
    return ModelHardcodedLiteralRuleRow(
        family=rule_string(rule, _FAMILY_KEY),
        rule_name=rule.rule_id,
        severity=rule.severity,
        remediation=rule_string(rule, _REMEDIATION_KEY),
    )


def load_rule_set(
    rules: Sequence[ModelValidatorRule],
    *,
    github_org: str,
    repository_names: Iterable[str],
    host_names: Iterable[str],
    python_suffixes: Iterable[str],
    slash_comment_suffixes: Iterable[str],
    no_comment_suffixes: Iterable[str],
    exclude_patterns: Iterable[str] = (),
) -> ModelHardcodedLiteralRuleSet:
    """Read the rule rows into a rule set; raise when any row is missing or mistyped.

    ``rules`` are the contract's rows, the disabled ones included, so a broken row fails
    even while its family is off. Only enabled rows judge.
    """
    by_family = {rule_string(rule, _FAMILY_KEY): rule for rule in rules}
    wanted = {"O", "G", "F", "P", "S", "H", "B"}
    missing = wanted - by_family.keys()
    if missing:
        raise ModelOnexError(
            message=f"contract has no rule row for families {sorted(missing)}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    o, g, f, p, s, h, b = (by_family[k] for k in ("O", "G", "F", "P", "S", "H", "B"))
    for pattern in (
        *rule_strings(o, "name_patterns"),
        *rule_strings(o, "text_patterns"),
        *rule_strings(f, "parameter_name_patterns"),
        *rule_strings(f, "constant_name_patterns"),
        *rule_strings(b, "name_patterns"),
        rule_string(f, "dot_directory_pattern"),
        rule_string(g, "placeholder_pattern"),
        *rule_strings(g, "scheme_patterns"),
        rule_string(s, "stamp_pattern"),
        rule_string(s, "text_pattern"),
        rule_string(b, "text_pattern"),
    ):
        re.compile(pattern)
    return ModelHardcodedLiteralRuleSet(
        rows=tuple(_row(rule) for rule in rules if rule.enabled),
        o_name_patterns=rule_strings(o, "name_patterns"),
        o_call_names=rule_strings(o, "call_names"),
        o_min_value=rule_int(o, "min_value"),
        o_text_patterns=rule_strings(o, "text_patterns"),
        g_hosts=rule_strings(g, "hosts"),
        g_scheme_patterns=rule_strings(g, "scheme_patterns"),
        g_placeholder_pattern=rule_string(g, "placeholder_pattern"),
        g_org=github_org,
        f_home_calls=rule_strings(f, "home_calls"),
        f_parameter_name_patterns=rule_strings(f, "parameter_name_patterns"),
        f_dot_directory_pattern=rule_string(f, "dot_directory_pattern"),
        f_constant_name_patterns=rule_strings(f, "constant_name_patterns"),
        f_anchor_names=rule_strings(f, "anchor_names"),
        f_path_constructors=rule_strings(f, "path_constructors"),
        p_names=(*rule_strings(p, "extra_names"), *repository_names),
        p_min_members=rule_int(p, "min_members"),
        s_stamp_pattern=rule_string(s, "stamp_pattern"),
        s_text_pattern=rule_string(s, "text_pattern"),
        h_host_names=tuple(host_names),
        h_min_members=rule_int(h, "min_members"),
        b_name_patterns=rule_strings(b, "name_patterns"),
        b_min_value=rule_int(b, "min_value"),
        b_text_pattern=rule_string(b, "text_pattern"),
        python_suffixes=tuple(python_suffixes),
        slash_comment_suffixes=tuple(slash_comment_suffixes),
        no_comment_suffixes=tuple(no_comment_suffixes),
        exclude_patterns=tuple(exclude_patterns),
    )


def _any_match(patterns: Iterable[str], name: str) -> bool:
    return any(re.search(pattern, name) for pattern in patterns)


def _number(node: ast.AST | None) -> float | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value
    return None


def _string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return f"{head}.{node.attr}" if head else node.attr
    if isinstance(node, ast.Call):
        return _dotted(node.func)
    return ""


def _target_names(node: ast.Assign | ast.AnnAssign) -> Iterator[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    for target in targets:
        if isinstance(target, ast.Name):
            yield target.id
        elif isinstance(target, ast.Attribute):
            yield target.attr


def _docstring_ids(tree: ast.AST) -> frozenset[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and _string(first.value) is not None:
                ids.add(id(first.value))
    return frozenset(ids)


def _joined(node: ast.JoinedStr) -> str:
    """An f-string as text with each interpolation written as ``{}``."""
    return "".join(
        part.value
        if isinstance(part, ast.Constant) and isinstance(part.value, str)
        else "{}"
        for part in node.values
    )


def _members(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return [s for elt in node.elts if (s := _string(elt)) is not None]
    return []


def _path_literal(node: ast.AST, rules: ModelHardcodedLiteralRuleSet) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in rules.f_anchor_names:
            return True
        if (
            isinstance(child, ast.Call)
            and _dotted(child.func) in rules.f_path_constructors
            and any(_string(arg) is not None for arg in child.args)
        ):
            return True
    text = _string(node)
    return text is not None and "/" in text


def _url_pattern(
    rules: ModelHardcodedLiteralRuleSet, *, org_only: bool
) -> re.Pattern[str] | None:
    if not rules.g_org or not rules.g_hosts or not rules.g_scheme_patterns:
        return None
    schemes = "|".join(rules.g_scheme_patterns)
    hosts = "|".join(re.escape(h) for h in rules.g_hosts)
    org = re.escape(rules.g_org) + r"(?![\w\-])"
    tail = org if org_only else f"(?:{org}|{rules.g_placeholder_pattern})"
    return re.compile(f"(?:{schemes})(?:{hosts})[/:]{tail}")


def _python_hits(
    tree: ast.Module, rules: ModelHardcodedLiteralRuleSet
) -> Iterator[Hit]:
    families = rules.families()
    docs = _docstring_ids(tree)
    plain_url = _url_pattern(rules, org_only=True)
    fstring_url = _url_pattern(rules, org_only=False)
    stamp = re.compile(rules.s_stamp_pattern)
    dot_dir = re.compile(rules.f_dot_directory_pattern)
    hosts = {h.lower() for h in rules.h_host_names}
    repos = set(rules.p_names)
    module_level = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Assign | ast.AnnAssign):
            value = node.value
            for name in _target_names(node):
                number = _number(value)
                if (
                    "O" in families
                    and number is not None
                    and number >= rules.o_min_value
                    and _any_match(rules.o_name_patterns, name)
                ):
                    yield line, "O", f"{name} = {number}"
                if (
                    "B" in families
                    and id(node) in module_level
                    and number is not None
                    and number >= rules.b_min_value
                    and _any_match(rules.b_name_patterns, name)
                ):
                    yield line, "B", f"{name} = {number}"
                text = _string(value)
                if (
                    "F" in families
                    and text is not None
                    and dot_dir.search(text)
                    and _any_match(rules.f_parameter_name_patterns, name)
                ):
                    yield line, "F", f"{name} = {text!r}"
                if (
                    "F" in families
                    and id(node) in module_level
                    and value is not None
                    and _any_match(rules.f_constant_name_patterns, name)
                    and _path_literal(value, rules)
                ):
                    yield line, "F", name
        elif isinstance(node, ast.Call):
            callee = _dotted(node.func)
            if "O" in families:
                for kw in node.keywords:
                    number = _number(kw.value)
                    if (
                        kw.arg
                        and number is not None
                        and number >= rules.o_min_value
                        and _any_match(rules.o_name_patterns, kw.arg)
                    ):
                        yield kw.value.lineno, "O", f"{kw.arg}={number}"
                last = callee.rsplit(".", 1)[-1]
                first = _number(node.args[0]) if node.args else None
                if (
                    last in rules.o_call_names
                    and first is not None
                    and first >= rules.o_min_value
                ):
                    yield line, "O", f"{last}({first})"
            if "F" in families and any(
                callee == call or callee.endswith("." + call)
                for call in rules.f_home_calls
            ):
                yield line, "F", callee
        elif isinstance(node, ast.arguments):
            positional = [*node.posonlyargs, *node.args]
            defaults = node.defaults
            pairs = list(
                zip(
                    positional[len(positional) - len(defaults) :], defaults, strict=True
                )
            )
            pairs += [
                (arg, default)
                for arg, default in zip(node.kwonlyargs, node.kw_defaults, strict=True)
                if default is not None
            ]
            for arg, default in pairs:
                number = _number(default)
                text = _string(default)
                if (
                    "O" in families
                    and number is not None
                    and number >= rules.o_min_value
                    and _any_match(rules.o_name_patterns, arg.arg)
                ):
                    yield default.lineno, "O", f"{arg.arg}={number}"
                if (
                    "F" in families
                    and text is not None
                    and dot_dir.search(text)
                    and _any_match(rules.f_parameter_name_patterns, arg.arg)
                ):
                    yield default.lineno, "F", f"{arg.arg}={text!r}"
        if isinstance(node, ast.JoinedStr):
            rendered = _joined(node)
            if "G" in families and fstring_url is not None:
                hit = fstring_url.search(rendered)
                if hit:
                    yield line, "G", hit.group(0)
            if "S" in families and (hit_s := stamp.search(rendered)):
                yield line, "S", hit_s.group(0)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docs:
                continue
            if "G" in families and plain_url is not None:
                hit = plain_url.search(node.value)
                if hit:
                    yield node.lineno, "G", hit.group(0)
            if "S" in families and (hit_s := stamp.search(node.value)):
                yield node.lineno, "S", hit_s.group(0)
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            names = _members(node)
            if "H" in families and sum(n.lower() in hosts for n in names) >= max(
                rules.h_min_members, 1
            ):
                yield line, "H", ",".join(names)
            if "P" in families and sum(n in repos for n in names) >= max(
                rules.p_min_members, 1
            ):
                yield line, "P", ",".join(names)


def _flow_members(line: str) -> Iterator[list[str]]:
    for match in re.finditer(r"\[([^\[\]]*)\]", line):
        yield [m.strip().strip("'\"") for m in match.group(1).split(",") if m.strip()]


def _text_hits(
    path: str, text: str, rules: ModelHardcodedLiteralRuleSet
) -> Iterator[Hit]:
    families = rules.families()
    url = _url_pattern(rules, org_only=False)
    hosts = {h.lower() for h in rules.h_host_names}
    repos = set(rules.p_names)
    for n, raw in enumerate(text.splitlines(), start=1):
        line = strip_comment(
            path, raw, rules.slash_comment_suffixes, rules.no_comment_suffixes
        )
        if not line.strip():
            continue
        if "O" in families:
            for pattern in rules.o_text_patterns:
                if hit := re.search(pattern, line):
                    yield n, "O", hit.group(0)
                    break
        if "G" in families and url is not None and (hit := url.search(line)):
            yield n, "G", hit.group(0)
        if "S" in families and (hit := re.search(rules.s_text_pattern, line)):
            yield n, "S", hit.group(0)
        if "B" in families and (hit := re.search(rules.b_text_pattern, line)):
            yield n, "B", hit.group(0)
        for names in _flow_members(line):
            if "H" in families and sum(m.lower() in hosts for m in names) >= max(
                rules.h_min_members, 1
            ):
                yield n, "H", ",".join(names)
            if "P" in families and sum(m in repos for m in names) >= max(
                rules.p_min_members, 1
            ):
                yield n, "P", ",".join(names)


def scan_literals(
    path: str, text: str, rules: ModelHardcodedLiteralRuleSet
) -> list[Hit]:
    """Every ``(line, family, matched text)`` hit of the enabled families, in line order.

    One hit per family per line, because the baseline is keyed by line content.
    """
    posix = path.replace("\\", "/").removeprefix("./")
    if not rules.families() or any(
        glob_regex(glob).match(posix) for glob in rules.exclude_patterns
    ):
        return []
    hits: Iterable[Hit]
    if file_suffix(path) in rules.python_suffixes:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            hits = _text_hits(path, text, rules)
        else:
            hits = _python_hits(tree, rules)
    else:
        hits = _text_hits(path, text, rules)
    seen: dict[tuple[int, LiteralFamily], Hit] = {}
    for hit in hits:
        seen.setdefault((hit[0], hit[1]), hit)
    return [seen[key] for key in sorted(seen)]


def check_text(
    path: str, text: str, rules: ModelHardcodedLiteralRuleSet
) -> tuple[ModelValidationIssue, ...]:
    """Facts in, issues out: one issue per hit, carrying its rule row's id and remediation."""
    rows: Mapping[str, ModelHardcodedLiteralRuleRow] = {
        row.family: row for row in rules.rows
    }
    return tuple(
        ModelValidationIssue(
            severity=rows[family].severity,
            message=f"{rows[family].rule_name}: {matched}",
            code=rows[family].rule_name,
            file_path=Path(path),
            line_number=line,
            rule_name=rows[family].rule_name,
            suggestion=rows[family].remediation,
            context={"family": family, "matched": matched},
        )
        for line, family, matched in scan_literals(path, text, rules)
    )


__all__ = ["Hit", "check_text", "load_rule_set", "scan_literals"]
