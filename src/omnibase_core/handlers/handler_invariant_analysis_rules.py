# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure registry, lifecycle and document rules for invariant analysis (OMN-21565)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.invariant_analysis.model_invariant_analysis_input import (
    ModelInvariantAnalysisInput,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_overlay import (
    ModelInvariantAnalysisOverlay,
)
from omnibase_core.models.invariant_analysis.model_invariant_analysis_rules import (
    ModelInvariantAnalysisRules,
)
from omnibase_core.models.invariant_analysis.model_invariant_entry import (
    ModelInvariantEntry,
)
from omnibase_core.models.invariant_analysis.model_invariant_registry import (
    ModelInvariantRegistry,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)

__all__ = [
    "analyse_document",
    "build_registry",
    "is_exempt_by_lifecycle",
    "matches_globs",
    "parse_overlay",
]


def _error(detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=detail, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{field}: expected nonempty text")
    return value.strip()


def _sequence(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _error(f"{field}: expected nonempty list")
    result = tuple(_text(item, field) for item in value)
    if len(set(result)) != len(result):
        raise _error(f"{field}: duplicate values")
    return result


def build_registry(
    raw: Mapping[str, object], rules: ModelInvariantAnalysisRules
) -> ModelInvariantRegistry:
    """Build a registry or reject a defect before any documents are judged."""
    row = rules.row("registry_invalid")
    if not isinstance(raw, Mapping):
        raise _error("Registry must be a mapping")
    scopes = _sequence(raw.get("scopes"), "scopes")
    entries = raw.get("invariants")
    if not isinstance(entries, list) or not entries:
        raise _error("invariants: expected nonempty list")
    invariants: list[ModelInvariantEntry] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise _error("Registry entry must be a mapping")
        for field in row.lists["required_fields"]:
            if field not in entry:
                raise _error(f"Missing required field: {field}")
        inv_id = _text(entry.get("id"), "id")
        if not row.pattern("id_pattern").fullmatch(inv_id) or inv_id in seen:
            raise _error(f"Invalid or duplicate id: {inv_id}")
        seen.add(inv_id)
        statement = _text(entry.get("statement"), "statement")
        _text(entry.get("enforcement"), "enforcement")
        scope = _sequence(entry.get("scope"), "scope")
        if set(scope) - set(scopes):
            raise _error(f"{inv_id}: unknown scope")
        ruled = entry.get("ruled")
        if not isinstance(ruled, Mapping):
            raise _error(f"{inv_id}: ruled must be a mapping")
        for field in row.lists["required_ruled_fields"]:
            _text(ruled.get(field), field)
        status = _text(entry.get("status"), "status")
        if status not in row.lists["valid_statuses"]:
            raise _error(f"{inv_id}: invalid status {status}")
        replacement = entry.get("superseded_by")
        if status == row.texts["superseded_status"]:
            replacement = _text(replacement, "superseded_by")
        elif replacement is not None:
            raise _error(f"{inv_id}: replacement on non-superseded entry")
        invariants.append(
            ModelInvariantEntry(
                id=inv_id,
                statement=" ".join(statement.split()),
                scope=scope,
                status=status,
                superseded_by=replacement,
            )
        )
    for invariant in invariants:
        if invariant.superseded_by is not None and invariant.superseded_by not in seen:
            raise _error(
                f"{invariant.id}: unknown replacement {invariant.superseded_by}"
            )
    return ModelInvariantRegistry(
        scopes=scopes,
        invariants=tuple(invariants),
        active_status=row.texts["active_status"],
    )


def parse_overlay(raw: Mapping[str, object]) -> ModelInvariantAnalysisOverlay:
    """Validate all required repository settings and the task capture expression."""
    try:
        overlay = ModelInvariantAnalysisOverlay.model_validate(raw)
        pattern = re.compile(overlay.task_heading_pattern)
        if pattern.groups < 1:
            raise _error("Task heading expression must capture an identifier")
        return overlay
    except (ValidationError, re.error) as exc:
        raise _error(f"Invalid overlay: {exc}") from exc


def is_exempt_by_lifecycle(
    path: str,
    lifecycle: Mapping[str, object],
    overlay: ModelInvariantAnalysisOverlay,
    rules: ModelInvariantAnalysisRules,
) -> bool:
    """Look up a document's lifecycle in the supplied projection."""
    row = rules.row("registry_invalid")
    entries = lifecycle.get(row.texts["lifecycle_entries_key"])
    if not isinstance(entries, list):
        return False
    return any(
        isinstance(entry, Mapping)
        and entry.get(row.texts["lifecycle_path_key"]) == path
        and entry.get(row.texts["lifecycle_status_key"])
        in overlay.exempt_lifecycle_statuses
        for entry in entries
    )


def matches_globs(path: str, globs: tuple[str, ...]) -> bool:
    """Match root-relative globs, including recursive directory components."""

    def match(parts: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
        if not pattern:
            return not parts
        if pattern[0] == "**":
            return match(parts, pattern[1:]) or bool(
                parts and match(parts[1:], pattern)
            )
        return bool(
            parts
            and fnmatchcase(parts[0], pattern[0])
            and match(parts[1:], pattern[1:])
        )

    return any(
        match(PurePosixPath(path).parts, PurePosixPath(pattern).parts)
        for pattern in globs
    )


def analyse_document(
    request: ModelInvariantAnalysisInput, rules: ModelInvariantAnalysisRules
) -> tuple[ModelValidationFindingEmbed, ...]:
    """Evaluate supplied facts; disabled rows suppress only their own findings."""
    findings: list[ModelValidationFindingEmbed] = []

    def add(rule_id: str, detail: str) -> None:
        row = rules.row(rule_id)
        if row.enabled:
            findings.append(
                ModelValidationFindingEmbed(
                    validator_id=request.contract.validator_id,
                    severity="ERROR" if row.severity.is_error_or_above() else "WARN",
                    location=request.path,
                    rule_id=rule_id,
                    message=row.texts["message"].format(detail=detail),
                    remediation=row.texts["remediation"],
                )
            )

    registry = request.registry
    if registry is None:
        if request.registry_error is None:
            raise _error("Absent registry requires an error")
        add("registry_invalid", request.registry_error)
        return tuple(findings)

    authority = rules.row("authority_doc_coverage")
    lines: list[str | None] = []
    fenced = False
    for source_line in request.text.splitlines():
        if authority.pattern("fence_pattern").match(source_line):
            fenced = not fenced
            lines.append(None)
        else:
            lines.append(None if fenced else source_line)
    by_id = registry.by_id()
    declared_raw: str | None = None
    for line in lines[: authority.integers["header_scan_lines"]]:
        match = (
            authority.pattern("marker_pattern").match(line.strip())
            if line is not None
            else None
        )
        if match:
            declared_raw = match.group(1)
            break
    starts = [
        i
        for i, line in enumerate(lines)
        if line is not None and authority.texts["coverage_start"] in line
    ]
    ends = [
        i
        for i, line in enumerate(lines)
        if line is not None and authority.texts["coverage_end"] in line
    ]
    if declared_raw is None:
        if starts or ends:
            add("authority_doc_coverage", request.path)
    else:
        scopes = frozenset(
            tag
            for tag in authority.pattern("scope_split_pattern").split(
                declared_raw.strip()
            )
            if tag
        )
        balanced = len(starts) == len(ends) == 1 and starts[0] < ends[0]
        if not scopes or scopes - set(registry.scopes) or not balanced:
            add("authority_doc_coverage", request.path)
        else:
            covered = {
                match.group(0)
                for line in lines[starts[0] + 1 : ends[0]]
                if line is not None
                for match in authority.pattern("id_pattern").finditer(line)
            }
            invalid = covered - set(by_id)
            invalid.update(
                inv_id
                for inv_id in covered
                if inv_id in by_id and by_id[inv_id].status != registry.active_status
            )
            missing = {inv.id for inv in registry.active_for_scopes(scopes)} - covered
            if invalid or missing:
                add("authority_doc_coverage", ", ".join(sorted(invalid | missing)))

    if not matches_globs(request.path, request.overlay.plan_globs):
        return tuple(findings)
    section_rule = rules.row("analysis_section_missing")
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line is not None and section_rule.pattern("heading_pattern").search(line)
        ),
        None,
    )
    if start is None:
        add("analysis_section_missing", request.path)
        return tuple(findings)
    section: list[str] = []
    for line in lines[start + 1 :]:
        if line is None:
            continue
        if section_rule.pattern("section_end_pattern").search(line):
            break
        section.append(line)
    scope_rule = rules.row("scope_declaration_missing_or_unknown")
    scope_matches = [
        match
        for line in section
        if (match := scope_rule.pattern("scopes_pattern").search(line))
    ]
    declared = frozenset(
        tag
        for match in scope_matches
        for tag in scope_rule.pattern("scope_split_pattern").split(
            match.group(1).strip()
        )
        if tag
    )
    if (
        not scope_matches
        or not declared
        or declared - set(registry.scopes)
        or set(request.overlay.always_scopes) - declared
    ):
        add("scope_declaration_missing_or_unknown", ", ".join(sorted(declared)))
    required = registry.active_for_scopes(
        declared | frozenset(request.overlay.always_scopes)
    )
    satisfied = rules.row("satisfied_by_task_absent")
    reasoned = rules.row("not_applicable_unreasoned")
    entry_rule = rules.row("invariant_unknown_or_retired")
    addressed: set[str] = set()
    tasks = {
        match.group(1)
        for line in lines
        if line is not None
        and (match := re.search(request.overlay.task_heading_pattern, line))
    }
    for line in section:
        entry = entry_rule.pattern("entry_pattern").search(line)
        if entry and (
            entry.group(1) not in by_id
            or by_id[entry.group(1)].status != registry.active_status
        ):
            add("invariant_unknown_or_retired", entry.group(1))
        match = satisfied.pattern("entry_pattern").search(line)
        if match:
            addressed.add(match.group(1))
            for task in satisfied.pattern("task_split_pattern").split(match.group(2)):
                if task.strip() not in tasks:
                    add("satisfied_by_task_absent", task.strip())
        match = reasoned.pattern("entry_pattern").search(line)
        if match:
            addressed.add(match.group(1))
            reason = match.group(2).strip()
            normalized = reasoned.pattern("trim_pattern").sub("", reason).casefold()
            denied = {
                reasoned.pattern("trim_pattern").sub("", item.strip()).casefold()
                for item in request.overlay.denied_placeholders
            }
            if len(reason) < request.overlay.min_reason_length or normalized in denied:
                add("not_applicable_unreasoned", match.group(1))
    for invariant in required:
        if invariant.id not in addressed:
            add("invariant_unaddressed", invariant.id)
    return tuple(findings)
