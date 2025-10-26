#!/usr/bin/env python3
"""
ONEX Error Compliance Validator

Ensures all exceptions raised in the codebase use OnexError instead of standard Python exceptions.
This maintains consistency with ONEX error handling standards and provides structured error context.

Key validations:
- All raised exceptions should be OnexError instances
- Standard Python exceptions should be converted to OnexError
- Proper error codes from EnumCoreErrorCode should be used
- Error context should be provided via ModelErrorContext

Exceptions allowed:
- Test files can raise standard exceptions for testing purposes
- Validation scripts can raise exceptions for script execution
- Third-party library integration may use standard exceptions (with explicit approval)
"""

import ast
import sys
from pathlib import Path


class OnexErrorComplianceChecker:
    """Checks that all raised exceptions use OnexError instead of standard Python exceptions."""

    def __init__(self):
        self.errors: list[str] = []
        self.checked_files = 0

        # Standard exceptions that should be converted to OnexError
        self.standard_exceptions = {
            "ValueError",
            "TypeError",
            "RuntimeError",
            "KeyError",
            "AttributeError",
            "IndexError",
            "FileNotFoundError",
            "PermissionError",
            "ImportError",
            "ModuleNotFoundError",
            "NotImplementedError",
            "OSError",
            "IOError",
            "ConnectionError",
            "TimeoutError",
            "JSONDecodeError",
            "ConfigurationError",
        }

        # Custom exceptions that should be converted
        self.custom_exceptions = {"YamlLoadingError"}  # Found in safe_yaml_loader.py

        # Files that are allowed to use standard exceptions
        self.allowed_patterns = {
            "test_",  # Test files
            "/tests/",  # Test directories
            "/validation/",  # Validation scripts themselves
            "/scripts/",  # Script files
            "__main__.py",  # Main entry points
            "conftest.py",  # Pytest configuration
        }

    def is_allowed_file(self, file_path: Path) -> bool:
        """Check if file is allowed to use standard exceptions."""
        file_str = str(file_path)
        return any(pattern in file_str for pattern in self.allowed_patterns)

    def check_python_file(self, file_path: Path) -> bool:
        """Check a Python file for OnexError compliance."""
        if self.is_allowed_file(file_path):
            return True

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            self.checked_files += 1

            # Check for OnexError import
            has_onex_error_import = self._has_onex_error_import(tree)

            # Find all raise statements
            raise_checker = RaiseStatementChecker(file_path, has_onex_error_import)
            raise_checker.visit(tree)

            if raise_checker.violations:
                self.errors.extend(raise_checker.violations)
                return False

            return True

        except Exception as e:
            self.errors.append(f"{file_path}: Failed to parse file - {e}")
            return False

    def _has_onex_error_import(self, tree: ast.AST) -> bool:
        """Check if file imports ModelOnexError."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (
                    node.module
                    and "error_codes" in node.module
                    and any(
                        alias.name == "ModelOnexError" for alias in node.names or []
                    )
                ):
                    return True
            elif isinstance(node, ast.Import):
                if any("ModelOnexError" in alias.name for alias in node.names):
                    return True
        return False

    def check_files(self, file_paths: list[Path]) -> bool:
        """Check multiple files for OnexError compliance."""
        success = True
        for file_path in file_paths:
            if file_path.suffix == ".py":
                if not self.check_python_file(file_path):
                    success = False
        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ ONEX Error Compliance Validation FAILED")
            print("=" * 60)
            print(
                f"Found {len(self.errors)} OnexError compliance violations in {self.checked_files} files:\n"
            )

            for error in self.errors:
                print(f"   • {error}")

            print("\n🔧 How to fix:")
            print("   Replace standard Python exceptions with ModelOnexError:")
            print("   ")
            print("   ❌ BAD:")
            print("   raise ValueError('Invalid input value')")
            print("   ")
            print("   ✅ GOOD:")
            print("   from omnibase_core.errors.error_codes import ModelOnexError")
            print("   from omnibase_core.errors.error_codes import ModelCoreErrorCode")
            print("   ")
            print("   raise ModelOnexError(")
            print("       message='Invalid input value',")
            print("       error_code=ModelCoreErrorCode.VALIDATION_ERROR")
            print("   )")
            print("   ")
            print("   Benefits of ModelOnexError:")
            print("   • Consistent error handling across ONEX framework")
            print("   • Structured error codes for programmatic handling")
            print("   • Rich error context for debugging")
            print("   • Standardized error reporting and logging")
        else:
            print(
                f"✅ ONEX Error Compliance Check PASSED ({self.checked_files} files checked)"
            )


class RaiseStatementChecker(ast.NodeVisitor):
    """AST visitor to check raise statements for OnexError compliance."""

    def __init__(self, file_path: Path, has_onex_error_import: bool):
        self.file_path = file_path
        self.has_onex_error_import = has_onex_error_import
        self.violations: list[str] = []

        # Standard exceptions that should be converted
        self.forbidden_exceptions = {
            "ValueError",
            "TypeError",
            "RuntimeError",
            "KeyError",
            "AttributeError",
            "IndexError",
            "FileNotFoundError",
            "PermissionError",
            "ImportError",
            "ModuleNotFoundError",
            "NotImplementedError",
            "OSError",
            "IOError",
            "ConnectionError",
            "TimeoutError",
            "YamlLoadingError",
        }

        # Read file content to check for error-ok comments
        with open(file_path, encoding="utf-8") as f:
            self.file_content = f.read()
            self.file_lines = self.file_content.split("\n")

    def visit_Raise(self, node: ast.Raise) -> None:
        """Check raise statements for OnexError compliance."""
        if node.exc:
            # Check for error-ok comment on the same line or previous line
            if self._has_error_ok_comment(node.lineno):
                return

            exception_name = self._get_exception_name(node.exc)

            if exception_name in self.forbidden_exceptions:
                self.violations.append(
                    f"{self.file_path}:{node.lineno}: "
                    f"Uses standard exception '{exception_name}' instead of ModelOnexError"
                )
            elif exception_name and exception_name not in [
                "OnexError",
                "ModelOnexError",
            ]:
                # Check if it's a known exception that should be converted
                if (
                    exception_name.endswith(("Error", "Exception"))
                ) and exception_name not in ["OnexError", "ModelOnexError"]:
                    self.violations.append(
                        f"{self.file_path}:{node.lineno}: "
                        f"Uses custom exception '{exception_name}' instead of ModelOnexError"
                    )

        self.generic_visit(node)

    def _has_error_ok_comment(self, line_num: int) -> bool:
        """Check if there's an error-ok comment on or before the given line."""
        # Check same line
        if line_num <= len(self.file_lines):
            line = self.file_lines[line_num - 1]
            if "# error-ok" in line or "# stub-ok" in line:
                return True

        # Check previous line
        if line_num > 1 and line_num - 1 <= len(self.file_lines):
            prev_line = self.file_lines[line_num - 2]
            if "# error-ok" in prev_line or "# stub-ok" in prev_line:
                return True

        return False

    def _get_exception_name(self, node: ast.expr) -> str | None:
        """Extract exception name from AST node."""
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


def main() -> int:
    """Main entry point for the validation script."""
    if len(sys.argv) < 2:
        print("Usage: validate-onex-error-compliance.py <file1.py> [file2.py] ...")
        print(
            "Validates that all raised exceptions use OnexError instead of standard Python exceptions."
        )
        return 1

    checker = OnexErrorComplianceChecker()

    # Process all provided files
    file_paths = [Path(arg) for arg in sys.argv[1:]]
    success = checker.check_files(file_paths)

    checker.print_results()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
