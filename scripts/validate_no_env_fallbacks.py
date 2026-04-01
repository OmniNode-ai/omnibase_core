#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Validate that no localhost/default-endpoint fallbacks exist in src/ code.

Scans Python source files (excluding tests/) for patterns that silently fall back
to localhost, 127.0.0.1, or hardcoded service URLs as default values in:
- Pydantic Field defaults
- Function/method parameter defaults
- os.getenv() fallback arguments

Exits 0 if clean, 1 if violations found.

Usage:
    uv run python scripts/validate_no_env_fallbacks.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

# Patterns that indicate a localhost/hardcoded fallback as a default value.
# We look for these in non-comment, non-docstring code lines.
FALLBACK_PATTERNS = [
    # Pydantic Field with localhost default
    re.compile(r'Field\(.*default\s*=\s*["\'].*localhost.*["\']'),
    # Function param with localhost default
    re.compile(r'def\s+\w+\(.*:\s*str\s*=\s*["\']localhost["\']'),
    # os.getenv with localhost fallback
    re.compile(r'os\.getenv\([^)]*,\s*["\'].*localhost.*["\']'),
    # Hardcoded redis:// default
    re.compile(r'url:\s*str\s*=\s*["\']redis://'),
    # Hardcoded postgresql:// default
    re.compile(r'url:\s*str\s*=\s*["\']postgresql://'),
    # Function param with redis/postgresql URL default
    re.compile(r'def\s+\w+\(.*url:\s*str\s*=\s*["\'](?:redis|postgresql)://'),
]

# Lines that are clearly docstrings/comments/examples are excluded
SKIP_PATTERNS = [
    re.compile(r'^\s*#'),          # Comments
    re.compile(r'^\s*["\']'),      # Docstring lines
    re.compile(r'^\s*>>>'),        # Doctest examples
    re.compile(r'^\s*\.\.\s'),     # RST continuation
]


def is_skippable(line: str) -> bool:
    return any(p.search(line) for p in SKIP_PATTERNS)


def scan_file(filepath: Path) -> list[tuple[int, str]]:
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    in_docstring = False
    docstring_delim = None

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # Track triple-quote docstrings
        for delim in ('"""', "'''"):
            count = stripped.count(delim)
            if in_docstring and docstring_delim == delim and count >= 1:
                in_docstring = False
                docstring_delim = None
                break
            elif not in_docstring and count == 1:
                in_docstring = True
                docstring_delim = delim
                break
            elif count >= 2:
                # Opens and closes on same line
                break

        if in_docstring:
            continue
        if is_skippable(stripped):
            continue

        for pattern in FALLBACK_PATTERNS:
            if pattern.search(line):
                violations.append((lineno, stripped))
                break

    return violations


def main() -> int:
    violations: list[tuple[str, int, str]] = []

    for py_file in sorted(SRC_DIR.rglob("*.py")):
        # Skip test files
        rel = py_file.relative_to(REPO_ROOT)
        if "test" in rel.parts:
            continue

        file_violations = scan_file(py_file)
        for lineno, line in file_violations:
            violations.append((str(rel), lineno, line))

    if violations:
        print(f"FAIL: {len(violations)} localhost/fallback violation(s) found:\n")
        for filepath, lineno, line in violations:
            print(f"  {filepath}:{lineno}: {line}")
        print(
            "\nAll service endpoints must be required fields or read from "
            "environment variables without localhost fallbacks."
        )
        return 1

    print("PASS: No localhost/fallback violations found in src/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
