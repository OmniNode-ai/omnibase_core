# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Require the three unfinished-work markers to reference a ticket (OMN-20068).

Ported from onex_change_control for OCC retirement step S8. The source's
line-by-line scanning heuristics and output format are preserved.

Usage::

    python -m omnibase_core.handlers.handler_todo_format [files...]

Exit code 0 = clean. Exit code 1 = violations found.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.validation.model_todo_format_finding import (
    ModelTodoFormatFinding,
)

# Any of the three unfinished-work markers without an immediate ticket reference:
# This single pattern detects bare markers even when a valid marker is also present.
MARKERS = ("TO" + "DO", "FIX" + "ME", "HA" + "CK")
INVALID_MARKER = re.compile(r"\b(?:" + "|".join(MARKERS) + r")\b(?!\(OMN-\d+\):)")

# Exemption marker: allows legacy unfinished-work notes with a stated reason.
EXEMPT = re.compile(r"#\s*" + MARKERS[0] + r"_FORMAT_EXEMPT:\s*\S")

TICKET_FORMAT = f"# {MARKERS[0]}(OMN-XXXX): description"
VIOLATION_MESSAGE = (
    f"bare {'/'.join(MARKERS)} without ticket reference -- use format: {TICKET_FORMAT}"
)

# Path segments that are excluded from scanning.
# Use bare directory names so both absolute (/tests/) and relative (tests/) paths match.
EXCLUDED_SEGMENTS: frozenset[str] = frozenset(
    {"tests", "docs", "examples", "fixtures", "vendored"}
)

# Basenames that are excluded (this script itself, for example).
EXCLUDED_BASENAMES: frozenset[str] = frozenset(
    {"check_todo_format.py", "handler_todo_format.py"}
)


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
        count = stripped.count(delim)
        if count == 1:
            in_docstring = not in_docstring
        # count >= 2 means open+close on same line; state unchanged.
    return in_docstring


def _extract_comment(line: str) -> str | None:
    """Extract the comment portion of a line (everything from ``#`` onward).

    Returns None if there is no comment outside of string literals.
    """
    in_single = False
    in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[i:]
        i += 1
    return None


def _scan_lines(text: str, path: str) -> list[ModelTodoFormatFinding]:
    """Scan *text* line-by-line and return findings."""
    violations: list[ModelTodoFormatFinding] = []
    in_docstring = False
    in_block_comment = False

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()

        # Track JS/TS/CSS block comments: /* ... */
        in_block_comment = _update_block_comment(stripped, in_block=in_block_comment)
        if in_block_comment or (stripped.startswith("*/") and not in_block_comment):
            continue

        # Track triple-quote docstrings (simple heuristic).
        in_docstring = _update_docstring(stripped, in_docstring=in_docstring)
        if in_docstring:
            continue

        # Extract comment portion only (ignore string contents).
        comment = _extract_comment(line)
        if comment is None:
            continue

        # Check the comment text for exemption (not full line, to avoid
        # false matches when the exemption token appears in string literals).
        if EXEMPT.search(comment):
            continue

        # Flag any of the three unfinished-work markers without a ticket -- catches
        # bare markers even when a valid marker is also present on the line.
        if INVALID_MARKER.search(comment):
            violations.append(
                ModelTodoFormatFinding(
                    path=path,
                    line=lineno,
                    message=VIOLATION_MESSAGE,
                )
            )

    return violations


def check_file(path: str) -> list[ModelTodoFormatFinding]:
    """Return violations for a single file."""
    basename = Path(path).name

    # Skip excluded basenames.
    if basename in EXCLUDED_BASENAMES:
        return []

    # Skip excluded path segments (works for both absolute and relative paths).
    path_parts = Path(path).parts
    if any(segment in path_parts for segment in EXCLUDED_SEGMENTS):
        return []

    # Only scan Python files.
    if not path.endswith(".py"):
        return []

    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    return _scan_lines(text, path)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    files = sys.argv[1:] if argv is None else argv
    all_violations: list[ModelTodoFormatFinding] = []
    for path in files:
        all_violations.extend(check_file(path))
    if all_violations:
        for finding in all_violations:
            sys.stdout.write(f"{finding.format()}\n")
        sys.stdout.write(
            f"\n{len(all_violations)} violation(s). Use format: {TICKET_FORMAT}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
