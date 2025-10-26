#!/usr/bin/env python3
"""
ONEX Stubbed Functionality Validator

Detects incomplete or stubbed implementations in the codebase to ensure production readiness.

This validator looks for patterns that indicate incomplete implementations:
- NotImplementedError being raised
- Pass statements followed by return (common stub pattern)
- Always-success returns without meaningful logic
- TODO/FIXME comments in production code
- Methods that only contain docstrings

Excludes:
- Test files and fixtures (allowed to have stubs for testing)
- Abstract base classes (expected to raise NotImplementedError)
- Development/example files explicitly marked as incomplete
"""

import ast
import sys
from pathlib import Path


class StubbedFunctionalityChecker(ast.NodeVisitor):
    """AST visitor to detect stubbed functionality patterns."""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: list[tuple[int, str]] = []
        self.current_function = None
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track current class for context."""
        old_class = self.current_class
        self.current_class = node.name

        # Check for abstract base classes (allowed to have NotImplementedError)
        is_abstract = any(
            (isinstance(base, ast.Name) and "ABC" in base.id)
            or (
                isinstance(base, ast.Attribute) and base.attr in ["ABC", "AbstractBase"]
            )
            for base in node.bases
        )

        if not is_abstract:
            self.generic_visit(node)

        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for stubbed patterns."""
        old_function = self.current_function
        self.current_function = node.name

        # Skip dunder methods and abstract methods
        if (node.name.startswith("__") and node.name.endswith("__")) or any(
            isinstance(dec, ast.Name) and dec.id == "abstractmethod"
            for dec in node.decorator_list
        ):
            self.current_function = old_function
            return

        # Get meaningful statements (skip docstrings)
        meaningful_statements = []
        for i, stmt in enumerate(node.body):
            # Skip docstring
            if (
                i == 0
                and isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                continue
            meaningful_statements.append(stmt)

        # Check for various stub patterns
        self._check_stub_patterns(node, meaningful_statements)

        self.generic_visit(node)
        self.current_function = old_function

    def _check_stub_patterns(
        self, node: ast.FunctionDef, statements: list[ast.stmt]
    ) -> None:
        """Check for various stubbed functionality patterns."""

        if not statements:
            # Function with only docstring
            self.issues.append(
                (
                    node.lineno,
                    f"Function '{node.name}' contains only docstring (no implementation)",
                )
            )
            return

        # Pattern 1: NotImplementedError
        for stmt in statements:
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if (
                        isinstance(stmt.exc.func, ast.Name)
                        and stmt.exc.func.id == "NotImplementedError"
                    ):
                        self.issues.append(
                            (
                                stmt.lineno,
                                f"Function '{node.name}' raises NotImplementedError (stubbed)",
                            )
                        )

        # Pattern 2: Pass followed by return
        has_pass = False
        for i, stmt in enumerate(statements):
            if isinstance(stmt, ast.Pass):
                has_pass = True
                # Check if next statement is return
                if i + 1 < len(statements) and isinstance(
                    statements[i + 1], ast.Return
                ):
                    self.issues.append(
                        (
                            stmt.lineno,
                            f"Function '{node.name}' has pass followed by return (stub pattern)",
                        )
                    )

        # Pattern 3: Only pass statements
        if all(isinstance(stmt, ast.Pass) for stmt in statements):
            self.issues.append(
                (node.lineno, f"Function '{node.name}' contains only pass statements")
            )

        # Pattern 4: Always-success return without logic
        if len(statements) == 1 and isinstance(statements[0], ast.Return):
            return_stmt = statements[0]
            if isinstance(return_stmt.value, ast.Constant):
                if return_stmt.value.value in [True, "success", "ok"]:
                    self.issues.append(
                        (
                            return_stmt.lineno,
                            f"Function '{node.name}' returns constant success value without logic",
                        )
                    )

    def visit_Expr(self, node: ast.Expr) -> None:
        """Check for TODO/FIXME comments in string literals."""
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            comment_text = node.value.value.upper()
            if any(
                marker in comment_text for marker in ["TODO", "FIXME", "XXX", "HACK"]
            ):
                self.issues.append(
                    (
                        node.lineno,
                        f"Contains development comment: {node.value.value[:50]}...",
                    )
                )
        self.generic_visit(node)


class ONEXStubbedFunctionalityValidator:
    """Validates codebase for stubbed or incomplete functionality."""

    def __init__(self):
        self.errors: list[str] = []
        self.checked_files = 0

        # Files/patterns allowed to have stubs
        self.allowed_patterns = {
            "test_",  # Test files
            "/tests/",  # Test directories
            "/examples/",  # Example files
            "/prototypes/",  # Prototype code
            "conftest.py",  # Pytest configuration
            "__init__.py",  # Init files (may be empty)
            "/archived/",  # Archived code
            "/archive/",  # Archive directories
        }

        # Filename patterns (not path patterns) allowed to have stubs
        self.allowed_filenames = {
            "abstract_",  # Abstract base classes
            "base_",  # Base classes
        }

    def is_allowed_file(self, file_path: Path) -> bool:
        """Check if file is allowed to have stubbed functionality."""
        file_str = str(file_path)
        filename = file_path.name

        # Check path patterns
        if any(pattern in file_str for pattern in self.allowed_patterns):
            return True

        # Check filename patterns
        if any(filename.startswith(pattern) for pattern in self.allowed_filenames):
            return True

        return False

    def check_python_file(self, file_path: Path) -> bool:
        """Check a Python file for stubbed functionality."""
        if self.is_allowed_file(file_path):
            return True

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            self.checked_files += 1

            checker = StubbedFunctionalityChecker(str(file_path))
            checker.visit(tree)

            if checker.issues:
                for line_no, message in checker.issues:
                    self.errors.append(f"{file_path}:{line_no}: {message}")
                return False

            return True

        except Exception as e:
            self.errors.append(f"{file_path}: Failed to parse file - {e}")
            return False

    def check_files(self, file_paths: list[Path]) -> bool:
        """Check multiple files for stubbed functionality."""
        success = True
        for file_path in file_paths:
            if file_path.suffix == ".py":
                if not self.check_python_file(file_path):
                    success = False
        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ Stubbed Functionality Validation FAILED")
            print("=" * 60)
            print(
                f"Found {len(self.errors)} stubbed functionality issues in {self.checked_files} files:\n"
            )

            for error in self.errors:
                print(f"   • {error}")

            print("\n🔧 How to fix:")
            print("   Complete the implementation of stubbed functionality:")
            print("   ")
            print("   ❌ BAD:")
            print("   def process_data(self, data):")
            print("       '''Process the data.'''")
            print("       pass")
            print("       return True")
            print("   ")
            print("   ✅ GOOD:")
            print("   def process_data(self, data):")
            print("       '''Process the data by validating and transforming it.'''")
            print("       if not data:")
            print(
                "           raise OnexError(EnumCoreErrorCode.INVALID_INPUT, 'Data cannot be empty')"
            )
            print("       ")
            print("       # Actual processing logic")
            print("       processed = self._validate_and_transform(data)")
            print("       return processed")
            print("   ")
            print("   Guidelines:")
            print("   • Replace NotImplementedError with actual implementation")
            print("   • Remove pass statements and add meaningful logic")
            print("   • Replace TODO/FIXME comments with completed functionality")
            print("   • Ensure functions perform their documented behavior")
        else:
            print(
                f"✅ Stubbed Functionality Check PASSED ({self.checked_files} files checked)"
            )


def main() -> int:
    """Main entry point for the validation script."""
    if len(sys.argv) < 2:
        print("Usage: validate-stubbed-functionality.py <file1.py> [file2.py] ...")
        print(
            "Validates that code doesn't contain stubbed or incomplete functionality."
        )
        return 1

    validator = ONEXStubbedFunctionalityValidator()

    # Process all provided files
    file_paths = [Path(arg) for arg in sys.argv[1:]]
    success = validator.check_files(file_paths)

    validator.print_results()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
