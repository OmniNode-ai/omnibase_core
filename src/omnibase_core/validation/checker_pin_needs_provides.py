# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure pin needs/provides checker: caller text and two declarations in, issues out (OMN-21879).

Each verifier names the pin keys a caller pins it under and declares, per version, what it
needs from its environment; each caller declares what it provides. A pin of a declared
verifier is refused when its version has no needs declaration, when its caller has no
provides declaration, or when one declared need is not provided. A caller file is judged
whole; a unified diff is judged on its added lines, each under the file its header names.
Pin syntax, diff syntax and diagnostics are parameters of
``pin_needs_provides.validation.yaml``; this module holds no rule data, no repository name
and no pin value.
"""

from __future__ import annotations

import re

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.pin_needs_provides.model_pin_needs_provides_check_input import (
    ModelPinNeedsProvidesCheckInput,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_provides_check_result import (
    ModelPinNeedsProvidesCheckResult,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_provides_rules import (
    ModelPinNeedsProvidesRules,
)

__all__ = ["check_pin_needs_provides"]


def _fill(template: str, **fields: str) -> str:
    """Fill a contract template; a template naming an unknown field is a contract error."""
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError) as exc:
        raise ModelOnexError(
            message=f"rule template {template!r} cannot be filled: {exc!r}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from exc


def _judged_lines(
    request: ModelPinNeedsProvidesCheckInput, rules: ModelPinNeedsProvidesRules
) -> list[tuple[int, str, str]]:
    """Every judged line as (document line, caller, text)."""
    lines = request.text.splitlines()
    row = rules.row("need_not_provided")
    if not row.pattern("diff_source_pattern").search(request.source_name):
        return [
            (index + 1, request.source_name, line) for index, line in enumerate(lines)
        ]
    header = row.pattern("diff_file_pattern")
    prefix = row.texts["added_line_prefix"]
    caller = request.source_name
    judged: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        file_match = header.match(line)
        if file_match:
            caller = file_match["path"]
        elif line.startswith(prefix):
            judged.append((index + 1, caller, line[len(prefix) :]))
    return judged


def check_pin_needs_provides(
    request: ModelPinNeedsProvidesCheckInput,
) -> ModelPinNeedsProvidesCheckResult:
    """Judge every verifier pin of a caller file or diff against both declarations."""
    rules = ModelPinNeedsProvidesRules.from_contract(request.contract)
    patterns = [
        re.compile(pattern)
        for pattern in rules.row("need_not_provided").lists["pin_patterns"]
    ]
    found: list[ModelValidationIssue] = []
    pins = 0

    def add(code: str, line: int, need: str = "", **fields: str) -> None:
        row = rules.row(code)
        if not row.enabled or not row.judges(request.source_name):
            return
        found.append(
            ModelValidationIssue(
                severity=row.severity,
                message=_fill(row.message, need=need, **fields),
                code=code,
                rule_name=code,
                line_number=line,
                context=fields,
            )
        )

    for line, caller, text in _judged_lines(request, rules):
        seen: set[tuple[str, str]] = set()
        for pattern in patterns:
            match = pattern.match(text)
            if not match or (match["pin_key"], match["version"]) in seen:
                continue
            seen.add((match["pin_key"], match["version"]))
            verifier = request.needs.verifier_for(match["pin_key"])
            if verifier is None:
                continue
            pins += 1
            fields = {
                "caller": caller,
                "verifier": verifier.verifier_name,
                "version": match["version"],
            }
            declared = verifier.version(match["version"])
            if declared is None or declared.needs is None:
                add("needs_undeclared", line, **fields)
                continue
            entry = request.provides.caller_for(caller)
            if entry is None or entry.provides is None:
                add("provides_undeclared", line, **fields)
                continue
            for need in declared.needs:
                if need not in entry.provides:
                    add("need_not_provided", line, need=need.label(), **fields)

    return ModelPinNeedsProvidesCheckResult(
        issues=tuple(found),
        exit_code=1 if any(i.severity.is_error_or_above() for i in found) else 0,
        pins_checked=pins,
    )
