#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Validator: no ImportError-assigned-to-None fallback (OMN-10819).

Rejects any `except ImportError` (or ModuleNotFoundError) block that assigns
a symbol to None:

    try:
        from foo import Bar
    except ImportError:
        Bar = None   # <-- REJECTED

This pattern causes AttributeError or TypeError at call-site instead of at
import time, making failures invisible until runtime under specific code paths.

Allowlist annotation: add  # import-fallback-ok: <reason>  on the assignment line.

Exits 0 if clean, 1 if violations found (REPORT mode: always exits 0 with count).
[OMN-10819]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

IMPORT_ERRORS = frozenset({"ImportError", "ModuleNotFoundError"})
ALLOWLIST_MARKER = "# import-fallback-ok"
SKIP_PATH_PARTS = frozenset({"tests", "test", "__pycache__", ".git", ".venv", "venv"})


class ImportNoneFallbackDetector(ast.NodeVisitor):
    """AST visitor that detects ImportError blocks assigning symbols to None."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.violations: list[tuple[int, str]] = []

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""

    def _has_allowlist(self, lineno: int) -> bool:
        return ALLOWLIST_MARKER in self._line(lineno)

    def _catches_import_error(self, handler: ast.ExceptHandler) -> bool:
        if handler.type is None:
            return False
        if isinstance(handler.type, ast.Name):
            return handler.type.id in IMPORT_ERRORS
        if isinstance(handler.type, ast.Tuple):
            return any(
                isinstance(e, ast.Name) and e.id in IMPORT_ERRORS
                for e in handler.type.elts
            )
        return False

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if not self._catches_import_error(node):
            self.generic_visit(node)
            return
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if (
                            isinstance(stmt.value, ast.Constant)
                            and stmt.value.value is None
                            and not self._has_allowlist(stmt.lineno)
                        ):
                            self.violations.append(
                                (stmt.lineno, self._line(stmt.lineno).rstrip())
                            )
        self.generic_visit(node)


def scan_python_source(path: Path) -> list[tuple[int, str]]:
    path_str = str(path)
    if "tests/" in path_str or "/test/" in path_str or path_str.startswith("test_"):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=str(path))
        detector = ImportNoneFallbackDetector(source_lines)
        detector.visit(tree)
        return detector.violations
    except SyntaxError:
        return []
    except OSError:
        return []


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PATH_PARTS for part in path.parts)


def run(scan_roots: list[Path]) -> list[tuple[str, int, str]]:
    all_violations: list[tuple[str, int, str]] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if not path.is_file() or _should_skip(path):
                continue
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


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent

    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if not f.startswith("--")]
        violations = run_on_files(files)
    else:
        scan_roots = [repo_root / "src", repo_root / "scripts"]
        violations = run(scan_roots)

    report_mode = "--report" in sys.argv

    if violations:
        print(
            f"FAIL: {len(violations)} ImportError-assigned-to-None fallback(s) found:\n"
        )
        for filepath, lineno, line_text in violations:
            print(f"  {filepath}:{lineno}")
            print(f"    {line_text}\n")
        print(
            "Fix: Replace `Symbol = None` with `raise ImportError(...)` or a real fallback.\n"
            "Annotate justified exceptions with  # import-fallback-ok: <reason>\n"
            "[OMN-10819]"
        )
        return 0 if report_mode else 1

    print("PASS: No ImportError-assigned-to-None fallbacks found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
