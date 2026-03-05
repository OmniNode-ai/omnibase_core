# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CI-runnable topic name validator.

Scans Python and TypeScript source files for topic string constants
(TOPIC_* and SUFFIX_*) and validates each against the canonical ONEX
format: onex.<kind>.<producer>.<event-name>.v<version>

Usage:
    onex-validate-topics /path/to/repo
    onex-validate-topics /path/to/repo --verbose

Exit Codes:
    0 - All topic constants are valid
    1 - One or more violations found

Related ticket: OMN-3740
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

from omnibase_core.validation.scripts.model_topic_extraction import TopicExtraction
from omnibase_core.validation.scripts.model_validation_report import ValidationReport
from omnibase_core.validation.validator_topic_suffix import validate_topic_suffix

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Patterns for finding topic constant assignments in Python files
# Matches: TOPIC_FOO = "..." or SUFFIX_FOO = "..."
PY_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^[ \t]*(?:TOPIC_|SUFFIX_)\w+\s*[:=]\s*["\']([^"\']+)["\']""",
    re.MULTILINE,
)

# Patterns for finding topic constant assignments in TypeScript files
# Matches: export const TOPIC_FOO = "..." or export const SUFFIX_FOO = "..."
TS_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^[ \t]*export\s+const\s+(?:TOPIC_|SUFFIX_)\w+\s*=\s*["\']([^"\']+)["\']""",
    re.MULTILINE,
)

# Glob patterns for discovering source files
PY_GLOBS: Final[list[str]] = ["**/*topic*.py", "**/*topics*.py"]
TS_GLOBS: Final[list[str]] = ["**/*topic*.ts", "**/*topics*.ts"]

# Flat legacy topic pattern (no dots at all, e.g. "agent-actions")
FLAT_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9-]*$")

# Environment-prefixed topic pattern (e.g. "{env}.onex.evt...")
ENV_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\{env\}\.",
)


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------


def scan_file(file_path: Path) -> list[TopicExtraction]:
    """Extract topic constant values from a single source file.

    Scans for TOPIC_* and SUFFIX_* constant assignments in both Python
    and TypeScript files.

    Args:
        file_path: Path to the source file to scan.

    Returns:
        List of extracted topic strings with their locations.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Select the right pattern based on file extension
    suffix = file_path.suffix.lower()
    if suffix == ".ts":
        pattern = TS_TOPIC_PATTERN
    elif suffix == ".py":
        pattern = PY_TOPIC_PATTERN
    else:
        return []

    extractions: list[TopicExtraction] = []
    for match in pattern.finditer(content):
        # Calculate line number from match position
        line_number = content[: match.start()].count("\n") + 1
        extractions.append(
            TopicExtraction(
                file_path=file_path,
                line_number=line_number,
                constant_value=match.group(1),
            )
        )

    return extractions


def discover_files(root: Path) -> list[Path]:
    """Discover Python and TypeScript files that may contain topic constants.

    Args:
        root: Root directory to search.

    Returns:
        Sorted list of file paths matching topic-related glob patterns.
    """
    files: set[Path] = set()
    all_globs = PY_GLOBS + TS_GLOBS
    for glob_pattern in all_globs:
        files.update(root.glob(glob_pattern))
    return sorted(files)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_topic(value: str) -> str | None:
    """Validate a single topic string against ONEX naming rules.

    Checks for:
    1. {env}. prefix (template variable prefix)
    2. Flat legacy names (no dots, e.g. "agent-actions")
    3. Canonical ONEX format via validate_topic_suffix()

    Args:
        value: The topic string to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    # Check for {env}. prefix
    if ENV_PREFIX_PATTERN.match(value):
        return f"topic uses {{env}}. prefix (legacy pattern): {value}"

    # Check for flat legacy topics (no dots at all)
    if FLAT_TOPIC_PATTERN.match(value):
        return f"flat legacy topic name (must use onex.<kind>.<producer>.<event>.v<n>): {value}"

    # Validate against canonical ONEX format
    result = validate_topic_suffix(value)
    if not result.is_valid:
        return f"{result.error}: {value}"

    return None


def validate_repo(root: Path, *, verbose: bool = False) -> ValidationReport:
    """Scan a repository and validate all topic constants.

    Args:
        root: Root directory of the repository to scan.
        verbose: If True, print progress information.

    Returns:
        ValidationReport with results.
    """
    report = ValidationReport()
    files = discover_files(root)
    report.scanned_files = len(files)

    for file_path in files:
        extractions = scan_file(file_path)
        for extraction in extractions:
            report.total_topics += 1
            error = validate_topic(extraction.constant_value)
            if error is not None:
                relative = _relative_path(file_path, root)
                report.violations.append(
                    f"{relative}:{extraction.line_number}: {error}"
                )

    if verbose:
        print(
            f"Scanned {report.scanned_files} files, "
            f"found {report.total_topics} topic constants"
        )

    return report


def _relative_path(path: Path, root: Path) -> str:
    """Return path relative to root, or absolute if not under root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for onex-validate-topics."""
    if len(sys.argv) < 2:
        print("Usage: onex-validate-topics <repo-root> [--verbose]", file=sys.stderr)
        sys.exit(2)

    root = Path(sys.argv[1]).resolve()
    verbose = "--verbose" in sys.argv

    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)

    report = validate_repo(root, verbose=verbose)

    if report.is_clean:
        print(
            f"OK: {report.total_topics} topic(s) validated across {report.scanned_files} file(s)"
        )
        sys.exit(0)
    else:
        print(f"FAIL: {len(report.violations)} violation(s) found:\n")
        for violation in report.violations:
            print(f"  {violation}")
        sys.exit(1)


if __name__ == "__main__":
    main()
