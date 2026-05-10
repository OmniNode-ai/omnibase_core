#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Validator: no event-bus none-guard before publish (OMN-10818).

Rejects any pattern where:
- `if self._event_bus is not None:` / `if self.event_bus is not None:`
  / `if event_bus is not None:` / `if event_bus:`
- Is followed by a publish/emit/send/dispatch call in the if body

This means the code silently skips event publication when event_bus is None.
The bus should be required and injected; optional buses cause silent gaps.

Allowlist annotation: add  # none-guard-ok: <reason>  on the if line.

Exits 0 if clean, 1 if violations found (REPORT mode: always exits 0 with count).
[OMN-10818]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

EVENT_BUS_NAMES = frozenset({"_event_bus", "event_bus", "_bus", "bus"})
PUBLISH_METHODS = frozenset({"publish", "emit", "send", "dispatch"})
ALLOWLIST_MARKER = "# none-guard-ok"
SKIP_PATH_PARTS = frozenset({"tests", "test", "__pycache__", ".git", ".venv", "venv"})


class NoneGuardPublishDetector(ast.NodeVisitor):
    """AST visitor that detects event-bus none-guard before publish."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.violations: list[tuple[int, str]] = []

    def _line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""

    def _has_allowlist(self, lineno: int) -> bool:
        return ALLOWLIST_MARKER in self._line(lineno)

    def _is_bus_none_guard(self, test: ast.expr) -> bool:
        """Return True if test is `<bus> is not None` or `<bus>` (truthy guard)."""
        # `if event_bus is not None:`
        if isinstance(test, ast.Compare):
            if (
                len(test.ops) == 1
                and isinstance(test.ops[0], ast.IsNot)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
            ):
                return self._is_bus_name(test.left)
        # `if event_bus:` (truthy)
        if isinstance(test, (ast.Name, ast.Attribute)):
            return self._is_bus_name(test)
        return False

    def _is_bus_name(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in EVENT_BUS_NAMES
        if isinstance(node, ast.Attribute):
            return node.attr in EVENT_BUS_NAMES
        return False

    def _has_publish_call(self, body: list[ast.stmt]) -> bool:
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in PUBLISH_METHODS:
                    if self._is_bus_name(func.value):
                        return True
        return False

    def visit_If(self, node: ast.If) -> None:
        if self._is_bus_none_guard(node.test) and not self._has_allowlist(node.lineno):
            if self._has_publish_call(node.body):
                self.violations.append((node.lineno, self._line(node.lineno).rstrip()))
        self.generic_visit(node)


def scan_python_source(path: Path) -> list[tuple[int, str]]:
    path_str = str(path)
    if "tests/" in path_str or "/test/" in path_str or path_str.startswith("test_"):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        source_lines = content.splitlines()
        tree = ast.parse(content, filename=str(path))
        detector = NoneGuardPublishDetector(source_lines)
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
            f"FAIL: {len(violations)} event-bus none-guard-before-publish violation(s) found:\n"
        )
        for filepath, lineno, line_text in violations:
            print(f"  {filepath}:{lineno}")
            print(f"    {line_text}\n")
        print(
            "Fix: Require the event bus via DI (never make it optional).\n"
            "Annotate justified exceptions with  # none-guard-ok: <reason>\n"
            "[OMN-10818]"
        )
        return 0 if report_mode else 1

    print("PASS: No event-bus none-guard-before-publish violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
