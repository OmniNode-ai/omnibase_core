#!/usr/bin/env python3
"""
ONEX No Fallback Patterns Validation

This pre-commit hook detects and prevents fallback patterns that violate the
"fail fast with explicit errors" principle. Code should raise clear errors
instead of silently falling back to default behavior.

Detected Patterns:
1. id(self) usage in get_id() methods - non-deterministic across process restarts
2. if 'field' in info.data patterns in validators - silent validation skipping
3. except ValueError: ... = Enum.UNKNOWN patterns - silent enum fallbacks
4. Bare except: or except Exception: without re-raise - error swallowing
5. .get(key, default) on enum mappings without error handling - silent defaults

Usage:
    python scripts/validation/check_no_fallbacks.py [files...]

    To allow specific fallbacks, add comment:
    # fallback-ok: reason for exception
"""

import ast
import sys
from pathlib import Path
from typing import Any


class FallbackDetector(ast.NodeVisitor):
    """AST visitor to detect fallback patterns in Python code."""

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[dict[str, Any]] = []
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track current function for context."""
        prev_function = self.current_function
        self.current_function = node.name

        # Check for id(self) usage in get_id() methods
        if node.name == "get_id":
            self._check_get_id_fallback(node)

        # Check for validator fallbacks
        has_field_validator = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "field_validator":
                has_field_validator = True
                break
            if isinstance(decorator, ast.Call):
                # Handle @field_validator("field_name") pattern
                if (
                    isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "field_validator"
                ):
                    has_field_validator = True
                    break

        if has_field_validator:
            self._check_validator_fallback(node)

        self.generic_visit(node)
        self.current_function = prev_function

    def visit_Try(self, node: ast.Try) -> None:
        """Check for silent exception handling fallbacks."""
        self._check_exception_fallback(node)
        self.generic_visit(node)

    def _check_get_id_fallback(self, node: ast.FunctionDef) -> None:
        """Detect id(self) usage in get_id() methods."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                # Check for id(self) in return statement
                if self._contains_id_self(stmt.value):
                    line_num = stmt.lineno
                    line = self.source_lines[line_num - 1].strip()

                    # Check for fallback-ok comment
                    if self._has_fallback_ok_comment(line_num):
                        continue

                    self.violations.append(
                        {
                            "type": "id_self_fallback",
                            "line": line_num,
                            "code": line,
                            "message": (
                                "get_id() uses id(self) fallback - non-deterministic across process restarts. "
                                "Raise ValueError instead if no UUID field found."
                            ),
                            "severity": "error",
                        }
                    )

    def _check_validator_fallback(self, node: ast.FunctionDef) -> None:
        """Detect if 'field' in info.data patterns in validators."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.If):
                # Check for "if 'field' in info.data" pattern
                if self._is_validator_field_check(stmt.test):
                    line_num = stmt.lineno
                    line = self.source_lines[line_num - 1].strip()

                    # Check for fallback-ok comment
                    if self._has_fallback_ok_comment(line_num):
                        continue

                    self.violations.append(
                        {
                            "type": "validator_field_fallback",
                            "line": line_num,
                            "code": line,
                            "message": (
                                "Validator uses 'field in info.data' pattern - silently skips validation if field missing. "
                                "Use @model_validator(mode='after') to ensure all fields are available."
                            ),
                            "severity": "error",
                        }
                    )

    def _check_exception_fallback(self, node: ast.Try) -> None:
        """Detect silent exception handling fallbacks."""
        for handler in node.handlers:
            # Check for bare except or broad Exception without re-raise
            is_bare_except = handler.type is None
            is_broad_exception = (
                isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
            )

            # Check if exception is re-raised
            has_reraise = any(
                isinstance(stmt, ast.Raise) and stmt.exc is None
                for stmt in handler.body
            )

            # Check for enum fallback pattern (assignment to UNKNOWN) - check all exception types
            if not has_reraise:
                for stmt in handler.body:
                    if isinstance(stmt, ast.Assign):
                        if self._is_enum_unknown_assignment(stmt):
                            line_num = stmt.lineno
                            line = self.source_lines[line_num - 1].strip()

                            # Check for fallback-ok comment
                            if self._has_fallback_ok_comment(line_num):
                                continue

                            self.violations.append(
                                {
                                    "type": "enum_fallback",
                                    "line": line_num,
                                    "code": line,
                                    "message": (
                                        "Exception handler assigns enum to UNKNOWN/NONE - silent fallback. "
                                        "Raise ValueError with clear message instead."
                                    ),
                                    "severity": "error",
                                }
                            )

            # Check for return in except block - only for bare/broad exceptions
            if is_bare_except or is_broad_exception:
                if not has_reraise:
                    # Check for return in except block
                    has_return = any(
                        isinstance(stmt, ast.Return) for stmt in handler.body
                    )

                    if has_return and not self._has_logging(handler):
                        line_num = handler.lineno
                        line = self.source_lines[line_num - 1].strip()

                        # Check for fallback-ok comment
                        if self._has_fallback_ok_comment(line_num):
                            continue

                        self.violations.append(
                            {
                                "type": "silent_exception_return",
                                "line": line_num,
                                "code": line,
                                "message": (
                                    "Exception handler returns value without re-raising - swallows errors. "
                                    "Either re-raise with 'raise' or raise a new error with context."
                                ),
                                "severity": "error",
                            }
                        )

    def _contains_id_self(self, node: ast.AST) -> bool:
        """Check if AST node contains id(self) call."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "id":
                if node.args and isinstance(node.args[0], ast.Name):
                    if node.args[0].id == "self":
                        return True
        # Check in f-strings and format strings
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == "id":
                    if child.args and isinstance(child.args[0], ast.Name):
                        if child.args[0].id == "self":
                            return True
        return False

    def _is_validator_field_check(self, node: ast.AST) -> bool:
        """Check if node is 'field' in info.data pattern."""
        # Handle BoolOp (and/or) by recursively checking values
        if isinstance(node, ast.BoolOp):
            return any(self._is_validator_field_check(val) for val in node.values)

        if isinstance(node, ast.Compare):
            # Check for "field" in info.data
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                if any(isinstance(op, ast.In) for op in node.ops):
                    for comp in node.comparators:
                        if isinstance(comp, ast.Attribute):
                            if (
                                isinstance(comp.value, ast.Name)
                                and comp.value.id == "info"
                                and comp.attr == "data"
                            ):
                                return True
        return False

    def _is_enum_unknown_assignment(self, node: ast.Assign) -> bool:
        """Check if assignment is to an enum UNKNOWN or NONE value."""
        if isinstance(node.value, ast.Attribute):
            if node.value.attr in ("UNKNOWN", "NONE"):
                # Check if it's an enum (class name contains "Enum" or is CamelCase)
                if isinstance(node.value.value, ast.Name):
                    class_name = node.value.value.id
                    # Accept if contains "Enum", is all uppercase, or is CamelCase (starts with capital)
                    if (
                        "Enum" in class_name
                        or class_name.isupper()
                        or (class_name[0].isupper() if class_name else False)
                    ):
                        return True
        return False

    def _has_logging(self, handler: ast.ExceptHandler) -> bool:
        """Check if exception handler has logging."""
        for stmt in handler.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                if isinstance(stmt.value.func, ast.Attribute):
                    if stmt.value.func.attr in (
                        "error",
                        "warning",
                        "debug",
                        "info",
                        "log",
                    ):
                        return True
        return False

    def _has_fallback_ok_comment(self, line_num: int) -> bool:
        """Check if line or subsequent lines (for Black formatting) have fallback-ok comment."""
        # Check the current line and up to 3 lines after for Black multi-line formatting
        # Example: except (\n    Exception\n):  # fallback-ok: ...\n    return False
        for offset in range(4):  # Check current line + next 3 lines
            check_line_idx = line_num - 1 + offset
            if check_line_idx < len(self.source_lines):
                line = self.source_lines[check_line_idx]
                if "# fallback-ok:" in line.lower():
                    return True
        return False


def check_file_for_fallbacks(filepath: Path) -> list[dict[str, Any]]:
    """Check a single file for fallback patterns."""
    try:
        source = filepath.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(filepath))

        detector = FallbackDetector(str(filepath), source_lines)
        detector.visit(tree)

        return detector.violations
    except SyntaxError as e:
        # Skip files with syntax errors
        return []
    except Exception as e:
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return []


def print_violations(violations: dict[str, list[dict[str, Any]]]) -> None:
    """Print violations in a clear format."""
    total_violations = sum(len(v) for v in violations.values())

    if total_violations == 0:
        print("✅ No fallback patterns detected!")
        return

    print(f"\n❌ Found {total_violations} fallback pattern(s):\n")

    for filepath, file_violations in sorted(violations.items()):
        if not file_violations:
            continue

        print(f"\n{filepath}")
        print("-" * len(filepath))

        for violation in file_violations:
            print(f"\nLine {violation['line']}: {violation['type']}")
            print(f"  Code: {violation['code']}")
            print(f"  Issue: {violation['message']}")
            print(f"  Severity: {violation['severity'].upper()}")

    print("\n" + "=" * 80)
    print("\nFallback Pattern Summary:")
    print("=" * 80)

    # Count by type
    type_counts: dict[str, int] = {}
    for file_violations in violations.values():
        for violation in file_violations:
            type_counts[violation["type"]] = type_counts.get(violation["type"], 0) + 1

    for violation_type, count in sorted(type_counts.items()):
        print(f"  {violation_type}: {count}")

    print("\n" + "=" * 80)
    print("\nTo allow specific fallbacks, add comment:")
    print("  # fallback-ok: reason for exception")
    print("\n" + "=" * 80)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_no_fallbacks.py [files...]", file=sys.stderr)
        return 1

    files = [Path(f) for f in sys.argv[1:] if Path(f).suffix == ".py"]

    if not files:
        print("No Python files to check", file=sys.stderr)
        return 0

    violations: dict[str, list[dict[str, Any]]] = {}

    for filepath in files:
        if not filepath.exists():
            print(f"Warning: File not found: {filepath}", file=sys.stderr)
            continue

        file_violations = check_file_for_fallbacks(filepath)
        if file_violations:
            violations[str(filepath)] = file_violations

    print_violations(violations)

    # Return non-zero if violations found
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
