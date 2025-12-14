#!/usr/bin/env python3
"""
ONEX No Print Statements Validation

This pre-commit hook detects and prevents print() statements in production code.
All logging should use structured logging (logger.debug/info/warning/error)
or emit_log_event() for proper observability.

Detected Patterns:
1. Direct print() function calls
2. print() in docstring code examples (documentation should show best practices)

Usage:
    python scripts/validation/check_no_print_statements.py [files...]

    To allow specific prints (e.g., CLI tools), add comment:
    # print-ok: reason for exception

Rationale:
    - print() statements are not captured by logging infrastructure
    - They bypass log levels, filters, and formatters
    - They cannot be redirected to file, syslog, or observability tools
    - They pollute stdout in production environments
    - Documentation examples should demonstrate best practices

Reference:
    - OMN-701: Replace print statements with structured logging
    - OMNIBASE_CORE_CODE_QUALITY_AUDIT.md - Section 2
"""

import ast
import sys
from pathlib import Path
from typing import Any


class PrintStatementDetector(ast.NodeVisitor):
    """AST visitor to detect print() statements in Python code."""

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Detect print() function calls."""
        # Check for direct print() calls
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            line_num = node.lineno
            line = (
                self.source_lines[line_num - 1].strip()
                if line_num <= len(self.source_lines)
                else ""
            )

            # Check for print-ok comment
            if self._has_print_ok_comment(line_num):
                self.generic_visit(node)
                return

            self.violations.append(
                {
                    "type": "print_statement",
                    "line": line_num,
                    "code": line,
                    "message": (
                        "print() statement detected. Use structured logging instead: "
                        "logger.debug(), logger.info(), logger.warning(), or logger.error()"
                    ),
                    "severity": "error",
                }
            )

        self.generic_visit(node)

    def _has_print_ok_comment(self, line_num: int) -> bool:
        """Check if line has a # print-ok: comment allowing the print."""
        # Check same line
        if line_num <= len(self.source_lines):
            line = self.source_lines[line_num - 1]
            if "# print-ok:" in line:
                return True

        # Check line above
        if line_num > 1:
            prev_line = self.source_lines[line_num - 2]
            if "# print-ok:" in prev_line.strip():
                return True

        return False


def check_docstring_prints(
    filename: str, source: str, source_lines: list[str]
) -> list[dict[str, Any]]:
    """
    Check for print() in docstring code examples.

    Even in docstrings, we want to show best practices using logger.* instead of print().
    """
    violations: list[dict[str, Any]] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        # Check docstrings in functions, classes, and modules
        docstring = None
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            docstring = ast.get_docstring(node)

        if docstring and "print(" in docstring:
            # Find the actual line number of the docstring
            if hasattr(node, "body") and node.body:
                first_stmt = node.body[0]
                if isinstance(first_stmt, ast.Expr) and isinstance(
                    first_stmt.value, ast.Constant
                ):
                    # Find print( in the docstring and report it
                    docstring_start = first_stmt.lineno
                    # Detect if opening quotes are on separate line (accounts for off-by-one)
                    opening_line = (
                        source_lines[docstring_start - 1].strip()
                        if docstring_start <= len(source_lines)
                        else ""
                    )
                    offset = 1 if opening_line in ('"""', "'''") else 0
                    docstring_lines = docstring.split("\n")

                    for i, doc_line in enumerate(docstring_lines):
                        if "print(" in doc_line:
                            actual_line = docstring_start + i + offset
                            line_content = (
                                source_lines[actual_line - 1].strip()
                                if actual_line <= len(source_lines)
                                else doc_line.strip()
                            )

                            # Check for print-ok comment
                            if "# print-ok:" in line_content:
                                continue

                            violations.append(
                                {
                                    "type": "docstring_print",
                                    "line": actual_line,
                                    "code": line_content,
                                    "message": (
                                        "print() in docstring example. Documentation should demonstrate "
                                        "best practices using logger.debug/info/warning/error()"
                                    ),
                                    "severity": "warning",
                                }
                            )

    return violations


def check_file(filepath: Path) -> list[dict[str, Any]]:
    """Check a single file for print statements."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [
            {
                "type": "read_error",
                "line": 0,
                "code": "",
                "message": str(e),
                "severity": "error",
            }
        ]

    source_lines = source.splitlines()

    # Parse and check AST for actual print() calls
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [
            {
                "type": "syntax_error",
                "line": e.lineno or 0,
                "code": "",
                "message": str(e),
                "severity": "error",
            }
        ]

    detector = PrintStatementDetector(str(filepath), source_lines)
    detector.visit(tree)

    # Also check docstring examples
    docstring_violations = check_docstring_prints(str(filepath), source, source_lines)

    return detector.violations + docstring_violations


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: check_no_print_statements.py <file1> [file2] ..."
        )  # print-ok: CLI output
        return 1

    files = [Path(f) for f in sys.argv[1:]]
    all_violations: list[tuple[Path, dict[str, Any]]] = []

    for filepath in files:
        if not filepath.exists():
            continue
        if filepath.suffix != ".py":
            continue

        violations = check_file(filepath)
        for v in violations:
            all_violations.append((filepath, v))

    if all_violations:
        print(f"\n{'=' * 60}")  # print-ok: CLI output
        print("ONEX Print Statement Validation Failed")  # print-ok: CLI output
        print(f"{'=' * 60}\n")  # print-ok: CLI output

        errors = [v for v in all_violations if v[1]["severity"] == "error"]
        warnings = [v for v in all_violations if v[1]["severity"] == "warning"]

        if errors:
            print(f"ERRORS ({len(errors)}):")  # print-ok: CLI output
            print("-" * 40)  # print-ok: CLI output
            for filepath, v in errors:
                print(f"  {filepath}:{v['line']}")  # print-ok: CLI output
                print(f"    {v['code']}")  # print-ok: CLI output
                print(f"    -> {v['message']}\n")  # print-ok: CLI output

        if warnings:
            print(f"WARNINGS ({len(warnings)}):")  # print-ok: CLI output
            print("-" * 40)  # print-ok: CLI output
            for filepath, v in warnings:
                print(f"  {filepath}:{v['line']}")  # print-ok: CLI output
                print(f"    {v['code']}")  # print-ok: CLI output
                print(f"    -> {v['message']}\n")  # print-ok: CLI output

        print(
            "\nTo allow specific prints, add: # print-ok: <reason>"
        )  # print-ok: CLI output
        print(
            f"Total: {len(errors)} errors, {len(warnings)} warnings"
        )  # print-ok: CLI output

        # Fail on errors only (warnings don't block commit)
        return 1 if errors else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
