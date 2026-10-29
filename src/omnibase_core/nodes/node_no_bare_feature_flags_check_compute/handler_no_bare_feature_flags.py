# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reject bare feature-flag environment reads (OMN-20074).

Ported from onex_change_control (``check-bare-feature-flags``, pinned fleet rev
8d7e85bc00e7) for OCC retirement step S8. The decisions are the source's, not
those of ``no-new-env-vars`` or ``no-new-os-environ``: an ``os.getenv``,
``os.environ.get`` or ``os.environ[`` read of an ``ENABLE_*`` or ``*_ENABLED``
name, or a ``process.env.`` read of one, on a line that does not start with a
comment marker, in a file that is neither an approved basename nor under an
approved path segment. A line carrying ``ONEX_FLAG_EXEMPT: <reason>`` is exempted
and listed in the summary; the marker without a reason is itself a violation.

The handler is pure over explicit ``(path, source)`` pairs and the typed rules
(``ModelBareFeatureFlagRules``, read from ``no_bare_feature_flags.validation.yaml``);
the hook entry ``runtime_no_bare_feature_flags_check`` reads the named files through
the source-file gather EFFECT.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_check_input import (
    ModelBareFeatureFlagCheckInput,
)
from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_rules import (
    ModelBareFeatureFlagRules,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

VALIDATOR_ID: Final[str] = "no-bare-feature-flags"


@lru_cache(maxsize=16)
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def _is_approved_path(path: str, rules: ModelBareFeatureFlagRules) -> bool:
    if Path(path).name in rules.approved_basenames:
        return True
    return any(segment in path for segment in rules.approved_path_segments)


def _is_comment_line(line: str, rules: ModelBareFeatureFlagRules) -> bool:
    return line.lstrip().startswith(rules.comment_prefixes)


def _extract_flag_name(line: str, rules: ModelBareFeatureFlagRules) -> str | None:
    """Return the flag name from a matching line, or None."""
    match = _re(rules.python_pattern).search(line)
    if match:
        return match.group(1)
    match = _re(rules.ts_pattern).search(line)
    if match:
        return match.group(1)
    return None


def _finding(
    severity: Literal["FAIL", "SKIP"], location: str, message: str
) -> ModelValidationFindingEmbed:
    finding = ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity=severity,
        rule_id=VALIDATOR_ID,
        location=location,
        message=message,
    )
    return ModelValidationFindingEmbed(**finding.model_dump(mode="json"))


def _scan(
    source: str, path: str, rules: ModelBareFeatureFlagRules
) -> list[ModelValidationFindingEmbed]:
    """Return a FAIL finding per violation and a SKIP finding per exemption, in line order."""
    findings: list[ModelValidationFindingEmbed] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if _is_comment_line(line, rules):
            continue
        flag_name = _extract_flag_name(line, rules)
        if flag_name is None:
            continue
        location = f"{path}:{lineno}"
        exempt_reason = _re(rules.exempt_with_reason_pattern).search(line)
        if exempt_reason and exempt_reason.group(1).strip():
            reason = exempt_reason.group(1).strip()
            findings.append(
                _finding(
                    "SKIP",
                    location,
                    rules.exemption_template.format(location=location, reason=reason),
                )
            )
            continue
        if _re(rules.exempt_bare_pattern).search(line):
            findings.append(
                _finding(
                    "FAIL",
                    location,
                    rules.bare_exemption_template.format(location=location),
                )
            )
            continue
        findings.append(
            _finding(
                "FAIL",
                location,
                rules.violation_template.format(location=location, flag_name=flag_name),
            )
        )
    return findings


class HandlerNoBareFeatureFlags:
    """Decide, per supplied source, which lines read a bare feature-flag variable."""

    def handle(self, request: ModelBareFeatureFlagCheckInput) -> ModelValidationReport:
        """Return FAIL findings for violations and SKIP findings for exemptions.

        Findings are in file then line order; a SKIP finding's message is the
        ``path:line [reason]`` cell the summary lists.
        """
        findings: list[ModelValidationFindingEmbed] = []
        for file in request.files:
            if _is_approved_path(file.path, request.rules):
                continue
            findings.extend(_scan(file.source, file.path, request.rules))
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
