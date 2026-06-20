# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Bypass-token blocklist enforcement (OMN-13388).

Enforces the 9-token bypass blocklist across every emitted artifact, backend and
UI contract edits alike.  Rule: no generated or human-authored artifact may
contain any of the 9 blocked tokens except on a line that carries the explicit
suppression annotation.

Blocked tokens (canonical source — also tested in tests/validators/
test_bypass_token_blocklist.py):
  1. [skip-receipt-gate:    — receipt-gate bypass (OMN-10414)
  2. --no-verify             — pre-commit bypass
  3. --no-gpg-sign           — commit-signing bypass
  4. [skip ci]               — CI skip (GitHub convention)
  5. [ci skip]               — CI skip (Travis/Jenkins convention)
  6. [skip-dod-sweep:        — DoD sweep bypass
  7. [skip-cr-gate:          — CodeRabbit gate bypass
  8. [deploy-gate-bypass:    — deploy-gate bypass
  9. receipt-gate-bypass     — receipt-gate bypass (bare variant)

``emergency_bypass.enabled`` is always false by contract schema; it is NOT in
this list because the schema layer enforces it — adding it here would create
duplicated enforcement and inflate the count.

Escape hatch (explicit user approval only):
  Add ``# bypass-token-ok: <receipt-id>`` on the SAME LINE as the token.
  The receipt-id must be a traceable approval handle, not free text.

Scanned file extensions: ``.md``, ``.yaml``, ``.yml``, ``.txt``
Skipped extensions: ``.py``, ``.sh``, and all others (discussion of bypass
tokens in source/docs that *describe* the rule must not be self-blocking).

Usage::

    # Pre-commit (staged files as positional args)
    python -m omnibase_core.validators.bypass_token_blocklist FILE [FILE ...]

    # CI / repo-wide grep (no args → scans src/ contracts/ docs/)
    python -m omnibase_core.validators.bypass_token_blocklist --scan-tree ROOT
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.validation.model_bypass_token_finding import (
    ModelBypassTokenFinding,
)

__all__ = [
    "BYPASS_TOKENS",
    "SUPPRESSION_TOKEN",
    "find_tokens_in_file",
    "find_tokens_in_text",
    "main",
    "scan_tree",
]

# ---------------------------------------------------------------------------
# Canonical 9-token blocklist (OMN-13388 §Task 13)
# ---------------------------------------------------------------------------

BYPASS_TOKENS: tuple[str, ...] = (
    "[skip-receipt-gate:",
    "--no-verify",
    "--no-gpg-sign",
    "[skip ci]",
    "[ci skip]",
    "[skip-dod-sweep:",
    "[skip-cr-gate:",
    "[deploy-gate-bypass:",
    "receipt-gate-bypass",
)

# Suppression annotation — must appear on the SAME LINE as the bypass token.
# Format: # bypass-token-ok: <receipt-id>
SUPPRESSION_TOKEN: str = "# bypass-token-ok:"  # secret-ok: annotation marker, not a credential  # env-var-ok: constant definition

# File extensions to scan (text-artifact types; source files are excluded to
# prevent self-blocking discussion of the blocklist).
_SCANNED_EXTENSIONS: frozenset[str] = frozenset((".md", ".yaml", ".yml", ".txt"))

# Default scan roots when invoked in tree-scan mode with no explicit args.
_DEFAULT_SCAN_DIRS: tuple[str, ...] = ("src", "contracts", "docs")


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------


def find_tokens_in_text(
    text: str,
    path: Path,
) -> list[ModelBypassTokenFinding]:
    """Return all bypass-token findings in ``text``, attributed to ``path``."""
    findings: list[ModelBypassTokenFinding] = []
    for line_index, raw_line in enumerate(text.splitlines(), start=1):
        line_lower = raw_line.lower()
        for token in BYPASS_TOKENS:
            if token.lower() not in line_lower:
                continue
            # Check for same-line suppression annotation (case-insensitive)
            if SUPPRESSION_TOKEN.lower() in line_lower:
                continue
            findings.append(
                ModelBypassTokenFinding(
                    path=path,
                    line_number=line_index,
                    token=token,
                    line_text=raw_line,
                )
            )
    return findings


def find_tokens_in_file(path: Path) -> list[ModelBypassTokenFinding]:
    """Scan a single file for bypass tokens.  Returns empty list for skipped types."""
    if path.suffix not in _SCANNED_EXTENSIONS:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return find_tokens_in_text(text, path)


def scan_tree(root: Path) -> list[ModelBypassTokenFinding]:
    """Recursively scan all scanned-extension files under ``root``."""
    findings: list[ModelBypassTokenFinding] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        if "__pycache__" in candidate.parts:
            continue
        findings.extend(find_tokens_in_file(candidate))
    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bypass-token-blocklist",
        description=(
            "Enforce the 9-token bypass blocklist on text artifacts "
            "(.md/.yaml/.yml/.txt).  "
            "Fails (exit 1) if any blocked token is found without an "
            "explicit same-line suppression annotation."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Explicit file paths to scan (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--scan-tree",
        metavar="ROOT",
        type=Path,
        action="append",
        default=None,
        help=(
            "Recursively scan all scanned-extension files under ROOT "
            "(used in CI repo-wide grep mode). Repeatable."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    findings: list[ModelBypassTokenFinding] = []

    if args.scan_tree is not None:
        for root in args.scan_tree:
            findings.extend(scan_tree(root))
    elif args.files:
        for path in args.files:
            findings.extend(find_tokens_in_file(path))
    else:
        # No args: scan default directories relative to cwd
        cwd = Path.cwd()
        for dir_name in _DEFAULT_SCAN_DIRS:
            candidate = cwd / dir_name
            if candidate.is_dir():
                findings.extend(scan_tree(candidate))

    if not findings:
        return 0

    sys.stderr.write("bypass-token-blocklist: FAIL — blocked tokens found:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nThe 9 bypass tokens must never appear in artifacts (OMN-13388).\n"
        "Fix the underlying gate issue instead of using a bypass token.\n"
        f"If a true exception is required, add '{SUPPRESSION_TOKEN} <receipt-id>' "
        "on the SAME LINE as the token, where <receipt-id> is a traceable "
        "user-approval handle.\n"
    )
    return 1


if __name__ == "__main__":
    _exit_code = main()
    raise SystemExit(_exit_code)  # error-ok: CLI entry point
