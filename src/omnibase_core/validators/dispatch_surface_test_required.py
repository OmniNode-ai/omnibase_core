# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dispatch-surface real-dispatch-test gate (OMN-12960).

Path-heuristic ratchet: a PR (or commit) that touches a **dispatch surface** —
message dispatch, handler routing, handler registration / auto-wiring, or the
transport-envelope unwrap predicate — MUST also touch at least one
**real-dispatch-path test**. Handler-isolation unit tests pass while the live
dispatch path fails (the OMN-12940 / OMN-12946 / OMN-12960 defect class); the
only durable guard is a test that drives the real dispatcher registration.

Why a path heuristic
--------------------
The live failures in the 2026-06-11 full-feature pass all shared the same shape:
the change was covered by a handler-isolation test that constructed the handler
directly and called ``handle()`` with a hand-built domain payload, so it never
exercised the materialized transport envelope the runtime actually delivers.
The fix (``repro_real_dispatch.py`` promoted to a reusable fixture) only helps
if PRs that change dispatch behaviour are *required* to use it. This validator
enforces that requirement mechanically.

Definitions
-----------
A changed file is a **dispatch surface** when its path matches any
``_DISPATCH_SURFACE_PATTERNS`` substring (e.g. ``message_dispatch_engine``,
``auto_wiring/``, ``handler_wiring``, ``handler_routing``, ``util_envelope_unwrap``,
``evidence_pipeline_native``) and it lives under a ``src/`` tree.

A changed file is a **real-dispatch-path test** when it is a test file
(``test_*.py`` / ``*_test.py`` under a ``tests/`` tree) whose contents reference
the reusable real-dispatch fixture or drive the real dispatcher directly
(``real_dispatch`` / ``drive_real_dispatch`` / ``MessageDispatchEngine`` /
``_make_dispatch_callback`` / ``_materialize_envelope_with_bindings``).

Exit codes
----------
``0`` — no dispatch surface touched, or a real-dispatch-path test is present.
``1`` — a dispatch surface was touched with no accompanying real-dispatch test.

Suppression
-----------
Add ``# dispatch-surface-test-ok: <reason>`` anywhere in any staged file to
acknowledge a genuinely test-irrelevant dispatch-surface change (e.g. a comment
or docstring-only edit). The reason is recorded in the failure output.

Usage::

    # Pre-commit (staged-file args)
    python -m omnibase_core.validators.dispatch_surface_test_required FILE [FILE ...]

    # CI (diff against a base ref)
    python -m omnibase_core.validators.dispatch_surface_test_required --base origin/dev
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

__all__ = [
    "DISPATCH_SURFACE_PATTERNS",
    "REAL_DISPATCH_TEST_MARKERS",
    "SUPPRESSION_TOKEN",
    "is_dispatch_surface",
    "is_real_dispatch_test",
    "main",
]

# Path substrings that identify a dispatch / routing / handler-registration /
# message-envelope source surface. Matched against the POSIX path.
DISPATCH_SURFACE_PATTERNS: tuple[str, ...] = (
    "message_dispatch_engine",
    "auto_wiring/",
    "handler_wiring",
    "handler_routing",
    "dispatch_engine",
    "util_envelope_unwrap",
    "evidence_pipeline_native",
)

# Content markers that prove a test drives the real dispatch path rather than
# constructing a handler in isolation.
REAL_DISPATCH_TEST_MARKERS: tuple[str, ...] = (
    "real_dispatch",
    "drive_real_dispatch",
    "MessageDispatchEngine",
    "_make_dispatch_callback",
    "_materialize_envelope_with_bindings",
)

SUPPRESSION_TOKEN = "# dispatch-surface-test-ok:"


def _is_source(path: str) -> bool:
    return "/src/" in path or path.startswith("src/")


def _is_test_file(path: str) -> bool:
    name = Path(path).name
    is_test_named = name.startswith("test_") or name.endswith("_test.py")
    in_tests_tree = "/tests/" in path or path.startswith("tests/")
    return path.endswith(".py") and is_test_named and in_tests_tree


def is_dispatch_surface(path: str) -> bool:
    """True when ``path`` is a dispatch-surface SOURCE file (not a test)."""
    posix = path.replace("\\", "/")
    if not posix.endswith(".py") or not _is_source(posix):
        return False
    if _is_test_file(posix):
        return False
    return any(pattern in posix for pattern in DISPATCH_SURFACE_PATTERNS)


def is_real_dispatch_test(path: str, text: str) -> bool:
    """True when ``path`` is a test file that drives the real dispatch path."""
    if not _is_test_file(path.replace("\\", "/")):
        return False
    return any(marker in text for marker in REAL_DISPATCH_TEST_MARKERS)


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _suppression_reason(paths: Iterable[str]) -> str | None:
    for path in paths:
        text = _read(path)
        for line in text.splitlines():
            if SUPPRESSION_TOKEN in line:
                return line.split(SUPPRESSION_TOKEN, 1)[1].strip()
    return None


def _git_changed_files(base: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(2)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _evaluate(paths: Sequence[str]) -> int:
    surfaces = [p for p in paths if is_dispatch_surface(p)]
    if not surfaces:
        return 0

    has_real_dispatch_test = any(
        is_real_dispatch_test(p, _read(p)) for p in paths if _is_test_file(p)
    )
    if has_real_dispatch_test:
        return 0

    reason = _suppression_reason(paths)
    if reason is not None:
        sys.stderr.write(
            "dispatch-surface-test-required: SUPPRESSED via "
            f"'{SUPPRESSION_TOKEN} {reason}'\n"
        )
        return 0

    sys.stderr.write(
        "dispatch-surface-test-required: FAIL\n"
        "  A dispatch / routing / handler-registration / message-envelope "
        "surface was changed without an accompanying real-dispatch-path test.\n"
        "  Changed dispatch surfaces:\n"
    )
    for surface in surfaces:
        sys.stderr.write(f"    - {surface}\n")
    sys.stderr.write(
        "  Add a test that drives the real dispatcher (use the reusable "
        "real-dispatch fixture / MessageDispatchEngine materialized envelope). "
        "Handler-isolation tests are not sufficient — they pass while live "
        "dispatch fails (OMN-12940 / OMN-12946 / OMN-12960).\n"
        f"  Test markers that satisfy this gate: {', '.join(REAL_DISPATCH_TEST_MARKERS)}\n"
        f"  Genuinely test-irrelevant change? Add '{SUPPRESSION_TOKEN} <reason>'.\n"
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dispatch-surface-test-required",
        description=(
            "Require a real-dispatch-path test for PRs touching dispatch, "
            "routing, handler-registration, or message-envelope surfaces."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit changed-file paths (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff HEAD against (CI mode). Mutually exclusive "
        "with positional file args.",
    )
    args = parser.parse_args(argv)

    if args.base is not None:
        paths = _git_changed_files(args.base)
    else:
        paths = list(args.files)

    return _evaluate(paths)


if __name__ == "__main__":
    raise SystemExit(main())
