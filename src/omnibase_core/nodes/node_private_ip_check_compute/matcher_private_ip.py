# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure port of the original private-IP scanner, including occurrence order."""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

VALIDATOR_ID: Final[str] = "validator-private-ip-compute"
SUPPRESSION_MARKER: Final[str] = "onex-" + "allow-internal-ip"
_FILE_SUPPRESSION_MARKER: Final[str] = "onex-" + "allow-file-internal-ip"
_IPV4_CANDIDATE: Final[re.Pattern[str]] = re.compile(
    r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"
)


def _rfc1918_block(o1: int, o2: int, o3: int, o4: int) -> str | None:
    """Return the original block label, rejecting octets above 255."""
    if any(o > 255 for o in (o1, o2, o3, o4)):
        return None
    if o1 == 10:
        return "10/8"
    if o1 == 172 and 16 <= o2 <= 31:
        return "172.16/12"
    if o1 == 192 and o2 == 168:
        return "192.168/16"
    return None


def find_private_ip_violations(path: str, source: str) -> list[ModelValidationFinding]:
    """Preserve every match, column, line context, and both existing markers."""
    if _FILE_SUPPRESSION_MARKER in source:
        return []
    findings: list[ModelValidationFinding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if SUPPRESSION_MARKER in line:
            continue
        for match in _IPV4_CANDIDATE.finditer(line):
            block = _rfc1918_block(*(int(group) for group in match.groups()))
            if block is None:
                continue
            column = match.start() + 1
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    rule_id=block,
                    location=f"{path}:{lineno}",
                    message=f"{path}:{lineno}:{column}: [{block}] {match.group()!r}",
                    evidence={
                        "column": column,
                        "matched_text": match.group(),
                        "context": line.rstrip(),
                    },
                )
            )
    return findings
