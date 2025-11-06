#!/usr/bin/env python3
"""
Secret Detection Validator for ONEX Architecture

Validates that:
1. No hardcoded secrets (passwords, API keys, tokens) exist in Python files
2. All secrets are properly stored in .env files
3. Code uses environment variables or secure configuration instead of hardcoded values

Common secret patterns detected:
- API keys (api_key, API_KEY)
- Passwords (password, PASSWORD, pwd)
- Tokens (token, TOKEN, auth_token, access_token)
- Connection strings (connection_string, DATABASE_URL)
- AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- Generic secrets (secret, SECRET)

Uses AST parsing for reliable detection of secret patterns and their values.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path
from typing import Final, NamedTuple


class BypassChecker:
    """Unified bypass comment detection for security validators.

    Provides consistent bypass checking across all security validation tools.
    Supports both file-level bypasses (anywhere in file) and line-level
    bypasses (inline with specific violations).
    """

    @staticmethod
    def check_line_bypass(line: str, bypass_patterns: list[str]) -> bool:
        """Check if a specific line has an inline bypass comment.

        Args:
            line: The line of code to check
            bypass_patterns: List of bypass marker patterns to search for

        Returns:
            True if line contains any bypass pattern, False otherwise

        Example:
            >>> BypassChecker.check_line_bypass(
            ...     'password = "test"  # secret-ok: test fixture',
            ...     ["secret-ok:", "nosec"]
            ... )
            True
        """
        return any(pattern in line for pattern in bypass_patterns)

    @staticmethod
    def check_file_bypass(
        content_lines: list[str], bypass_patterns: list[str], max_lines: int = 10
    ) -> bool:
        """Check if file has a bypass comment in the header.

        Args:
            content_lines: Lines of the file to check
            bypass_patterns: List of bypass marker patterns to search for
            max_lines: Maximum number of lines to check from file start (default: 10)

        Returns:
            True if file header contains any bypass pattern, False otherwise

        Example:
            >>> lines = ["# secret-ok: test file", "password = 'test'"]
            >>> BypassChecker.check_file_bypass(lines, ["secret-ok:"])
            True
        """
        # Check first N lines for bypass comment
        for line in content_lines[:max_lines]:
            stripped = line.strip()
            if stripped.startswith("#"):
                if any(pattern in line for pattern in bypass_patterns):
                    return True
        return False

    @staticmethod
    def extract_bypass_reason(line: str) -> str:
        """Extract the reason/justification from a bypass comment.

        Args:
            line: Line containing bypass comment

        Returns:
            The comment text after the bypass marker, or empty string if no comment

        Example:
            >>> BypassChecker.extract_bypass_reason('password = "test"  # secret-ok: test fixture')
            '# secret-ok: test fixture'
        """
        if "#" not in line:
            return ""
        comment_start = line.index("#")
        return line[comment_start:].strip()


class SecretViolation(NamedTuple):
    """Represents a secret detection violation."""

    file_path: str
    line_number: int
    column: int
    secret_name: str
    violation_type: str
    suggestion: str


# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent DoS attacks
VALIDATION_TIMEOUT = 600  # 10 minutes


# Bypass patterns for allowing intentional hardcoded secrets (e.g., test fixtures)
BYPASS_PATTERNS: Final[list[str]] = [
    "secret-ok:",
    "password-ok:",
    "hardcoded-ok:",
    "nosec",  # Common security scanner bypass
    "noqa: secrets",  # Another common bypass pattern
]

# Pre-compiled regex patterns for performance (compiled once at module load)
# Typical performance improvement: 2-5x faster for repeated pattern matching
COMPILED_SECRET_PATTERNS: Final[list[re.Pattern[str]]] = [
    # API Keys
    re.compile(r".*api[_-]?key.*", re.IGNORECASE),
    re.compile(r".*apikey.*", re.IGNORECASE),
    # Passwords
    re.compile(r".*password.*", re.IGNORECASE),
    re.compile(r".*passwd.*", re.IGNORECASE),
    re.compile(r".*pwd.*", re.IGNORECASE),
    # Tokens
    re.compile(r".*token.*", re.IGNORECASE),
    re.compile(r".*auth.*token.*", re.IGNORECASE),
    re.compile(r".*access.*token.*", re.IGNORECASE),
    re.compile(r".*refresh.*token.*", re.IGNORECASE),
    re.compile(r".*bearer.*", re.IGNORECASE),
    # AWS Credentials
    re.compile(r".*aws.*access.*key.*", re.IGNORECASE),
    re.compile(r".*aws.*secret.*key.*", re.IGNORECASE),
    re.compile(r".*aws.*session.*token.*", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID pattern
    # Database & Connection Strings
    re.compile(r".*connection.*string.*", re.IGNORECASE),
    re.compile(r".*database.*url.*", re.IGNORECASE),
    re.compile(r".*db.*url.*", re.IGNORECASE),
    re.compile(r".*dsn.*", re.IGNORECASE),
    # Generic Secrets
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*private.*key.*", re.IGNORECASE),
    re.compile(r".*encryption.*key.*", re.IGNORECASE),
    re.compile(r".*signing.*key.*", re.IGNORECASE),
    # OAuth & Authentication
    re.compile(r".*client.*secret.*", re.IGNORECASE),
    re.compile(r".*consumer.*secret.*", re.IGNORECASE),
    re.compile(r".*app.*secret.*", re.IGNORECASE),
    # SSH & Keys
    re.compile(r".*ssh.*key.*", re.IGNORECASE),
    re.compile(r".*rsa.*key.*", re.IGNORECASE),
    # Certificate & TLS
    re.compile(r".*certificate.*", re.IGNORECASE),
    re.compile(r".*cert.*key.*", re.IGNORECASE),
    re.compile(r".*tls.*key.*", re.IGNORECASE),
]

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class PythonSecretValidator(ast.NodeVisitor):
    """AST visitor to validate secrets are not hardcoded in Python files."""

    def __init__(self, file_path: str, file_lines: list[str] | None = None):
        self.file_path = file_path
        self.violations: list[SecretViolation] = []
        self.file_lines = file_lines or []
        self.class_stack: list[ast.ClassDef] = []  # Track class definition context
        self.bypass_usage: list[tuple[str, int, str]] = []  # (file, line, reason)

        # Exception patterns - legitimate use cases that shouldn't be flagged
        self.exceptions = {
            # Variable names (not values)
            "password_field",
            "password_validator",
            "password_hash",
            "password_pattern",
            "password_regex",
            "token_type",
            "token_validator",
            "secret_name",
            "secret_type",
            "api_key_name",
            # Documentation & examples
            "example_password",
            "sample_password",
            "test_password",
            "dummy_password",
            "fake_password",
            # Configuration keys (not values)
            "password_min_length",
            "password_max_length",
            "token_expiry",
            "token_lifetime",
            "secret_length",
            # Type hints & protocols
            "password_type",
            # Metadata
            "password_updated_at",
            "password_created_at",
            "token_created_at",
            # Logging & errors
            "password_error",
            "token_error",
            "secret_error",
        }

        # Metadata patterns - recognize configuration/metadata assignments
        # Maps variable name patterns to valid metadata values
        self.metadata_patterns = {
            "password_strength": [
                "weak",
                "very_weak",
                "medium",
                "moderate",
                "strong",
                "very_strong",
            ],
            "secret_rotation": [
                "manual",
                "automatic",
                "disabled",
                "manual_or_operator",
            ],
            "auth_type": ["bearer", "api_key", "oauth", "basic", "none"],
            "token_type": ["bearer", "refresh", "access", "id_token"],
            "api_key": ["api_key"],  # Enum value pattern
            "bearer": ["bearer"],  # Enum value pattern
            "password": ["password"],  # Enum value pattern (when used in enum context)
            "secret": ["secret"],  # Enum value pattern (when used in enum context)
        }

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions to detect Enum contexts."""
        self.class_stack.append(node)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignments to detect hardcoded secrets."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                field_name = target.id
                self._check_secret_assignment(
                    field_name, node.value, node.lineno, node.col_offset
                )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments (field definitions with values)."""
        if isinstance(node.target, ast.Name) and node.value:
            field_name = node.target.id
            self._check_secret_assignment(
                field_name, node.value, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        """Visit keyword arguments in function calls."""
        if node.arg:
            self._check_secret_assignment(
                node.arg, node.value, node.value.lineno, node.value.col_offset
            )
        self.generic_visit(node)

    def _is_in_enum_class(self) -> bool:
        """Check if current assignment is inside an Enum class definition."""
        for class_node in self.class_stack:
            for base in class_node.bases:
                # Check if any base class contains "Enum" in its name
                if isinstance(base, ast.Name) and "Enum" in base.id:
                    return True
                # Handle qualified names like enum.Enum
                if isinstance(base, ast.Attribute) and "Enum" in base.attr:
                    return True
        return False

    def _is_metadata_assignment(self, var_name: str, value: str) -> bool:
        """Check if assignment is metadata (configuration), not an actual secret."""
        var_lower = var_name.lower()
        value_lower = value.lower()

        # Check against known metadata patterns
        for pattern, valid_values in self.metadata_patterns.items():
            if pattern in var_lower:
                if value_lower in valid_values:
                    return True

        return False

    def _has_inline_bypass(self, line_number: int) -> bool:
        """Check if line has an inline bypass comment.

        Uses BypassChecker for consistent bypass detection across validators.
        Tracks bypass usage for reporting.
        """
        if not self.file_lines or line_number < 1 or line_number > len(self.file_lines):
            return False

        line = self.file_lines[line_number - 1]
        is_bypass = BypassChecker.check_line_bypass(line, BYPASS_PATTERNS)

        if is_bypass:
            reason = BypassChecker.extract_bypass_reason(line)
            self.bypass_usage.append((self.file_path, line_number, reason))

        return is_bypass

    def _check_secret_assignment(
        self, field_name: str, value_node: ast.AST, line_number: int, column: int
    ) -> None:
        """Check if a field assignment contains a hardcoded secret."""
        # Skip exceptions
        if field_name.lower() in self.exceptions:
            return

        # Check if field name matches secret patterns
        if not self._matches_secret_patterns(field_name):
            return

        # Check if we're inside an Enum class - skip enum members
        if self._is_in_enum_class():
            return

        # Check for inline bypass comment
        if self._has_inline_bypass(line_number):
            return

        # Check if value is a hardcoded string (not an environment variable lookup)
        if self._is_hardcoded_value(value_node):
            # Extract the actual value for metadata check
            value_str = ""
            if isinstance(value_node, ast.Constant) and isinstance(
                value_node.value, str
            ):
                value_str = value_node.value

            # Check if this is a metadata assignment (not actual secret)
            if value_str and self._is_metadata_assignment(field_name, value_str):
                return

            suggestion = (
                f"Use environment variable or secure configuration instead. "
                f"Example: os.getenv('{field_name.upper()}') or container.get_service('ProtocolConfig')"
            )

            self.violations.append(
                SecretViolation(
                    file_path=self.file_path,
                    line_number=line_number,
                    column=column,
                    secret_name=field_name,
                    violation_type="hardcoded_secret",
                    suggestion=suggestion,
                )
            )

    def _matches_secret_patterns(self, field_name: str) -> bool:
        """Check if field name matches any secret pattern using pre-compiled patterns."""
        return any(pattern.match(field_name) for pattern in COMPILED_SECRET_PATTERNS)

    def _is_hardcoded_value(self, value_node: ast.AST) -> bool:
        """Check if value is a hardcoded string (not from environment or config)."""
        # String constants are hardcoded
        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            # Ignore empty strings and placeholder patterns
            value = value_node.value
            if not value or value in ["", "YOUR_KEY_HERE", "CHANGEME", "TODO"]:
                return False
            # Ignore very short strings (< 3 chars) - likely not real secrets
            if len(value) < 3:
                return False
            return True

        # JoinedStr (f-strings) might contain hardcoded secrets
        if isinstance(value_node, ast.JoinedStr):
            # Check if it contains any hardcoded values
            for joined_value in value_node.values:
                if isinstance(joined_value, ast.Constant) and isinstance(
                    joined_value.value, str
                ):
                    if len(joined_value.value) >= 3:
                        return True

        # Safe patterns - environment variable access
        if isinstance(value_node, ast.Call):
            func_name = self._get_call_func_name(value_node.func)
            # os.getenv(), os.environ.get(), config.get_service()
            if func_name in [
                "getenv",
                "os.getenv",
                "environ.get",
                "os.environ.get",
                "get_service",
                "get",
            ]:
                return False

        # Subscript for environ["KEY"]
        if isinstance(value_node, ast.Subscript):
            if isinstance(value_node.value, ast.Attribute):
                # os.environ["KEY"]
                if value_node.value.attr == "environ":
                    return False
            if isinstance(value_node.value, ast.Name):
                # environ["KEY"]
                if value_node.value.id == "environ":
                    return False

        return False

    def _get_call_func_name(self, func_node: ast.AST) -> str:
        """Extract the function name from a call node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            # Handle os.getenv pattern
            if isinstance(func_node.value, ast.Name):
                return f"{func_node.value.id}.{func_node.attr}"
            elif isinstance(func_node.value, ast.Attribute):
                # Handle os.environ.get pattern
                if isinstance(func_node.value.value, ast.Name):
                    return f"{func_node.value.attr}.{func_node.attr}"
            return func_node.attr
        return ""


class SecretValidator:
    """Validates that Python files don't contain hardcoded secrets."""

    def __init__(self) -> None:
        self.violations: list[SecretViolation] = []
        self.checked_files = 0
        self.bypass_usage: list[tuple[str, int, str]] = []  # (file, line, reason)

    def validate_python_file(self, python_path: Path, content_lines: list[str]) -> bool:
        """Validate a Python file for hardcoded secrets."""
        # Check file existence and basic properties
        if not python_path.exists():
            return True  # Skip non-existent files

        if not python_path.is_file():
            return True  # Skip non-files

        # Check file permissions
        if not os.access(python_path, os.R_OK):
            print(f"Warning: Cannot read file: {python_path}")
            return True

        # Check file size to prevent DoS attacks
        try:
            file_size = python_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                print(
                    f"Warning: File too large ({file_size} bytes), max allowed: {MAX_FILE_SIZE}"
                )
                return True
        except OSError:
            return True

        # Read file content with proper error handling
        try:
            with open(python_path, encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError, OSError):
            return True  # Skip files we can't read

        # Skip empty files
        if not content.strip():
            return True

        # Check for bypass comments
        if self._has_bypass_comment(content_lines):
            return True

        self.checked_files += 1

        # AST-based validation for hardcoded secrets
        # Pass file_lines to enable inline bypass comment detection
        ast_validator = PythonSecretValidator(str(python_path), content_lines)
        try:
            tree = ast.parse(content, filename=str(python_path))
            ast_validator.visit(tree)

            # Add AST violations to our list
            self.violations.extend(ast_validator.violations)
            # Collect bypass usage for reporting
            self.bypass_usage.extend(ast_validator.bypass_usage)

        except SyntaxError:
            # Skip files with syntax errors - they'll be caught by other tools
            pass
        except Exception as e:
            print(f"Warning: Error during AST validation of {python_path}: {e}")

        return len(ast_validator.violations) == 0

    def _has_bypass_comment(self, content_lines: list[str]) -> bool:
        """Check if file has a bypass comment at the top.

        Uses BypassChecker for consistent bypass detection across validators.
        """
        return BypassChecker.check_file_bypass(content_lines, BYPASS_PATTERNS)

    def print_results(self) -> None:
        """Print validation results."""
        if self.violations:
            print("❌ Secret Validation FAILED")
            print("=" * 80)
            print(
                f"Found {len(self.violations)} hardcoded secrets in {self.checked_files} files:"
            )
            print()

            # Group by file
            by_file: dict[str, list[SecretViolation]] = {}
            for violation in self.violations:
                if violation.file_path not in by_file:
                    by_file[violation.file_path] = []
                by_file[violation.file_path].append(violation)

            for file_path, file_violations in by_file.items():
                print(f"📁 {file_path}")
                for violation in file_violations:
                    print(
                        f"  🔐 Line {violation.line_number}:{violation.column} - "
                        f"Secret '{violation.secret_name}' is hardcoded"
                    )
                    print(f"      💡 {violation.suggestion}")
                print()

            print("🔧 How to fix:")
            print("   1. Move secrets to .env file:")
            print("      Example: API_KEY=your_secret_key")
            print("   2. Load from environment in code:")
            print("      Example: api_key = os.getenv('API_KEY')")
            print("   3. Or use dependency injection:")
            print("      Example: config = container.get_service('ProtocolConfig')")
            print("   4. For test fixtures, add bypass comment:")
            print("      Example: # secret-ok: test fixture")
            print("   5. Or use inline bypass:")
            print("      Example: password = 'test'  # noqa: secrets")
            print()
        else:
            print(f"✅ Secret Validation PASSED ({self.checked_files} files checked)")

    def print_bypass_report(self) -> None:
        """Print report of bypass comment usage."""
        if not self.bypass_usage:
            print("\n📊 Bypass Usage Report: No bypasses used")
            return

        print(f"\n📊 Bypass Usage Report: {len(self.bypass_usage)} bypass(es) found")
        print("=" * 80)

        for file_path, line_num, reason in sorted(self.bypass_usage):
            print(f"  {file_path}:{line_num}")
            print(f"    → {reason}")

        print("=" * 80)


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        import argparse

        parser = argparse.ArgumentParser(
            description="Validate Python files for hardcoded secrets"
        )
        parser.add_argument("files", nargs="+", help="Python files to validate")
        parser.add_argument(
            "--report-bypasses",
            action="store_true",
            help="Report all bypass comment usage",
        )
        args = parser.parse_args()

        validator = SecretValidator()
        file_paths = [Path(f) for f in args.files]

        # Filter to only Python files
        python_files = [f for f in file_paths if f.suffix == ".py"]

        if not python_files:
            print("✅ Secret Validation PASSED (no Python files to check)")
            return 0

        success = True
        for python_path in python_files:
            # Read file lines for bypass comment check
            try:
                with open(python_path, encoding="utf-8") as f:
                    content_lines = f.readlines()
            except (UnicodeDecodeError, PermissionError, OSError):
                content_lines = []

            if not validator.validate_python_file(python_path, content_lines):
                success = False

        validator.print_results()

        # Print bypass report if requested or if validation failed
        if args.report_bypasses or not success:
            validator.print_bypass_report()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\nError: Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error in main function: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
