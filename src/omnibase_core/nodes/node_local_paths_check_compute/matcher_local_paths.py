# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Self-contained port of the pre-node scanner and its comment tokenization."""

from __future__ import annotations

import re
import tokenize
from io import StringIO
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

VALIDATOR_ID: Final[str] = "validator-local-paths-compute"
SUPPRESSION_MARKER: Final[str] = "local-path" + "-ok"

_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("macOS volume mount", re.compile(r"/" + r"Volumes/[A-Za-z][A-Za-z0-9_.\-]*/")),
    ("macOS user home", re.compile(r"/" + r"Users/[A-Za-z_][A-Za-z0-9_.\-]*/")),
    ("Linux user home", re.compile(r"/home/[A-Za-z_][A-Za-z0-9_.\-]*/")),
    ("Windows user path", re.compile(r"[Cc]:[/\\][Uu]sers[/\\]")),
)


def comment_carries_suppression_marker(line: str) -> bool:
    """Recognize the existing marker exclusively inside a Python comment token."""
    try:
        return any(
            token.type == tokenize.COMMENT and SUPPRESSION_MARKER in token.string
            for token in tokenize.generate_tokens(StringIO(line).readline)
        )
    except tokenize.TokenError:
        return False


def scan_source(content: str, path: str) -> list[ModelValidationFinding]:
    """Match every occurrence in stable line, column and pattern-name order."""
    matches: list[tuple[int, int, str, str, str]] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if comment_carries_suppression_marker(line):
            continue
        for pattern_name, pattern in _PATTERNS:
            for match in pattern.finditer(line):
                matches.append(
                    (
                        lineno,
                        match.start() + 1,
                        pattern_name,
                        match.group(),
                        line.rstrip(),
                    )
                )
    matches.sort(key=lambda match: match[:3])
    return [
        ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity="FAIL",
            rule_id=pattern_name,
            location=f"{path}:{line}",
            message=f"{path}:{line}:{column}: [{pattern_name}] {matched_text!r}",
            evidence={
                "column": column,
                "matched_text": matched_text,
                "context": context,
            },
        )
        for line, column, pattern_name, matched_text, context in matches
    ]
