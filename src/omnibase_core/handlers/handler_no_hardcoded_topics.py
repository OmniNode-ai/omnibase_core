# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reject hardcoded ONEX topic literals outside approved constant files (OMN-20074).

Ported from onex_change_control (``check-hardcoded-topics``, pinned fleet rev
8d7e85bc00e7) for OCC retirement step S8. The decisions are the source's, not
those of ``node_hardcoded_topic_check_compute`` or ``validator_hardcoded_topics``:
a quoted ``onex.evt.`` or ``onex.cmd.`` literal on a line that is not a comment,
a docstring line or a block-comment line, in a file that is neither a test file,
an authoritative wire schema nor one of the approved basenames.

The handler is pure over explicit ``(path, source)`` pairs; ``main`` reads the
named files through the source-file gather EFFECT.

Usage::

    python -m omnibase_core.handlers.handler_no_hardcoded_topics [files...]

Exit code 0 = clean. Exit code 1 = violations found, or a named file unreadable.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
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

VALIDATOR_ID: Final[str] = "no-hardcoded-topics"

# Match quoted topic literals: "onex.evt.*" or "onex.cmd.*"
TOPIC_LITERAL: Final[re.Pattern[str]] = re.compile(r"""["']onex\.(evt|cmd)\.""")

# Basenames of files that are allowed to define topic constants.
APPROVED_BASENAMES: Final[frozenset[str]] = frozenset(
    {
        "platform_topic_suffixes.py",
        "topics.py",
        "topics.ts",
        "contract.yaml",
        "handler_contract.yaml",
        "topics.yaml",
        "contract_topic_extractor.py",
        "check_topic_drift.py",
        "topic_constants.py",
        "constants_topic_taxonomy.py",
        "topic_naming_baseline.txt",
        "governance_emitter.py",
    }
)

# Comment prefixes to skip (stripped lines starting with these).
_COMMENT_PREFIXES: Final[tuple[str, ...]] = ("#", "//", "*", "/*")
_WIRE_SCHEMA_NAME: Final[re.Pattern[str]] = re.compile(r".+_v\d+\.ya?ml")
_WIRE_SCHEMA_MIN_PARTS: Final[int] = 4
_MESSAGE: Final[str] = (
    "hardcoded topic string -- use a constant from the canonical topic registry"
)


def _is_test_file(path: str) -> bool:
    """Return True if *path* looks like a test file."""
    if "/tests/" in path:
        return True
    basename = Path(path).name
    if basename.startswith("test_"):
        return True
    return basename.endswith(("_test.py", ".test.ts", ".test.js"))


def _is_wire_schema_contract(path: str) -> bool:
    """Return True if *path* is an authoritative wire schema YAML contract."""
    parts = Path(path).as_posix().split("/")
    return (
        len(parts) >= _WIRE_SCHEMA_MIN_PARTS
        and parts[-2] == "wire_schemas"
        and _WIRE_SCHEMA_NAME.fullmatch(parts[-1]) is not None
    )


def _is_exempt_path(path: str) -> bool:
    """Return True if no line of the file at *path* is ever flagged."""
    if Path(path).name in APPROVED_BASENAMES:
        return True
    if _is_test_file(path):
        return True
    return _is_wire_schema_contract(path)


def _is_comment_line(line: str) -> bool:
    return line.lstrip().startswith(_COMMENT_PREFIXES)


def _update_block_comment(stripped: str, *, in_block: bool) -> bool:
    """Return updated ``in_block_comment`` state for a single line."""
    if in_block:
        return "*/" not in stripped
    return "/*" in stripped and (
        "*/" not in stripped or stripped.index("/*") > stripped.index("*/")
    )


def _update_docstring(stripped: str, *, in_docstring: bool) -> bool:
    """Return updated ``in_docstring`` state for a single line."""
    for delim in ('"""', "'''"):
        # One delimiter opens or closes; two on the same line leave the state unchanged.
        if stripped.count(delim) == 1:
            in_docstring = not in_docstring
    return in_docstring


def _violation_lines(text: str) -> list[int]:
    """Return the 1-based numbers of the lines that hold a flagged literal."""
    flagged: list[int] = []
    in_docstring = False
    in_block_comment = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        # JS/TS/CSS block comments: /* ... */
        in_block_comment = _update_block_comment(stripped, in_block=in_block_comment)
        if in_block_comment or stripped.startswith("*/"):
            continue
        # Triple-quote docstrings (simple heuristic).
        in_docstring = _update_docstring(stripped, in_docstring=in_docstring)
        if in_docstring or _is_comment_line(line):
            continue
        if TOPIC_LITERAL.search(line):
            flagged.append(lineno)
    return flagged


class HandlerNoHardcodedTopics:
    """Decide, per supplied source, which lines hold an unapproved topic literal."""

    def handle(self, request: ModelHardcodedTopicCheckInput) -> ModelValidationReport:
        """Return one FAIL finding per flagged line, in file then line order."""
        findings: list[ModelValidationFindingEmbed] = []
        for file in request.files:
            if _is_exempt_path(file.path):
                continue
            for lineno in _violation_lines(file.source):
                location = f"{file.path}:{lineno}"
                finding = ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    rule_id=VALIDATOR_ID,
                    location=location,
                    message=f"{location}: {_MESSAGE}",
                )
                findings.append(
                    ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                )
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
    if gathered.skipped:
        for skipped in gathered.skipped:
            sys.stdout.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
        return 1
    report = HandlerNoHardcodedTopics().handle(
        ModelHardcodedTopicCheckInput(
            files=[
                ModelSourceFile(path=f.path, source=f.source) for f in gathered.files
            ]
        )
    )
    if report.findings:
        for finding in report.findings:
            sys.stdout.write(f"{finding.message}\n")
        sys.stdout.write(
            f"\n{len(report.findings)} violation(s)."
            " Move topic strings to an approved constant file.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
