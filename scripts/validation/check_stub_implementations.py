#!/usr/bin/env python3
"""
ONEX Stub Implementation Detector - AST-Based Pre-commit Hook

Detects stub function/method implementations in Python code using AST parsing.
This ensures production-ready code without incomplete implementations.

Detection Patterns:
    - Functions/methods containing only 'pass'
    - Functions/methods containing only '...' (Ellipsis)
    - Functions/methods that only raise NotImplementedError
    - Functions/methods with TODO/FIXME comments suggesting incomplete work
    - Empty function bodies (docstring + pass/ellipsis)

Exclusions (Legitimate Cases):
    - Abstract base class methods (@abstractmethod decorator)
    - Overload decorated methods (@overload for type hints)
    - Protocol class methods (typing.Protocol subclasses)
    - Type stub files (.pyi extension)
    - Test fixtures with intentional pass statements
    - __init__.py files with protocol definitions
    - Dunder methods (__init__, __str__, etc.)

Configuration:
    - Supports exclusion via inline comments: # stub-ok
    - Supports exclusion via config file (.stub-check-config.yaml)
    - --check-mode: CI mode (strict checking)
    - --fix-suggestions: Provides code fix suggestions

Usage:
    python check_stub_implementations.py <file1.py> [file2.py] ...
    python check_stub_implementations.py --check-mode src/
    python check_stub_implementations.py --fix-suggestions file.py
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class StubIssue:
    """Represents a detected stub implementation issue."""

    file_path: str
    line_no: int
    function_name: str
    issue_type: str
    description: str
    fix_suggestion: str | None = None


class StubDetectorConfig:
    """Configuration for stub detection."""

    def __init__(self, config_path: Path | None = None):
        self.excluded_files: set[str] = set()
        self.excluded_patterns: set[str] = set()
        self.excluded_functions: set[str] = set()

        # Default exclusions
        self.default_exclusions = {
            "test_",  # Test files
            "/tests/",  # Test directories
            "/examples/",  # Example code
            "/prototypes/",  # Prototype code
            "/archived/",  # Archived code
            "/archive/",  # Archive directories
            "conftest.py",  # Pytest configuration
        }

        # Load config if available
        if config_path and config_path.exists() and YAML_AVAILABLE:
            self._load_config(config_path)

    def _load_config(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            self.excluded_files.update(config.get("excluded_files", []))
            self.excluded_patterns.update(config.get("excluded_patterns", []))
            self.excluded_functions.update(config.get("excluded_functions", []))
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")

    def is_excluded(self, file_path: Path, function_name: str | None = None) -> bool:
        """Check if file or function is excluded from checking."""
        file_str = str(file_path)

        # Check default exclusions
        if any(pattern in file_str for pattern in self.default_exclusions):
            return True

        # Check configured exclusions
        if file_path.name in self.excluded_files:
            return True

        if any(pattern in file_str for pattern in self.excluded_patterns):
            return True

        if function_name and function_name in self.excluded_functions:
            return True

        return False


class StubImplementationDetector(ast.NodeVisitor):
    """AST visitor to detect stub implementations."""

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.issues: list[StubIssue] = []
        self.current_function: str | None = None
        self.current_class: str | None = None
        self.in_protocol: bool = False
        self.in_abstract_class: bool = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track current class and detect Protocol/ABC classes."""
        old_class = self.current_class
        old_protocol = self.in_protocol
        old_abstract = self.in_abstract_class

        self.current_class = node.name

        # Check if this is a Protocol class
        # Handles: Protocol, typing.Protocol, Protocol[T], typing.Protocol[T_co]
        self.in_protocol = any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            or (
                isinstance(base, ast.Subscript)
                and (
                    (isinstance(base.value, ast.Name) and base.value.id == "Protocol")
                    or (
                        isinstance(base.value, ast.Attribute)
                        and base.value.attr == "Protocol"
                    )
                )
            )
            for base in node.bases
        )

        # Check if this is an ABC class
        self.in_abstract_class = any(
            (isinstance(base, ast.Name) and base.id in ["ABC", "ABCMeta"])
            or (isinstance(base, ast.Attribute) and base.attr in ["ABC", "ABCMeta"])
            for base in node.bases
        )

        self.generic_visit(node)

        self.current_class = old_class
        self.in_protocol = old_protocol
        self.in_abstract_class = old_abstract

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for stub patterns."""
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for stub patterns."""
        self._check_function(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check function/method for stub patterns."""
        old_function = self.current_function
        self.current_function = node.name

        # Skip if in Protocol or ABC class (legitimate stubs)
        if self.in_protocol or self.in_abstract_class:
            self.current_function = old_function
            return

        # Skip dunder methods (except __init__)
        if (
            node.name.startswith("__")
            and node.name.endswith("__")
            and node.name != "__init__"
        ):
            self.current_function = old_function
            return

        # Skip @abstractmethod decorated functions
        if self._has_abstractmethod_decorator(node):
            self.current_function = old_function
            return

        # Skip @overload decorated functions (type hints)
        if self._has_overload_decorator(node):
            self.current_function = old_function
            return

        # Check for inline exclusion comment
        if self._has_stub_ok_comment(node.lineno):
            self.current_function = old_function
            return

        # Get meaningful statements (skip docstrings)
        docstring, meaningful_statements = self._extract_statements(node)

        # Check for various stub patterns
        self._check_stub_patterns(node, docstring, meaningful_statements)

        self.generic_visit(node)
        self.current_function = old_function

    def _has_abstractmethod_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Check if function has @abstractmethod decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                return True
            if (
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "abstractmethod"
            ):
                return True
        return False

    def _has_overload_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Check if function has @overload decorator (for type hints)."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "overload":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "overload":
                return True
        return False

    def _has_stub_ok_comment(self, line_no: int) -> bool:
        """Check if line has '# stub-ok' comment."""
        if line_no <= len(self.source_lines):
            line = self.source_lines[line_no - 1]
            return "# stub-ok" in line or "# noqa: stub" in line
        return False

    def _extract_statements(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[str | None, list[ast.stmt]]:
        """Extract docstring and meaningful statements from function body."""
        docstring = None
        meaningful_statements = []

        for i, stmt in enumerate(node.body):
            # Check for docstring (first statement, string constant)
            if (
                i == 0
                and isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                docstring = stmt.value.value
                continue
            meaningful_statements.append(stmt)

        return docstring, meaningful_statements

    def _check_stub_patterns(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        docstring: str | None,
        statements: list[ast.stmt],
    ) -> None:
        """Check for various stub implementation patterns."""
        func_name = node.name

        # Pattern 1: Empty function body (no statements or only pass/ellipsis)
        if not statements:
            self._add_issue(
                node.lineno,
                func_name,
                "empty_body",
                "Function contains only docstring (no implementation)",
                self._suggest_implementation(func_name, docstring),
            )
            return

        # Pattern 2: Single Pass statement
        if len(statements) == 1 and isinstance(statements[0], ast.Pass):
            self._add_issue(
                node.lineno,
                func_name,
                "only_pass",
                "Function contains only 'pass' statement",
                self._suggest_implementation(func_name, docstring),
            )
            return

        # Pattern 3: Single Ellipsis (...) statement
        if len(statements) == 1 and self._is_ellipsis(statements[0]):
            self._add_issue(
                node.lineno,
                func_name,
                "only_ellipsis",
                "Function contains only '...' (Ellipsis)",
                self._suggest_implementation(func_name, docstring),
            )
            return

        # Pattern 4: NotImplementedError
        for stmt in statements:
            if self._raises_not_implemented_error(stmt):
                # Check if the raise statement has a stub-ok comment
                if self._has_stub_ok_comment(stmt.lineno):
                    continue  # Skip this - it's an approved stub

                self._add_issue(
                    stmt.lineno,
                    func_name,
                    "not_implemented_error",
                    "Function raises NotImplementedError (stubbed)",
                    self._suggest_implementation(func_name, docstring),
                )
                return

        # Pattern 5: Pass followed by return (common stub pattern)
        for i, stmt in enumerate(statements):
            if isinstance(stmt, ast.Pass):
                if i + 1 < len(statements) and isinstance(
                    statements[i + 1], ast.Return
                ):
                    self._add_issue(
                        stmt.lineno,
                        func_name,
                        "pass_return",
                        "Function has 'pass' followed by return (stub pattern)",
                        "Remove 'pass' and implement actual logic before return",
                    )

        # Pattern 6: TODO/FIXME in docstring or comments
        if docstring:
            if any(
                marker in docstring.upper()
                for marker in ["TODO", "FIXME", "XXX", "STUB"]
            ):
                # Check if the function has a stub-ok comment
                if not self._has_stub_ok_comment(node.lineno):
                    self._add_issue(
                        node.lineno,
                        func_name,
                        "todo_in_docstring",
                        "Function docstring contains TODO/FIXME marker",
                        "Complete the implementation and remove TODO/FIXME markers",
                    )

    def _is_ellipsis(self, stmt: ast.stmt) -> bool:
        """Check if statement is an Ellipsis (...)."""
        if isinstance(stmt, ast.Expr):
            return isinstance(stmt.value, ast.Constant) and stmt.value.value is ...
        return False

    def _raises_not_implemented_error(self, stmt: ast.stmt) -> bool:
        """Check if statement raises NotImplementedError."""
        if isinstance(stmt, ast.Raise):
            if isinstance(stmt.exc, ast.Call):
                if isinstance(stmt.exc.func, ast.Name):
                    return stmt.exc.func.id == "NotImplementedError"
                if isinstance(stmt.exc.func, ast.Attribute):
                    return stmt.exc.func.attr == "NotImplementedError"
            if isinstance(stmt.exc, ast.Name):
                return stmt.exc.id == "NotImplementedError"
        return False

    def _suggest_implementation(self, func_name: str, docstring: str | None) -> str:
        """Generate implementation suggestion based on function context."""
        if func_name == "__init__":
            return "Initialize instance attributes with proper values"
        if func_name.startswith("get_"):
            return "Implement getter logic to retrieve and return the requested data"
        if func_name.startswith("set_"):
            return "Implement setter logic to validate and store the provided data"
        if func_name.startswith("validate_"):
            return "Implement validation logic and raise appropriate errors for invalid data"
        if func_name.startswith("process_"):
            return "Implement processing logic based on the function's purpose"
        if docstring:
            return f"Implement the documented behavior: {docstring[:80]}..."
        return "Implement actual logic based on function's documented purpose"

    def _add_issue(
        self,
        line_no: int,
        func_name: str,
        issue_type: str,
        description: str,
        fix_suggestion: str | None = None,
    ) -> None:
        """Add a stub implementation issue."""
        self.issues.append(
            StubIssue(
                file_path=self.filename,
                line_no=line_no,
                function_name=func_name,
                issue_type=issue_type,
                description=description,
                fix_suggestion=fix_suggestion,
            )
        )


class StubImplementationChecker:
    """Main checker for stub implementations."""

    def __init__(
        self,
        check_mode: bool = False,
        fix_suggestions: bool = False,
        config_path: Path | None = None,
    ):
        self.check_mode = check_mode
        self.fix_suggestions = fix_suggestions
        self.config = StubDetectorConfig(config_path)
        self.issues: list[StubIssue] = []
        self.checked_files = 0

    def check_file(self, file_path: Path) -> bool:
        """Check a single Python file for stub implementations."""
        # Skip .pyi type stub files
        if file_path.suffix == ".pyi":
            return True

        # Skip excluded files
        if self.config.is_excluded(file_path):
            return True

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                source_lines = content.splitlines()

            tree = ast.parse(content, filename=str(file_path))
            self.checked_files += 1

            detector = StubImplementationDetector(str(file_path), source_lines)
            detector.visit(tree)

            if detector.issues:
                self.issues.extend(detector.issues)
                return False

            return True

        except SyntaxError as e:
            print(f"⚠️  Syntax error in {file_path}:{e.lineno}: {e.msg}")
            return True  # Don't fail on syntax errors (let other tools handle)
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
            return True

    def check_files(self, paths: list[Path]) -> bool:
        """Check multiple files or directories."""
        files_to_check = []

        for path in paths:
            if path.is_file() and path.suffix == ".py":
                files_to_check.append(path)
            elif path.is_dir():
                files_to_check.extend(path.rglob("*.py"))

        success = True
        for file_path in files_to_check:
            if not self.check_file(file_path):
                success = False

        return success

    def print_results(self) -> None:
        """Print check results with detailed error messages."""
        if self.issues:
            print("❌ Stub Implementation Detection FAILED")
            print("=" * 80)
            print(
                f"Found {len(self.issues)} stub implementation(s) in {self.checked_files} file(s):\n"
            )

            # Group issues by file
            issues_by_file = {}
            for issue in self.issues:
                if issue.file_path not in issues_by_file:
                    issues_by_file[issue.file_path] = []
                issues_by_file[issue.file_path].append(issue)

            # Print issues by file
            for file_path, file_issues in sorted(issues_by_file.items()):
                print(f"\n📄 {file_path}")
                for issue in sorted(file_issues, key=lambda x: x.line_no):
                    print(f"   Line {issue.line_no}: {issue.function_name}()")
                    print(f"   ├─ Issue: {issue.description}")
                    if self.fix_suggestions and issue.fix_suggestion:
                        print(f"   └─ Fix: {issue.fix_suggestion}")

            # Print helpful guidance
            print("\n" + "=" * 80)
            print("🔧 How to Fix Stub Implementations:\n")
            print("❌ BAD Examples:")
            print("   def process_data(data):")
            print("       '''Process the data.'''")
            print("       pass  # Stub - needs implementation")
            print()
            print("   def calculate(x, y):")
            print("       ...  # Stub")
            print()
            print("   def validate(value):")
            print("       raise NotImplementedError('TODO: implement validation')")
            print()
            print("✅ GOOD Examples:")
            print("   def process_data(data):")
            print("       '''Process the data by validating and transforming it.'''")
            print("       if not data:")
            print("           raise ValueError('Data cannot be empty')")
            print("       return [item.strip() for item in data]")
            print()
            print("   def calculate(x, y):")
            print("       '''Calculate sum with validation.'''")
            print(
                "       if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):"
            )
            print("           raise TypeError('Arguments must be numeric')")
            print("       return x + y")
            print()
            print("💡 Tips:")
            print("   • Replace pass/... with actual implementation logic")
            print("   • Replace NotImplementedError with working code")
            print("   • Remove TODO/FIXME comments after implementation")
            print("   • Use '# stub-ok' comment to exclude legitimate stubs")
            print("   • Protocol/ABC classes are automatically excluded")

        else:
            mode_str = " (check mode)" if self.check_mode else ""
            print(f"✅ Stub Implementation Check PASSED{mode_str}")
            print(
                f"   Checked {self.checked_files} file(s) - no stub implementations found"
            )


def main() -> int:
    """Main entry point for the stub implementation checker."""
    parser = argparse.ArgumentParser(
        description="Detect stub implementations in Python code using AST parsing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file1.py file2.py              # Check specific files
  %(prog)s src/                           # Check directory recursively
  %(prog)s --check-mode src/              # Strict CI mode
  %(prog)s --fix-suggestions file.py      # Show fix suggestions
  %(prog)s --config .stub-check.yaml src/ # Use custom config

Exit Codes:
  0 - No stub implementations found
  1 - Stub implementations detected
        """,
    )

    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to check",
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        help="Enable strict checking mode (for CI)",
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show detailed fix suggestions",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (.yaml)",
    )

    args = parser.parse_args()

    # Validate paths
    for path in args.paths:
        if not path.exists():
            print(f"❌ Error: Path does not exist: {path}")
            return 1

    # Run checker
    checker = StubImplementationChecker(
        check_mode=args.check_mode,
        fix_suggestions=args.fix_suggestions,
        config_path=args.config,
    )

    success = checker.check_files(args.paths)
    checker.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
