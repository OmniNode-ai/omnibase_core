# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure dependency provenance checker: a pyproject snapshot in, issues out (OMN-22011, T2.3).

A governed first-party package is sourced from the registry, a workspace, or the dev-merge tag
of its own repository, and from nothing else. This module judges the ``[tool.uv.sources]`` table
of one ``pyproject.toml`` against the rule rows of ``contracts/dep_provenance.validation.yaml``.
Which packages are governed, which shapes each admits, the marker that exempts one line and every
message are parameters of those rows; nothing here names a package, a repository, an organisation
or a path. No comment exempts a line. The identity of a dev-merge tag is not judged here: it needs
the remote and is the ``dev_tag_lineage`` validator. The module performs no I/O: no file read,
no clock, no environment.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path

from omnibase_core.enums.enum_dep_provenance_shape import EnumDepProvenanceShape
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.dep_provenance.model_dep_provenance_package import (
    ModelDepProvenancePackage,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_rules import (
    FOREIGN_RULE,
    INVALID_RULE,
    REPOSITORY_RULE,
    SHAPE_RULE,
    ModelDepProvenanceRules,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_vocabulary import (
    ModelDepProvenanceVocabulary,
)

__all__ = ["check_dep_provenance"]


def _unquote(text: str) -> str:
    return text.strip().strip("\"'")


def _source_lines(
    source: str, vocabulary: ModelDepProvenanceVocabulary
) -> dict[str, int]:
    """The 1-based line that declares each package: its key line or its subtable header."""
    table = ".".join(vocabulary.sources_table)
    header_pattern = re.compile(vocabulary.table_header_pattern)
    key_pattern = re.compile(vocabulary.key_pattern)
    found: dict[str, int] = {}
    inside = False
    for number, line in enumerate(source.splitlines(), start=1):
        header = header_pattern.match(line)
        if header is not None:
            name = ".".join(_unquote(part) for part in header.group(1).split("."))
            inside = name == table
            if name.startswith(table + "."):
                found.setdefault(vocabulary.normalize(name[len(table) + 1 :]), number)
            continue
        if inside and not line.lstrip().startswith("#"):
            key = key_pattern.match(line)
            if key is not None:
                head = key.group(1)
                head = head if head[0] in "\"'" else head.split(".")[0]
                found.setdefault(vocabulary.normalize(head), number)
    return found


def _sources(
    parsed: dict[str, object], vocabulary: ModelDepProvenanceVocabulary
) -> dict[str, object]:
    node: object = parsed
    for part in vocabulary.sources_table:
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _keys(attrs: dict[str, object], names: tuple[str, ...]) -> list[str]:
    return sorted(key for key in attrs if key in names)


def _issue(
    rules: ModelDepProvenanceRules,
    rule_id: str,
    template: str,
    remediation: str,
    path: Path,
    line: int | None,
    **fields: object,
) -> ModelValidationIssue | None:
    row = rules.rows[rule_id]
    if not row.enabled:
        return None
    text = template.format(line=line if line is not None else "unknown", **fields)
    return ModelValidationIssue(
        severity=row.severity,
        message=f"{text} -- {remediation}",
        code=rule_id,
        file_path=path,
        line_number=line,
        rule_name=rule_id,
    )


def _describe(attrs: dict[str, object], keys: list[str]) -> str:
    return ", ".join(f"{key}={attrs[key]!r}" for key in keys)


def check_dep_provenance(
    path: Path,
    source: str,
    rules: ModelDepProvenanceRules,
    tag_pattern: str,
) -> tuple[ModelValidationIssue, ...]:
    """One issue per source that is not an admitted shape.

    Raises ``ModelOnexError`` through ``rules`` when a rule row is unreadable, so an invalid
    contract fails to load instead of passing.
    """
    vocabulary = rules.vocabulary
    try:
        parsed = tomllib.loads(source)
    except tomllib.TOMLDecodeError as exc:
        return _present(
            [
                _issue(
                    rules,
                    INVALID_RULE,
                    rules.invalid.message,
                    rules.invalid.remediation,
                    path,
                    None,
                    detail=str(exc),
                )
            ]
        )
    packages = {row.name: row for row in vocabulary.package_rows}
    exempt = {vocabulary.normalize(name) for name in vocabulary.exempt_packages}
    lines = _source_lines(source, vocabulary)
    issues: list[ModelValidationIssue | None] = []
    for name, value in _sources(parsed, vocabulary).items():
        package = vocabulary.normalize(name)
        number = lines.get(package)
        for attrs in value if isinstance(value, list) else [value]:
            if not isinstance(attrs, dict):
                continue
            finding = _classify(
                package,
                attrs,
                packages.get(package),
                package in exempt,
                rules,
                tag_pattern,
            )
            if finding is not None:
                rule_id, template, remediation, fields = finding
                issues.append(
                    _issue(
                        rules, rule_id, template, remediation, path, number, **fields
                    )
                )
    return _present(issues)


def _present(
    issues: list[ModelValidationIssue | None],
) -> tuple[ModelValidationIssue, ...]:
    return tuple(issue for issue in issues if issue is not None)


def _classify(
    package: str,
    attrs: dict[str, object],
    row: ModelDepProvenancePackage | None,
    exempt: bool,
    rules: ModelDepProvenanceRules,
    tag_pattern: str,
) -> tuple[str, str, str, Mapping[str, object]] | None:
    """The finding a source earns before any marker is read, or None when it is admitted."""
    vocabulary = rules.vocabulary
    git = _keys(attrs, vocabulary.git_keys)
    local = _keys(attrs, vocabulary.local_keys)
    if row is None:
        if exempt or not git:
            return None
        return (
            FOREIGN_RULE,
            rules.foreign.message,
            rules.foreign.remediation,
            {"package": package, "keys": _describe(attrs, git)},
        )
    admitted = ", ".join(shape.value for shape in row.shapes)
    refused = (
        SHAPE_RULE,
        rules.shape.message,
        rules.shape.remediation,
        {
            "package": package,
            "keys": _describe(attrs, git + local),
            "admitted": admitted,
        },
    )
    if local:
        return refused
    if not git:
        shape = (
            EnumDepProvenanceShape.WORKSPACE
            if attrs.get(vocabulary.workspace_key) is True
            else EnumDepProvenanceShape.REGISTRY
        )
        return (
            None
            if shape in row.shapes
            else (
                SHAPE_RULE,
                rules.shape.message,
                rules.shape.remediation,
                {
                    "package": package,
                    "keys": _describe(attrs, sorted(attrs)) or shape.value,
                    "admitted": admitted,
                },
            )
        )
    tag = attrs.get(vocabulary.tag_key)
    url = attrs.get(vocabulary.git_key)
    if (
        set(git) != {vocabulary.git_key, vocabulary.tag_key}
        or not isinstance(tag, str)
        or not isinstance(url, str)
        or re.fullmatch(tag_pattern, tag) is None
        or EnumDepProvenanceShape.SIBLING_DEV_TAG not in row.shapes
    ):
        return refused
    own = [
        template.format(org=vocabulary.github_org, repo=row.repository)
        for template in vocabulary.repository_urls
    ]
    if url in own:
        return None
    return (
        REPOSITORY_RULE,
        rules.repository.message,
        rules.repository.remediation,
        {"package": package, "tag": tag, "git": url, "expected": own[0]},
    )
