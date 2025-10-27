#!/usr/bin/env python3
"""
ONEX Elif Chain Limit Validator

Enforces limits on elif chain length to maintain code readability and encourage better patterns.

Long elif chains often indicate:
- Missing use of dictionary/mapping patterns
- Need for polymorphism or strategy pattern
- Complex conditional logic that should be refactored
- Poor code organization

This validator:
- Limits elif chains to a maximum count (default: 5)
- Suggests alternative patterns for complex conditionals
- Excludes specific patterns where elif chains are appropriate (e.g., parsing, state machines)
"""

import ast
import sys
from pathlib import Path


class ElifChainChecker(ast.NodeVisitor):
    """AST visitor to detect excessively long elif chains."""

    def __init__(self, filename: str, max_elif_count: int = 5):
        self.filename = filename
        self.max_elif_count = max_elif_count
        self.issues: list[tuple[int, str, int]] = []
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track current function for context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_If(self, node: ast.If) -> None:
        """Check if statements for excessive elif chains."""
        elif_count = 0
        current = node

        # Count consecutive elif statements
        while current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                # This is an elif
                elif_count += 1
                current = current.orelse[0]
            else:
                # This is an else block, stop counting
                break

        if elif_count > self.max_elif_count:
            context = (
                f" in function '{self.current_function}'"
                if self.current_function
                else ""
            )
            self.issues.append(
                (
                    node.lineno,
                    f"Elif chain with {elif_count} branches exceeds limit of {self.max_elif_count}{context}",
                    elif_count,
                )
            )

        self.generic_visit(node)


class ONEXElifLimitValidator:
    """Validates that elif chains don't exceed reasonable limits."""

    def __init__(self, max_elif_count: int = 5):
        self.max_elif_count = max_elif_count
        self.errors: list[str] = []
        self.checked_files = 0

        # Files/patterns where long elif chains might be acceptable
        self.allowed_patterns = {
            "/tests/",  # Test files
            "test_",  # Test files
            "parser",  # Parser implementations
            "lexer",  # Lexer implementations
            "state_machine",  # State machine implementations
            "/migration/",  # Migration scripts
            "/cli/",  # CLI command handling
            "conftest.py",  # Pytest configuration
        }

        # Function patterns where long elif chains might be acceptable
        self.allowed_function_patterns = {
            "parse",
            "handle_command",
            "process_state",
            "migrate",
            "dispatch",
            "route",
        }

    def is_allowed_file(self, file_path: Path) -> bool:
        """Check if file is allowed to have long elif chains."""
        file_str = str(file_path).lower()
        return any(pattern in file_str for pattern in self.allowed_patterns)

    def is_allowed_function(self, function_name: str | None) -> bool:
        """Check if function is allowed to have long elif chains."""
        if not function_name:
            return False
        function_lower = function_name.lower()
        return any(
            pattern in function_lower for pattern in self.allowed_function_patterns
        )

    def check_python_file(self, file_path: Path) -> bool:
        """Check a Python file for excessive elif chains."""
        if self.is_allowed_file(file_path):
            return True

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            self.checked_files += 1

            checker = ElifChainChecker(str(file_path), self.max_elif_count)
            checker.visit(tree)

            if checker.issues:
                for line_no, message, elif_count in checker.issues:
                    # Check if this is in an allowed function
                    if not self.is_allowed_function(checker.current_function):
                        self.errors.append(f"{file_path}:{line_no}: {message}")
                        continue

                return (
                    len(
                        [
                            issue
                            for issue in checker.issues
                            if not self.is_allowed_function(checker.current_function)
                        ]
                    )
                    == 0
                )

            return True

        except Exception as e:
            self.errors.append(f"{file_path}: Failed to parse file - {e}")
            return False

    def check_files(self, file_paths: list[Path]) -> bool:
        """Check multiple files for excessive elif chains."""
        success = True
        for file_path in file_paths:
            if file_path.suffix == ".py":
                if not self.check_python_file(file_path):
                    success = False
        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ Elif Chain Limit Validation FAILED")
            print("=" * 60)
            print(
                f"Found {len(self.errors)} excessive elif chain violations in {self.checked_files} files:\n"
            )

            for error in self.errors:
                print(f"   • {error}")

            print(f"\n🔧 How to fix (limit: {self.max_elif_count} elif branches):")
            print("   Replace long elif chains with better patterns:")
            print("   ")
            print("   ❌ BAD:")
            print("   if status == 'pending':")
            print("       return 'Waiting for processing'")
            print("   elif status == 'processing':")
            print("       return 'Currently processing'")
            print("   elif status == 'completed':")
            print("       return 'Process completed'")
            print("   elif status == 'failed':")
            print("       return 'Process failed'")
            print("   elif status == 'cancelled':")
            print("       return 'Process cancelled'")
            print("   elif status == 'timeout':")
            print("       return 'Process timed out'")
            print("   ")
            print("   ✅ GOOD - Dictionary/Mapping Pattern:")
            print("   STATUS_MESSAGES = {")
            print("       'pending': 'Waiting for processing',")
            print("       'processing': 'Currently processing',")
            print("       'completed': 'Process completed',")
            print("       'failed': 'Process failed',")
            print("       'cancelled': 'Process cancelled',")
            print("       'timeout': 'Process timed out'")
            print("   }")
            print("   return STATUS_MESSAGES.get(status, 'Unknown status')")
            print("   ")
            print("   ✅ GOOD - Enum with Methods:")
            print("   class ProcessStatus(Enum):")
            print("       PENDING = 'pending'")
            print("       PROCESSING = 'processing'")
            print("       # ... other statuses")
            print("       ")
            print("       def get_message(self) -> str:")
            print("           return self._get_status_message()")
            print("   ")
            print("   ✅ GOOD - Strategy Pattern:")
            print("   class StatusHandler:")
            print("       def __init__(self):")
            print("           self.handlers = {")
            print("               'pending': self._handle_pending,")
            print("               'processing': self._handle_processing,")
            print("               # ... other handlers")
            print("           }")
            print("   ")
            print("   Alternative patterns:")
            print("   • Dictionary/mapping for simple value lookups")
            print("   • Enum classes with methods for related behavior")
            print("   • Strategy pattern for complex conditional logic")
            print("   • Polymorphism for type-based behavior")
            print("   • Early returns to reduce nesting")

        else:
            print(
                f"✅ Elif Chain Limit Check PASSED ({self.checked_files} files checked)"
            )


def main() -> int:
    """Main entry point for the validation script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate elif chain limits in Python files"
    )
    parser.add_argument("files", nargs="+", help="Python files to validate")
    parser.add_argument(
        "--max-elif",
        type=int,
        default=5,
        help="Maximum number of elif branches allowed (default: 5)",
    )

    args = parser.parse_args()

    validator = ONEXElifLimitValidator(max_elif_count=args.max_elif)

    # Process all provided files
    file_paths = [Path(f) for f in args.files]
    success = validator.check_files(file_paths)

    validator.print_results()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
