# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reject bare feature-flag environment reads (OMN-20074).

Ported from onex_change_control (``check-bare-feature-flags``, pinned fleet rev
8d7e85bc00e7) for OCC retirement step S8. The decisions are the source's, not
those of ``no-new-env-vars`` or ``no-new-os-environ``: an ``os.getenv``,
``os.environ.get`` or ``os.environ[`` read of an ``ENABLE_*`` or ``*_ENABLED``
name, or a ``process.env.`` read of one, on a line that does not start with a
``#`` or ``//`` comment marker, in a file that is neither one of the four
approved basenames nor under one of the four approved path segments. A line
carrying ``ONEX_FLAG_EXEMPT: <reason>`` is exempted and listed in the summary; the
marker without a reason is itself a violation.

The handler is pure over explicit ``(path, source)`` pairs; ``main`` reads the
named files through the source-file gather EFFECT. A named path that cannot be
read is skipped without a message, as in the source.

Usage::

    python -m omnibase_core.handlers.handler_no_bare_feature_flags [files...]

Exit code 0 = clean. Exit code 1 = violations found.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal

from omnibase_core.models.nodes.bare_feature_flag_check.model_bare_feature_flag_check_input import (
    ModelBareFeatureFlagCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

VALIDATOR_ID: Final[str] = "no-bare-feature-flags"

# Python getenv / environ.get / environ[] with an ENABLE_ prefix or _ENABLED suffix.
PYTHON_ENABLE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""(?:os\.getenv|os\.environ\.get|os\.environ\[)\s*\(?\s*["'](ENABLE_\w+|[A-Z_]*_ENABLED)["']"""
)

# TypeScript / JavaScript: process.env.ENABLE_* / process.env.*_ENABLED.
TS_ENABLE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""process\.env\.(ENABLE_\w+|[A-Z_]*_ENABLED)"""
)

# Exemption marker, with and without its mandatory reason.
_EXEMPT_WITH_REASON: Final[re.Pattern[str]] = re.compile(
    r"""(?:#|//)\s*ONEX_FLAG_EXEMPT:\s*(\S.*)"""
)
_EXEMPT_BARE: Final[re.Pattern[str]] = re.compile(r"""(?:#|//)\s*ONEX_FLAG_EXEMPT:""")

# Basenames of files that are allowed to read feature-flag variables.
APPROVED_BASENAMES: Final[frozenset[str]] = frozenset(
    {
        "feature_flag_resolver.py",
        "contract.yaml",
        "check_bare_feature_flags.py",
        "model_contract_feature_flag.py",
    }
)

# Path segments, each with its leading slash, under which no line is flagged.
APPROVED_PATH_SEGMENTS: Final[tuple[str, ...]] = (
    "/tests/",
    "/capabilities/",
    "/config_discovery/",
    "/contracts/",
)

_COMMENT_PREFIXES: Final[tuple[str, ...]] = ("#", "//")


def _is_approved_path(path: str) -> bool:
    if Path(path).name in APPROVED_BASENAMES:
        return True
    return any(segment in path for segment in APPROVED_PATH_SEGMENTS)


def _is_comment_line(line: str) -> bool:
    return line.lstrip().startswith(_COMMENT_PREFIXES)


def _extract_flag_name(line: str) -> str | None:
    """Return the flag name from a matching line, or None."""
    match = PYTHON_ENABLE_PATTERN.search(line)
    if match:
        return match.group(1)
    match = TS_ENABLE_PATTERN.search(line)
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


def _scan(source: str, path: str) -> list[ModelValidationFindingEmbed]:
    """Return a FAIL finding per violation and a SKIP finding per exemption, in line order."""
    findings: list[ModelValidationFindingEmbed] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if _is_comment_line(line):
            continue
        flag_name = _extract_flag_name(line)
        if flag_name is None:
            continue
        location = f"{path}:{lineno}"
        exempt_reason = _EXEMPT_WITH_REASON.search(line)
        if exempt_reason and exempt_reason.group(1).strip():
            reason = exempt_reason.group(1).strip()
            findings.append(_finding("SKIP", location, f"{location} [{reason}]"))
            continue
        if _EXEMPT_BARE.search(line):
            findings.append(
                _finding(
                    "FAIL",
                    location,
                    f"{location}: ONEX_FLAG_EXEMPT without reason token"
                    " -- add a reason after the colon",
                )
            )
            continue
        findings.append(
            _finding(
                "FAIL",
                location,
                f"{location}: bare feature flag env var"
                f' "{flag_name}"'
                " -- declare in contract.yaml feature_flags: block"
                " and resolve via flag system",
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
            if _is_approved_path(file.path):
                continue
            findings.extend(_scan(file.source, file.path))
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        return 0
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=paths,
            include_patterns=["**/*"],
            decode_errors="replace",
        )
    )
    # The source skips a path it cannot read without a message, so
    # gathered.skipped is deliberately not reported.
    report = HandlerNoBareFeatureFlags().handle(
        ModelBareFeatureFlagCheckInput(
            files=[
                ModelSourceFile(path=f.path, source=f.source) for f in gathered.files
            ]
        )
    )
    violations = [f.message for f in report.findings if f.severity == "FAIL"]
    exemptions = [f.message for f in report.findings if f.severity == "SKIP"]
    if violations:
        for violation in violations:
            sys.stdout.write(f"{violation}\n")
        exemption_summary = ""
        if exemptions:
            exemption_summary = (
                f", {len(exemptions)} exemption(s) ({', '.join(exemptions)})"
            )
        sys.stdout.write(
            f"\n{len(violations)} violation(s){exemption_summary}."
            " Declare flags in contract.yaml feature_flags: block"
            " and resolve via the flag system.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
