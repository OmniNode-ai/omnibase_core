# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Line-based matcher that detects localhost/hardcoded-endpoint fallback defaults.

Split out of ``handler.py`` (single-class-per-file convention established by
``node_no_utcnow_check_compute``, OMN-14656) — this module has no classes at
all since the port is a per-line regex match with lightweight docstring
tracking, not an AST walk.

Port of the Python-file and shell-file scanners
(``omniclaude/scripts/validate_no_env_fallbacks.py:41-186``). Six pattern
types: ``os.environ.get``/``os.getenv`` with a localhost/private-IP default,
Pydantic/keyword ``default=``/``: str =`` localhost or private-IP literals,
``bootstrap_servers=`` localhost/private-IP literals, and ``${VAR:-...}``
shell-parameter-expansion fallbacks — each exempt on a line carrying one of
``EXEMPT_MARKERS`` or on a pure-comment / docstring line.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = [
    "VALIDATOR_ID",
    "should_skip_path",
    "find_env_fallback_violations",
]

VALIDATOR_ID: Final[str] = "arch-no-env-fallbacks"
_REMEDIATION: Final[str] = (
    'replace with os.environ["VAR"] (fail-fast, no default) or raise explicitly; '
    "annotate a justified exception with # fallback-ok: <reason>"
)

# ---------------------------------------------------------------------------
# Pattern building blocks (oracle _LOCALHOST_VARIANTS / _PRIV_IP)
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
# Python patterns (oracle PYTHON_FALLBACK_PATTERNS)
# ---------------------------------------------------------------------------
_PYTHON_FALLBACK_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        rf"""os\.environ\.get\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""
    ),
    re.compile(
        rf"""os\.getenv\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""
    ),
    re.compile(rf"""default\s*=\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""),
    re.compile(rf""":\s*str\s*=\s*["'][^"']*{_LOCALHOST_VARIANTS}[^"']*["']"""),
    re.compile(
        rf"""os\.(?:environ\.get|getenv)\(\s*["'][^"']*["']\s*,\s*["'][^"']*{_PRIV_IP}[^"']*["']"""
    ),
    re.compile(rf"""(?:default\s*=|:\s*str\s*=)\s*["'][^"']*{_PRIV_IP}[^"']*["']"""),
    re.compile(
        rf"""bootstrap_servers\s*=\s*["'](?:{_LOCALHOST_VARIANTS}|{_PRIV_IP})[^"']*["']"""
    ),
]

# ---------------------------------------------------------------------------
# Shell patterns (oracle SHELL_FALLBACK_PATTERNS)
# ---------------------------------------------------------------------------
_SHELL_FALLBACK_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        rf"""\$\{{[A-Za-z_][A-Za-z0-9_]*:-[^}}]*{_LOCALHOST_VARIANTS}[^}}]*\}}"""
    ),
    re.compile(rf"""\$\{{[A-Za-z_][A-Za-z0-9_]*:-[^}}]*{_PRIV_IP}[^}}]*\}}"""),
]

# ---------------------------------------------------------------------------
# Skip / exempt configuration (oracle SKIP_DIRS / EXEMPT_MARKERS)
# ---------------------------------------------------------------------------
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {"tests", "node_tests", "__tests__", "test", "__pycache__", ".git", ".venv", "venv"}
)

_EXEMPT_MARKERS: Final[tuple[str, ...]] = (
    "# fallback-ok",
    "# cloud-bus-ok",
    "# OMN-7227-exempt",
)

_COMMENT_RE: Final[re.Pattern[str]] = re.compile(r"^\s*#")
_TRIPLE_QUOTE_DELIMS: Final[tuple[str, str]] = ('"""', "'''")


def should_skip_path(path: str) -> bool:
    """Return True if any path component is a skip directory (oracle ``_should_skip``,
    dir-membership half only — the SKIP_FILES self-exclusion does not apply generically)."""
    parts = PurePosixPath(path.replace("\\", "/")).parts
    return any(part in _SKIP_DIRS for part in parts)


def _is_pure_comment(line: str) -> bool:
    return bool(_COMMENT_RE.match(line))


def _has_exempt_marker(line: str) -> bool:
    return any(marker in line for marker in _EXEMPT_MARKERS)


def _has_executable_suffix_after_closing_delim(line: str, delim: str) -> bool:
    close_index = line.find(delim, len(delim))
    if close_index == -1:
        return False
    suffix = line[close_index + len(delim) :].strip()
    return bool(suffix and not suffix.startswith("#"))


def _scan_python_lines(path: str, source: str) -> list[ModelValidationFinding]:
    """Port of ``scan_python_file`` (validate_no_env_fallbacks.py:121-166)."""
    findings: list[ModelValidationFinding] = []
    in_docstring = False
    docstring_delim: str | None = None

    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        skip_line = False

        for delim in _TRIPLE_QUOTE_DELIMS:
            count = stripped.count(delim)
            if in_docstring and docstring_delim == delim:
                if count >= 1:
                    in_docstring = False
                    docstring_delim = None
                    skip_line = True
                break
            if not in_docstring and stripped.startswith(delim):
                if count == 1:
                    in_docstring = True
                    docstring_delim = delim
                elif not _has_executable_suffix_after_closing_delim(stripped, delim):
                    skip_line = True
                break

        if in_docstring or skip_line:
            continue
        if _is_pure_comment(line):
            continue
        if _has_exempt_marker(line):
            continue

        for pattern in _PYTHON_FALLBACK_PATTERNS:
            if pattern.search(line):
                findings.append(_make_finding(path, lineno, line.rstrip()))
                break

    return findings


def _scan_shell_lines(path: str, source: str) -> list[ModelValidationFinding]:
    """Port of ``scan_shell_file`` (validate_no_env_fallbacks.py:169-185)."""
    findings: list[ModelValidationFinding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _is_pure_comment(line):
            continue
        if _has_exempt_marker(line):
            continue
        for pattern in _SHELL_FALLBACK_PATTERNS:
            if pattern.search(line):
                findings.append(_make_finding(path, lineno, line.rstrip()))
                break
    return findings


def _make_finding(path: str, lineno: int, line_text: str) -> ModelValidationFinding:
    return ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity="FAIL",
        location=f"{path}:{lineno}",
        message=f"{path}:{lineno}: {line_text.strip()}",
        remediation=_REMEDIATION,
    )


def find_env_fallback_violations(
    path: str, source: str
) -> list[ModelValidationFinding]:
    """Dispatch a (path, source) pair to the Python or shell scanner by suffix.

    Any other suffix is not scanned (oracle only handles ``.py``/``.sh``/``.bash``).
    """
    if should_skip_path(path):
        return []

    suffix = PurePosixPath(path.replace("\\", "/")).suffix
    if suffix == ".py":
        return _scan_python_lines(path, source)
    if suffix in (".sh", ".bash"):
        return _scan_shell_lines(path, source)
    return []
