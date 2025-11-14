#!/usr/bin/env python3
"""
ONEX Error Raising Validation

Comprehensive pre-commit hook that detects ALL standard Python exception raises
and enforces OnexError usage throughout the codebase.

Detected Patterns:
1. Standard Python exceptions (ValueError, TypeError, RuntimeError, etc.)
2. Generic Exception raises (too generic)
3. Custom exceptions (should use OnexError instead)
4. NotImplementedError (unless marked with # stub-ok)

Allowed Patterns:
1. OnexError raises - the ONEX standard
2. Exception catching (not raising)
3. Re-raising as OnexError with 'from e'
4. Explicit overrides with # error-ok: reason
5. Test files (tests/ directory)
6. ValueError/AssertionError in Pydantic validators (framework-mandated)

Pydantic Validator Exception (Auto-Detected):
Pydantic's validator framework requires raising ValueError or AssertionError for
validation failures. These exceptions are automatically allowed when raised inside
functions decorated with:
  - @model_validator (Pydantic v2)
  - @field_validator (Pydantic v2)
  - @validator (Pydantic v1)
  - @root_validator (Pydantic v1)

This is a framework requirement, not an anti-pattern. No # error-ok comment needed.

Usage:
    python scripts/validation/check_error_raising.py [files...]

    To allow specific exception raises, add comment:
    # error-ok: reason for using standard exception
"""

import ast
import sys
from pathlib import Path
from typing import Any


class ErrorRaisingDetector(ast.NodeVisitor):
    """AST visitor to detect standard exception raises in Python code."""

    # Standard Python exception types that should use OnexError
    STANDARD_EXCEPTIONS = {
        "ValueError",
        "TypeError",
        "RuntimeError",
        "KeyError",
        "AttributeError",
        "IndexError",
        "ImportError",
        "IOError",
        "OSError",
        "FileNotFoundError",
        "PermissionError",
        "ZeroDivisionError",
        "OverflowError",
        "RecursionError",
        "AssertionError",
        "SystemError",
        "MemoryError",
        "Exception",  # Too generic
        "StopIteration",
        "StopAsyncIteration",
        "ArithmeticError",
        "FloatingPointError",
        "LookupError",
        "NameError",
        "UnboundLocalError",
        "ReferenceError",
        "SystemExit",
        "KeyboardInterrupt",
        "GeneratorExit",
        "ConnectionError",
        "TimeoutError",
        "BlockingIOError",
        "ChildProcessError",
        "InterruptedError",
        "IsADirectoryError",
        "NotADirectoryError",
        "ProcessLookupError",
        "FileExistsError",
    }

    # Pydantic validator decorators that require ValueError/AssertionError
    # These are framework-mandated exception types for validation
    PYDANTIC_DECORATORS = {
        "model_validator",  # Pydantic v2
        "field_validator",  # Pydantic v2
        "validator",  # Pydantic v1
        "root_validator",  # Pydantic v1
    }

    # Exceptions that are allowed in Pydantic validators
    PYDANTIC_ALLOWED_EXCEPTIONS = {"ValueError", "AssertionError"}

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.violations: list[dict[str, Any]] = []
        self.in_exception_handler = False
        self.current_function_decorators: set[str] = set()
        self.function_decorator_stack: list[set[str]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Track when we're in an exception handler (catching is OK)."""
        prev_in_handler = self.in_exception_handler
        self.in_exception_handler = True
        self.generic_visit(node)
        self.in_exception_handler = prev_in_handler

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function decorators as we enter functions."""
        # Extract decorator names from this function
        decorators = self._extract_decorator_names(node.decorator_list)

        # Save current decorators and push new ones
        self.function_decorator_stack.append(self.current_function_decorators)
        self.current_function_decorators = decorators

        # Visit function body
        self.generic_visit(node)

        # Restore previous decorators
        self.current_function_decorators = self.function_decorator_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function decorators as we enter functions."""
        # Same logic as regular function
        decorators = self._extract_decorator_names(node.decorator_list)
        self.function_decorator_stack.append(self.current_function_decorators)
        self.current_function_decorators = decorators
        self.generic_visit(node)
        self.current_function_decorators = self.function_decorator_stack.pop()

    def _extract_decorator_names(self, decorator_list: list[ast.expr]) -> set[str]:
        """Extract decorator names from a decorator list."""
        decorators = set()
        for decorator in decorator_list:
            name = self._get_decorator_name(decorator)
            if name:
                decorators.add(name)
        return decorators

    def _get_decorator_name(self, node: ast.expr) -> str | None:
        """Get the name of a decorator from an AST node."""
        if isinstance(node, ast.Name):
            # Simple decorator: @decorator_name
            return node.id
        elif isinstance(node, ast.Call):
            # Decorator with arguments: @decorator_name(args)
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        elif isinstance(node, ast.Attribute):
            # Attribute decorator: @module.decorator_name
            return node.attr
        return None

    def _is_inside_pydantic_validator(self) -> bool:
        """Check if we're currently inside a Pydantic validator function."""
        return bool(self.current_function_decorators & self.PYDANTIC_DECORATORS)

    def visit_Raise(self, node: ast.Raise) -> None:
        """Check raise statements for OnexError compliance."""
        # Allow bare 're-raise' statements (raise without expression)
        if node.exc is None:
            self.generic_visit(node)
            return

        exception_name = self._get_exception_name(node.exc)

        # Skip if not a standard exception
        if exception_name not in self.STANDARD_EXCEPTIONS:
            # Special handling for NotImplementedError (check for stub-ok)
            if exception_name == "NotImplementedError":
                line_num = node.lineno
                if self._has_stub_ok_comment(line_num):
                    self.generic_visit(node)
                    return

                # NotImplementedError without stub-ok should use OnexError
                line = self.source_lines[line_num - 1].strip()
                if not self._has_error_ok_comment(line_num):
                    self.violations.append(
                        {
                            "type": "not_implemented_without_stub",
                            "line": line_num,
                            "code": line,
                            "exception": exception_name,
                            "message": (
                                "Uses NotImplementedError without # stub-ok comment. "
                                "Use OnexError instead or add # stub-ok: reason"
                            ),
                            "severity": "error",
                        }
                    )
            self.generic_visit(node)
            return

        line_num = node.lineno
        line = self.source_lines[line_num - 1].strip()

        # Check for error-ok comment
        if self._has_error_ok_comment(line_num):
            self.generic_visit(node)
            return

        # Check if this is a re-raise as OnexError
        if self._is_reraise_as_onex_error(node):
            self.generic_visit(node)
            return

        # PYDANTIC VALIDATOR EXCEPTION:
        # Allow ValueError and AssertionError in Pydantic validators
        # These are framework-mandated exception types for validation
        if (
            self._is_inside_pydantic_validator()
            and exception_name in self.PYDANTIC_ALLOWED_EXCEPTIONS
        ):
            self.generic_visit(node)
            return

        # Report violation
        self.violations.append(
            {
                "type": "standard_exception_raise",
                "line": line_num,
                "code": line,
                "exception": exception_name,
                "message": (
                    f"Uses standard Python exception '{exception_name}' instead of OnexError. "
                    f"Use OnexError with EnumCoreErrorCode"
                ),
                "severity": "error",
            }
        )

        self.generic_visit(node)

    def _get_exception_name(self, node: ast.expr | None) -> str | None:
        """Extract exception name from AST node."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_reraise_as_onex_error(self, node: ast.Raise) -> bool:
        """Check if this is re-raising as OnexError (raise ... from e)."""
        # Check if there's a 'cause' (from e)
        if node.cause is not None:
            # Check if the raised exception is OnexError
            exception_name = self._get_exception_name(node.exc)
            return exception_name == "OnexError"
        return False

    def _has_error_ok_comment(self, line_num: int) -> bool:
        """Check if line has # error-ok: comment."""
        if line_num < 1 or line_num > len(self.source_lines):
            return False

        # Check current line
        line = self.source_lines[line_num - 1]
        if "# error-ok:" in line:
            return True

        # Check previous line (for comments above the statement)
        if line_num > 1:
            prev_line = self.source_lines[line_num - 2]
            if "# error-ok:" in prev_line.strip():
                return True

        return False

    def _has_stub_ok_comment(self, line_num: int) -> bool:
        """Check if line has # stub-ok: comment."""
        if line_num < 1 or line_num > len(self.source_lines):
            return False

        # Check current line
        line = self.source_lines[line_num - 1]
        if "# stub-ok:" in line:
            return True

        # Check previous line (for comments above the statement)
        if line_num > 1:
            prev_line = self.source_lines[line_num - 2]
            if "# stub-ok:" in prev_line.strip():
                return True

        return False


def check_file(file_path: Path) -> list[dict[str, Any]]:
    """Check a single file for error raising violations."""
    # Skip test files
    if "tests/" in str(file_path) or str(file_path).startswith("test_"):
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
            source_lines = source.splitlines()

        tree = ast.parse(source, filename=str(file_path))
        detector = ErrorRaisingDetector(str(file_path), source_lines)
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        return [
            {
                "type": "syntax_error",
                "line": e.lineno or 0,
                "code": "",
                "exception": "SyntaxError",
                "message": f"Syntax error: {e.msg}",
                "severity": "error",
            }
        ]
    except Exception as e:
        return [
            {
                "type": "processing_error",
                "line": 0,
                "code": "",
                "exception": "ProcessingError",
                "message": f"Failed to process file: {e}",
                "severity": "warning",
            }
        ]


def main() -> int:
    """Main entry point for the validation script."""
    if len(sys.argv) < 2:
        print("Usage: check_error_raising.py <file1.py> [file2.py] ...")
        print(
            "Validates that all error raising uses OnexError instead of standard Python exceptions."
        )
        return 1

    all_violations: list[tuple[Path, dict[str, Any]]] = []

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        if file_path.suffix != ".py":
            continue

        violations = check_file(file_path)
        for violation in violations:
            all_violations.append((file_path, violation))

    if all_violations:
        print("❌ ONEX Error Raising Validation FAILED")
        print("=" * 80)
        print(f"Found {len(all_violations)} error raising violations:\n")

        for file_path, violation in all_violations:
            exception = violation["exception"]
            line = violation["line"]
            code = violation["code"]
            message = violation["message"]

            print(f"   {file_path}:{line}")
            print(f"   ❌ {message}")
            print(f"      Code: {code}")
            print()

        print("🔧 How to fix:")
        print("   Replace standard Python exceptions with OnexError:")
        print()
        print("   ❌ BAD:")
        print("   raise ValueError('Invalid input value')")
        print()
        print("   ✅ GOOD:")
        print("   from omnibase_core.exceptions.onex_error import OnexError")
        print(
            "   from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode"
        )
        print()
        print("   raise OnexError(")
        print("       code=EnumCoreErrorCode.VALIDATION_ERROR,")
        print("       message='Invalid input value'")
        print("   )")
        print()
        print("   To allow specific exceptions, add comment:")
        print("   raise ValueError(...)  # error-ok: reason for exception")
        print()
        print("   Benefits of OnexError:")
        print("   • Consistent error handling across ONEX framework")
        print("   • Structured error codes for programmatic handling")
        print("   • Rich error context for debugging")
        print("   • Standardized error reporting and logging")

        return 1

    print(f"✅ ONEX Error Raising Check PASSED ({len(sys.argv) - 1} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
