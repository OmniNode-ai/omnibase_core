#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical unified validator: no localhost/hardcoded-endpoint fallbacks.

Covers all 6 pattern types from OMN-10658 enforcement sweep:
  1. os.environ.get("X", "localhost...")
  2. os.getenv("X", "localhost...")
  3. default="localhost..." (Pydantic Field or function param)
  4. ${VAR:-localhost} (shell scripts)
  5. Hardcoded 192.168.* IPs as default values
  6. 127.0.0.1 bind addresses as default values

Exits 0 if clean, 1 if violations found.

Annotation: add  # fallback-ok: <reason>  to a line to exempt it.
[OMN-10741]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pattern building blocks
# ---------------------------------------------------------------------------
_LOCALHOST_VARIANTS = (
    r"(?:localhost|127\.0\.0\.1"
    r"|http://localhost|https://localhost"
    r"|bolt://localhost|redis://localhost"
    r"|postgresql://localhost|amqp://localhost"
    r"|http://127\.0\.0\.1|redis://127\.0\.0\.1|postgresql://127\.0\.0\.1)"
)
_PRIV_IP = r"192\.168\.\d{1,3}\.\d{1,3}"

# ---------------------------------------------------------------------------
# Python patterns
# ---------------------------------------------------------------------------
PYTHON_FALLBACK_PATTERNS: list[re.Pattern[str]] = [
    # os.environ.get("VAR", "localhost...")
    re.compile(
        rf"""os\.environ\.get\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""
    ),
    # os.getenv("VAR", "localhost...")
    re.compile(
        rf"""os\.getenv\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""
    ),
    # default="localhost..." (Pydantic Field or keyword argument)
    re.compile(rf"""default\s*=\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""),
    # ": str = "localhost..." style parameter defaults
    re.compile(rf""":\s*str\s*=\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""),
    # os.environ.get / os.getenv with private-IP default
    re.compile(
        rf"""os\.(?:environ\.get|getenv)\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_PRIV_IP}[^"']*["']"""
    ),
    # default="192.168...." or ": str = "192.168...." style
    re.compile(rf"""(?:default\s*=|:\s*str\s*=)\s*["'][^"']*{_PRIV_IP}[^"']*["']"""),
    # bootstrap_servers="localhost:..." or private-IP
    re.compile(
        rf"""bootstrap_servers\s*=\s*["'](?:{_LOCALHOST_VARIANTS}|{_PRIV_IP})[^"']*["']"""
    ),
]

# ---------------------------------------------------------------------------
# Shell patterns
# ---------------------------------------------------------------------------
SHELL_FALLBACK_PATTERNS: list[re.Pattern[str]] = [
    # ${VAR:-localhost} or ${VAR:-http://localhost:8080}
    re.compile(
        rf"""\$\{{[A-Za-z_][A-Za-z0-9_]*:-[^}}]*{_LOCALHOST_VARIANTS}[^}}]*\}}"""
    ),
    re.compile(rf"""\$\{{[A-Za-z_][A-Za-z0-9_]*:-[^}}]*{_PRIV_IP}[^}}]*\}}"""),
]

# ---------------------------------------------------------------------------
# Skip / exempt configuration
# ---------------------------------------------------------------------------
SKIP_DIRS: frozenset[str] = frozenset(
    {"tests", "node_tests", "__tests__", "test", "__pycache__", ".git", ".venv", "venv"}
)

SKIP_FILES: frozenset[str] = frozenset(
    {
        "validate_no_env_fallbacks.py",  # this script — patterns appear as strings
    }
)

EXEMPT_MARKERS: tuple[str, ...] = (
    "# fallback-ok",
    "# cloud-bus-ok",
    "# OMN-7227-exempt",
)

_COMMENT_RE = re.compile(r"^\s*#")


def _is_pure_comment(line: str) -> bool:
    return bool(_COMMENT_RE.match(line))


def _has_exempt_marker(line: str) -> bool:
    return any(marker in line for marker in EXEMPT_MARKERS)


# ---------------------------------------------------------------------------
# File scanners
# ---------------------------------------------------------------------------


def scan_python_file(path: Path) -> list[tuple[int, str]]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    violations: list[tuple[int, str]] = []
    in_docstring = False
    docstring_delim: str | None = None

    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # Track triple-quoted docstrings
        for delim in ('"""', "'''"):
            count = stripped.count(delim)
            if in_docstring and docstring_delim == delim:
                if count >= 1:
                    in_docstring = False
                    docstring_delim = None
                break
            if not in_docstring and count == 1:
                in_docstring = True
                docstring_delim = delim
                break
            if count >= 2:
                # Opens and closes on the same line — skip as a docstring line
                break

        if in_docstring:
            continue
        if _is_pure_comment(line):
            continue
        if _has_exempt_marker(line):
            continue

        for pattern in PYTHON_FALLBACK_PATTERNS:
            if pattern.search(line):
                violations.append((lineno, line.rstrip()))
                break

    return violations


def scan_shell_file(path: Path) -> list[tuple[int, str]]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _is_pure_comment(line):
            continue
        if _has_exempt_marker(line):
            continue
        for pattern in SHELL_FALLBACK_PATTERNS:
            if pattern.search(line):
                violations.append((lineno, line.rstrip()))
                break
    return violations


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _should_skip(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.name in SKIP_FILES:
        return True
    return False


def run(scan_roots: list[Path], repo_root: Path) -> list[tuple[str, int, str]]:
    all_violations: list[tuple[str, int, str]] = []
    for base in scan_roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if _should_skip(path, repo_root):
                continue
            rel = str(path.relative_to(repo_root))
            if path.suffix == ".py":
                file_viols = scan_python_file(path)
            elif path.suffix in (".sh", ".bash"):
                file_viols = scan_shell_file(path)
            else:
                continue
            for lineno, line_text in file_viols:
                all_violations.append((rel, lineno, line_text))
    return all_violations


def run_on_files(files: list[Path], repo_root: Path) -> list[tuple[str, int, str]]:
    """Scan a specific list of files (pre-commit pass_filenames mode)."""
    all_violations: list[tuple[str, int, str]] = []
    for path in files:
        path = path if path.is_absolute() else repo_root / path
        if not path.is_file():
            continue
        if _should_skip(path, repo_root):
            continue
        rel = str(path.relative_to(repo_root))
        if path.suffix == ".py":
            file_viols = scan_python_file(path)
        elif path.suffix in (".sh", ".bash"):
            file_viols = scan_shell_file(path)
        else:
            continue
        for lineno, line_text in file_viols:
            all_violations.append((rel, lineno, line_text))
    return all_violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    if len(sys.argv) > 1:
        # pre-commit pass_filenames mode: scan only the files passed as args
        files = [Path(f) for f in sys.argv[1:]]
        violations = run_on_files(files, repo_root)
    else:
        # standalone mode: scan all of src/ and scripts/
        scan_roots = [repo_root / "src", repo_root / "scripts"]
        violations = run(scan_roots, repo_root)

    if violations:
        print(
            f"FAIL: {len(violations)} localhost/hardcoded-endpoint fallback(s) found:\n"
        )
        for filepath, lineno, line_text in violations:
            print(f"  {filepath}:{lineno}")
            print(f"    {line_text}\n")
        print(
            'Fix: Replace with os.environ["VAR"] (fail-fast, no default) or raise explicitly.\n'
            "Annotate justified exceptions with  # fallback-ok: <reason>  on the same line.\n"
            "[OMN-10741]"
        )
        return 1

    print("PASS: No localhost/hardcoded-endpoint fallbacks found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
