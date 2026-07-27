#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Validator: no except-log-no-reraise (OMN-10817).

Rejects any except block that:
- Catches Exception or BaseException (broad catch)
- Contains a logger call (logger.warning/info/debug/error/critical/exception)
- Does NOT re-raise (no `raise` statement in the except body)

This pattern silently swallows errors — the log entry is easy to miss in
production, and the calling code proceeds as if nothing failed.

Allowlist annotation: add  # reraise-ok: <reason>  on the except line.

Exits 0 if clean, 1 if violations found (REPORT mode: always exits 0 with count).
[OMN-10817]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BROAD_EXCEPTIONS = frozenset({"Exception", "BaseException"})
LOGGER_METHODS = frozenset(
    {"warning", "info", "debug", "error", "critical", "exception"}
)
ALLOWLIST_MARKER = "# reraise-ok"
SKIP_PATH_PARTS = frozenset({"tests", "test", "__pycache__", ".git", ".venv", "venv"})


class ExceptSwallowDetector(ast.NodeVisitor):
    """AST visitor that detects broad-catch + log + no-reraise."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.violations: list[tuple[int, str]] = []

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""

    def _has_allowlist(self, lineno: int) -> bool:
        return ALLOWLIST_MARKER in self._line(lineno)

    def _catches_broad(self, handler: ast.ExceptHandler) -> bool:
        if handler.type is None:
            return True
        if isinstance(handler.type, ast.Name):
            return handler.type.id in BROAD_EXCEPTIONS
        if isinstance(handler.type, ast.Tuple):
            return any(
                isinstance(e, ast.Name) and e.id in BROAD_EXCEPTIONS
                for e in handler.type.elts
            )
        return False

    def _has_logger_call(self, body: list[ast.stmt]) -> bool:
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Call):
                func = node.func
                # logger.warning(...) style
                if isinstance(func, ast.Attribute) and func.attr in LOGGER_METHODS:
                    return True
        return False

    def _has_reraise(self, body: list[ast.stmt]) -> bool:
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Raise):
                return True
        return False

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if self._catches_broad(node) and not self._has_allowlist(node.lineno):
            if self._has_logger_call(node.body) and not self._has_reraise(node.body):
                self.violations.append((node.lineno, self._line(node.lineno).rstrip()))
        self.generic_visit(node)


def scan_python_source(path: Path) -> list[tuple[int, str]]:
    """Return violations for a single Python file, skipping test paths."""
    path_str = str(path)
    if "tests/" in path_str or "/test/" in path_str or path_str.startswith("test_"):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=str(path))
        detector = ExceptSwallowDetector(source_lines)
        detector.visit(tree)
        return detector.violations
    except SyntaxError:
        return []
    except OSError:
        return []


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PATH_PARTS for part in path.parts)


def _resolve_scan_files(scan_roots: list[Path]) -> list[Path]:
    """Return the concrete, non-skipped ``*.py`` files a default-scope scan opens.

    Single source of truth for both driving the scan and for the fail-closed
    empty-scope guard: a required gate that resolves zero files is a silent
    false-green, not a clean result. [OMN-14082]
    """
    files: list[Path] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if path.is_file() and not _should_skip(path):
                files.append(path)
    return files


def run(scan_roots: list[Path]) -> list[tuple[str, int, str]]:
    all_violations: list[tuple[str, int, str]] = []
    for path in _resolve_scan_files(scan_roots):
        for lineno, line_text in scan_python_source(path):
            all_violations.append((str(path), lineno, line_text))
    return all_violations


def run_on_files(files: list[Path]) -> list[tuple[str, int, str]]:
    all_violations: list[tuple[str, int, str]] = []
    for path in files:
        if not path.is_file() or _should_skip(path):
            continue
        for lineno, line_text in scan_python_source(path):
            all_violations.append((str(path), lineno, line_text))
    return all_violations


def main(argv: list[str] | None = None, repo_root: Path | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent

    report_mode = "--report" in args
    # Positional (non-flag) args are explicit file paths — pre-commit passes the
    # staged filenames after the flags. Flags like --report must NOT be treated
    # as file paths (the OMN-14082 false-green bug). [OMN-14082]
    file_args = [a for a in args if not a.startswith("--")]

    if file_args:
        files = [Path(f) for f in file_args]
        # FAIL-CLOSED: paths were listed but none exist as files — a broken
        # invocation (e.g. a flag leaked in as a path). Never report PASS on an
        # empty scan scope. [OMN-14082]
        if not any(f.is_file() for f in files):
            print(
                f"ERROR: {len(files)} path(s) listed but none exist as files: "
                f"{[str(f) for f in files]}. Refusing to PASS on an empty scan "
                "scope. [OMN-14082]"
            )
            return 1
        violations = run_on_files(files)
        scanned = sum(1 for f in files if f.is_file() and not _should_skip(f))
        scope_note = f"{scanned} of {len(files)} listed file(s)"
    else:
        # Default self-scan (CI `--report` with no filenames): whole src/ + scripts/.
        scan_roots = [repo_root / "src", repo_root / "scripts"]
        scanned_files = _resolve_scan_files(scan_roots)
        # FAIL-CLOSED: a required gate that resolves zero files is a silent
        # false-green, not a clean result (wrong CWD / repo layout). [OMN-14082]
        if not scanned_files:
            print(
                "ERROR: empty scan scope — resolved 0 Python files under "
                f"{[str(r) for r in scan_roots]}. A required validator that scans "
                "nothing is a false-green; check the working directory / repo "
                "layout. [OMN-14082]"
            )
            return 1
        violations = run(scan_roots)
        scope_note = f"{len(scanned_files)} file(s) under src/ + scripts/"

    if violations:
        print(
            f"FAIL: {len(violations)} except-log-no-reraise violation(s) found "
            f"(scanned {scope_note}):\n"
        )
        for filepath, lineno, line_text in violations:
            print(f"  {filepath}:{lineno}")
            print(f"    {line_text}\n")
        print(
            "Fix: add `raise` after the logger call, or annotate with  # reraise-ok: <reason>\n"
            "[OMN-10817]"
        )
        return 0 if report_mode else 1

    print(f"PASS: No except-log-no-reraise violations found (scanned {scope_note}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
