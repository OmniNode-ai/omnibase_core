# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure line scanner preserving the original hardcoded-topic acceptance rule."""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

VALIDATOR_ID: Final[str] = "validator-hardcoded-topic-compute"
RULE_ID: Final[str] = "hardcoded-topic-literal"

_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(['\"])" + r"onex\." + r"[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+(?:\.[a-z0-9]+)*\1"
)
_LINE_MARKER: Final[str] = "onex" + "-allow-topic-literal"
_FILE_MARKER: Final[str] = "onex" + "-allow-file-topic-literal"


def scan_source(content: str, path: str = "<input>") -> list[ModelValidationFinding]:
    """Return findings in line and match order, including duplicate literals."""
    if _FILE_MARKER in content:
        return []

    findings: list[ModelValidationFinding] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _LINE_MARKER in line:
            continue
        for match in _TOPIC_PATTERN.finditer(line):
            topic = match.group(0)[1:-1]
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    rule_id=RULE_ID,
                    location=f"{path}:{lineno}",
                    message=f"{path}:{lineno}: [{topic}] {line.strip()}",
                    evidence={"topic": topic, "context": line.strip()},
                )
            )
    return findings
