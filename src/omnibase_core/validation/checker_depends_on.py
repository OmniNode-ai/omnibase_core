# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure depends-on checker: a document and the world's facts in, issues out (OMN-24537).

A document declares what it depends on under the dotted key paths the contract names,
searched in order; the facts say, per kind, what exists in the world. A malformed
declaration, a declaration of an unknown kind, a known kind with no facts supplied and
a declared token the facts do not hold are each refused, never skipped. The declaration
key paths, the kinds, the field separator and the diagnostics are parameters of
``depends_on.validation.yaml``; this module holds no rule data, no repository name and
no dependency name.
"""

from __future__ import annotations

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_duplicate_yaml_mapping_key import (
    DuplicateYamlMappingKeyError,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.depends_on.model_depends_on_check_input import (
    ModelDependsOnCheckInput,
)
from omnibase_core.models.depends_on.model_depends_on_check_result import (
    ModelDependsOnCheckResult,
)
from omnibase_core.models.depends_on.model_depends_on_entry import ModelDependsOnEntry
from omnibase_core.models.depends_on.model_depends_on_rules import ModelDependsOnRules
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["check_depends_on"]


def _fill(template: str, **fields: str) -> str:
    """Fill a contract template; a template naming an unknown field is a contract error."""
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError) as exc:
        raise ModelOnexError(
            message=f"rule template {template!r} cannot be filled: {exc!r}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from exc


def _document(request: ModelDependsOnCheckInput) -> dict[object, object] | None:
    """The document as a mapping; a text that is not a YAML mapping declares nothing.

    A duplicate mapping key still raises: it must not silently collapse into a
    document that declares nothing.
    """
    try:
        return load_yaml_mapping_no_duplicates(request.text, source=request.source_name)
    except DuplicateYamlMappingKeyError:
        raise
    except ValueError:
        return None


def _declared(document: dict[object, object], path: str) -> object | None:
    """The value at a dotted key path; an absent path or a non-mapping intermediate is None."""
    node: object = document
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _entry(raw: object) -> ModelDependsOnEntry | None:
    """A declared entry, or None when it is not a mapping of a non-empty kind and name."""
    if not isinstance(raw, dict):
        return None
    try:
        return ModelDependsOnEntry.model_validate(raw)
    except ValidationError:
        return None


def _rendered(raw: object) -> str:
    """A malformed declaration as diagnostic text."""
    return raw if isinstance(raw, str) else str(raw)


def _line_of(lines: list[str], needle: str) -> int:
    """The first line holding the needle, else the first line."""
    return next((index + 1 for index, line in enumerate(lines) if needle in line), 1)


def check_depends_on(
    request: ModelDependsOnCheckInput,
) -> ModelDependsOnCheckResult:
    """Judge every dependency a document declares against the world the facts describe."""
    rules = ModelDependsOnRules.from_contract(request.contract)
    separator = rules.row("dependency_absent").texts["field_separator"]
    kinds = rules.row("dependency_kind_unknown").lists["kinds"]
    lines = request.text.splitlines()
    found: list[ModelValidationIssue] = []
    checked = 0

    def add(code: str, needle: str, **fields: str) -> None:
        row = rules.row(code)
        if not row.enabled or not row.judges(request.source_name):
            return
        found.append(
            ModelValidationIssue(
                severity=row.severity,
                message=_fill(row.message, **fields),
                code=code,
                rule_name=code,
                line_number=_line_of(lines, needle),
                context=fields,
            )
        )

    document = _document(request)
    if document is None:
        return ModelDependsOnCheckResult(
            issues=(),
            exit_code=0,
            dependencies_checked=0,
        )
    for path in rules.row("dependency_absent").lists["declaration_keys"]:
        declared = _declared(document, path)
        if declared is None:
            continue
        if not isinstance(declared, list):
            rendered = _rendered(declared)
            add(
                "dependency_malformed",
                rendered,
                source=request.source_name,
                entry=rendered,
            )
            continue
        for raw in declared:
            entry = _entry(raw)
            if entry is None:
                rendered = _rendered(raw)
                add(
                    "dependency_malformed",
                    rendered,
                    source=request.source_name,
                    entry=rendered,
                )
                continue
            if entry.kind not in kinds:
                add(
                    "dependency_kind_unknown",
                    entry.name,
                    source=request.source_name,
                    kind=entry.kind,
                    kinds=", ".join(kinds),
                )
                continue
            checked += 1
            if request.facts is None or not request.facts.has_kind(entry.kind):
                add(
                    "facts_unsupplied",
                    entry.name,
                    source=request.source_name,
                    kind=entry.kind,
                    label=entry.label(separator),
                )
            elif not request.facts.holds(entry.kind, entry.token(separator)):
                add(
                    "dependency_absent",
                    entry.name,
                    source=request.source_name,
                    label=entry.label(separator),
                )

    return ModelDependsOnCheckResult(
        issues=tuple(found),
        exit_code=1 if any(i.severity.is_error_or_above() for i in found) else 0,
        dependencies_checked=checked,
    )
