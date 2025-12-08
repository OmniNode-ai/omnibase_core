#!/usr/bin/env python3
"""
Hardcoded Environment Variable Validator for ONEX Architecture

Validates that:
1. Environment variables are not hardcoded with literal values
2. All environment variable assignments use os.getenv() or os.environ
3. Configuration values come from environment or dependency injection

Common anti-patterns detected:
- DATABASE_URL = "postgresql://..." instead of os.getenv("DATABASE_URL")
- API_ENDPOINT = "https://..." instead of os.getenv("API_ENDPOINT")
- DEBUG = True instead of os.getenv("DEBUG", "false").lower() == "true"
- PORT = 8000 instead of int(os.getenv("PORT", "8000"))

Convention: Variable names in UPPER_CASE are assumed to be environment variables
and should not have hardcoded values.

Uses AST parsing for reliable detection of environment variable patterns.
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
            ...     'DATABASE_URL = "test"  # env-var-ok: test constant',
            ...     ["env-var-ok:"]
            ... )
            True
        """
        return any(pattern in line for pattern in bypass_patterns)

    @staticmethod
    def check_file_bypass(content: str, bypass_patterns: list[str]) -> bool:
        """Check if file has a bypass comment anywhere.

        Args:
            content: File content to check
            bypass_patterns: List of bypass marker patterns to search for

        Returns:
            True if file contains any bypass pattern, False otherwise

        Example:
            >>> content = "# env-var-ok: test file\nDATABASE_URL = 'test'"
            >>> BypassChecker.check_file_bypass(content, ["env-var-ok:"])
            True
        """
        return any(pattern in content for pattern in bypass_patterns)

    @staticmethod
    def extract_bypass_reason(line: str) -> str:
        """Extract the reason/justification from a bypass comment.

        Args:
            line: Line containing bypass comment

        Returns:
            The comment text after the bypass marker, or empty string if no comment

        Example:
            >>> BypassChecker.extract_bypass_reason('DATABASE_URL = "test"  # env-var-ok: test constant')
            '# env-var-ok: test constant'
        """
        if "#" not in line:
            return ""
        comment_start = line.index("#")
        return line[comment_start:].strip()


class EnvVarViolation(NamedTuple):
    """Represents a hardcoded environment variable violation."""

    file_path: str
    line_number: int
    column: int
    var_name: str
    hardcoded_value: str
    suggestion: str


# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent DoS attacks


# Bypass patterns for allowing intentional hardcoded environment variables
BYPASS_PATTERNS: Final[list[str]] = [
    "env-var-ok:",
]

# Pre-compiled regex pattern for performance (compiled once at module load)
# Typical performance improvement: 2-5x faster for repeated pattern matching
COMPILED_ENV_VAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class PythonEnvVarValidator(ast.NodeVisitor):
    """AST visitor to validate environment variables are not hardcoded."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[EnvVarViolation] = []
        self.class_stack: list[
            ast.ClassDef
        ] = []  # Track class context for Enum detection
        self.bypass_usage: list[tuple[str, int, str]] = []  # (file, line, reason)

        # Common environment variable prefixes
        self.env_var_prefixes = [
            "DATABASE_",
            "DB_",
            "REDIS_",
            "KAFKA_",
            "API_",
            "APP_",
            "SERVICE_",
            "ONEX_",
            "AWS_",
            "AZURE_",
            "GCP_",
            "GOOGLE_",
            "STRIPE_",
            "TWILIO_",
            "SENDGRID_",
            "SMTP_",
            "EMAIL_",
            "LOG_",
            "LOGGING_",
            "SENTRY_",
            "DATADOG_",
            "NEW_RELIC_",
        ]

        # Common environment variable suffixes (more precise than broad keyword matching)
        self.env_var_suffixes = [
            "_URL",
            "_URI",
            "_KEY",
            "_TOKEN",
            "_SECRET",
            "_PASSWORD",
            "_HOST",
            "_PORT",
            "_USER",
            "_USERNAME",
            "_ENDPOINT",
            "_CONNECTION",
            "_SERVERS",  # For KAFKA_BOOTSTRAP_SERVERS
            "_TOPIC",  # For KAFKA_TOPIC
            "_BUCKET",  # For AWS_BUCKET
            "_REGION",  # For AWS_REGION
        ]

        # Common environment variable names (exact matches)
        self.common_env_vars = {
            "DEBUG",
            "ENVIRONMENT",
            "ENV",
            "NODE_ENV",
            "PORT",
            "HOST",
            "HOSTNAME",
            "LOG_LEVEL",
            "WORKERS",
            "TIMEOUT",
            "MAX_CONNECTIONS",
            "POOL_SIZE",
            "BASE_URL",
            "API_URL",
            "FRONTEND_URL",
            "BACKEND_URL",
            "CORS_ORIGINS",
            "ALLOWED_HOSTS",
            "SECRET_KEY",
            "ENCRYPTION_KEY",
            "JWT_SECRET",
            "SESSION_SECRET",
            "COOKIE_SECRET",
        }

        # Exceptions - legitimate constant definitions
        self.exceptions = {
            # HTTP status codes
            "HTTP_OK",
            "HTTP_CREATED",
            "HTTP_BAD_REQUEST",
            "HTTP_UNAUTHORIZED",
            "HTTP_FORBIDDEN",
            "HTTP_NOT_FOUND",
            "HTTP_INTERNAL_ERROR",
            # Common constants
            "DEFAULT_TIMEOUT",
            "MAX_RETRIES",
            "MIN_LENGTH",
            "MAX_LENGTH",
            "DEFAULT_PORT",
            "DEFAULT_HOST",
            # Type definitions
            "TYPE_STRING",
            "TYPE_INTEGER",
            "TYPE_BOOLEAN",
            # Logging levels (when used as constants)
            "LOG_LEVEL_DEBUG",
            "LOG_LEVEL_INFO",
            "LOG_LEVEL_WARNING",
            "LOG_LEVEL_ERROR",
            "LOG_LEVEL_CRITICAL",
            # Protocol/Format constants
            "PROTOCOL_HTTP",
            "PROTOCOL_HTTPS",
            "FORMAT_JSON",
            "FORMAT_XML",
            "FORMAT_YAML",
            # Version constants
            "API_VERSION",
            "SCHEMA_VERSION",
            # Enum-like constants
            "STATUS_PENDING",
            "STATUS_ACTIVE",
            "STATUS_INACTIVE",
            "STATUS_COMPLETED",
            # Test constants
            "TEST_DATABASE_URL",
            "TEST_API_KEY",
            "TEST_USER",
            "TEST_PASSWORD",
        }

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to track Enum classes."""
        self.class_stack.append(node)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignments to detect hardcoded environment variables."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                self._check_env_var_assignment(
                    var_name, node.value, node.lineno, node.col_offset
                )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments."""
        if isinstance(node.target, ast.Name) and node.value:
            var_name = node.target.id
            self._check_env_var_assignment(
                var_name, node.value, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def _check_env_var_assignment(
        self, var_name: str, value_node: ast.AST, line_number: int, column: int
    ) -> None:
        """Check if an environment variable assignment is hardcoded."""
        # Skip if inside an Enum class
        if self._is_in_enum_class():
            return

        # Skip if not an environment variable pattern
        if not self._is_env_var_name(var_name):
            return

        # Skip exceptions
        if var_name in self.exceptions:
            return

        # Check if value is hardcoded (not from environment)
        if self._is_hardcoded_value(value_node):
            value_repr = self._get_value_repr(value_node)
            suggestion = (
                f"Use environment variable instead. "
                f"Example: {var_name} = os.getenv('{var_name}', {value_repr})"
            )

            self.violations.append(
                EnvVarViolation(
                    file_path=self.file_path,
                    line_number=line_number,
                    column=column,
                    var_name=var_name,
                    hardcoded_value=value_repr,
                    suggestion=suggestion,
                )
            )

    def _is_in_enum_class(self) -> bool:
        """Check if we're currently inside an Enum class definition."""
        for class_node in self.class_stack:
            # Check if any base class is an Enum
            for base in class_node.bases:
                base_name = ast.unparse(base)
                if (
                    "Enum" in base_name
                    or "IntEnum" in base_name
                    or "StrEnum" in base_name
                ):
                    return True
        return False

    def _is_env_var_name(self, var_name: str) -> bool:
        """Check if variable name follows environment variable naming convention.

        Uses precise heuristics to avoid false positives:
        1. Exact matches in common_env_vars (DEBUG, PORT, etc.)
        2. Known prefixes (DATABASE_, API_, AWS_, etc.)
        3. Known suffixes (_URL, _KEY, _TOKEN, etc.)

        Avoids flagging legitimate constants, enum members, and error codes.
        """
        # Must match UPPER_CASE pattern using pre-compiled regex
        if not COMPILED_ENV_VAR_PATTERN.match(var_name):
            return False

        # Check if it's a common environment variable name (exact match)
        if var_name in self.common_env_vars:
            return True

        # Check if it starts with a common environment variable prefix
        for prefix in self.env_var_prefixes:
            if var_name.startswith(prefix):
                return True

        # Check if it ends with a common environment variable suffix
        for suffix in self.env_var_suffixes:
            if var_name.endswith(suffix):
                return True

        # Not an environment variable pattern
        return False

    def _is_hardcoded_value(self, value_node: ast.AST) -> bool:
        """Check if value is hardcoded (not from environment or config)."""
        # Constants are hardcoded
        if isinstance(value_node, ast.Constant):
            # Ignore None values (these are placeholders)
            if value_node.value is None:
                return False
            return True

        # Lists, dicts, sets are hardcoded
        if isinstance(value_node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
            return True

        # Safe patterns - environment variable access
        if isinstance(value_node, ast.Call):
            func_name = self._get_call_func_name(value_node.func)
            # os.getenv(), os.environ.get(), config.get(), etc.
            safe_funcs = [
                "getenv",
                "os.getenv",
                "environ.get",
                "os.environ.get",
                "get_service",
                "get",
                "get_config",
                "load_config",
            ]
            if func_name in safe_funcs:
                return False

        # Subscript for environ["KEY"] or config["KEY"]
        if isinstance(value_node, ast.Subscript):
            if isinstance(value_node.value, ast.Attribute):
                # os.environ["KEY"]
                if value_node.value.attr in ["environ", "config"]:
                    return False
            if isinstance(value_node.value, ast.Name):
                # environ["KEY"] or config["KEY"]
                if value_node.value.id in ["environ", "config"]:
                    return False

        # Attribute access for config values
        if isinstance(value_node, ast.Attribute):
            # config.DATABASE_URL
            if isinstance(value_node.value, ast.Name):
                if value_node.value.id in ["config", "settings", "env"]:
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

    def _get_value_repr(self, value_node: ast.AST) -> str:
        """Get a string representation of the value."""
        if isinstance(value_node, ast.Constant):
            if isinstance(value_node.value, str):
                return f'"{value_node.value}"'
            return str(value_node.value)
        elif isinstance(value_node, ast.List):
            return "[...]"
        elif isinstance(value_node, ast.Dict) or isinstance(value_node, ast.Set):
            return "{...}"
        else:
            try:
                return ast.unparse(value_node)
            except AttributeError:
                return "<value>"


class HardcodedEnvVarValidator:
    """Validates that Python files don't contain hardcoded environment variables."""

    def __init__(self) -> None:
        self.violations: list[EnvVarViolation] = []
        self.checked_files = 0
        self.bypass_usage: list[tuple[str, int, str]] = []  # (file, line, reason)

    def validate_python_file(self, python_path: Path) -> bool:
        """Validate a Python file for hardcoded environment variables."""
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

        # Check for bypass comments using BypassChecker
        if BypassChecker.check_file_bypass(content, BYPASS_PATTERNS):
            # Track file-level bypass
            reason = "# env-var-ok: (file-level bypass)"
            for line_num, line in enumerate(content.split("\n"), 1):
                if any(pattern in line for pattern in BYPASS_PATTERNS):
                    reason = BypassChecker.extract_bypass_reason(line)
                    self.bypass_usage.append((str(python_path), line_num, reason))
                    break
            return True

        self.checked_files += 1

        # AST-based validation for hardcoded environment variables
        ast_validator = PythonEnvVarValidator(str(python_path))
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

    def print_results(self) -> None:
        """Print validation results."""
        if self.violations:
            print("❌ Hardcoded Environment Variable Validation FAILED")
            print("=" * 80)
            print(
                f"Found {len(self.violations)} hardcoded environment variables in {self.checked_files} files:"
            )
            print()

            # Group by file
            by_file: dict[str, list[EnvVarViolation]] = {}
            for violation in self.violations:
                if violation.file_path not in by_file:
                    by_file[violation.file_path] = []
                by_file[violation.file_path].append(violation)

            for file_path, file_violations in by_file.items():
                print(f"📁 {file_path}")
                for violation in file_violations:
                    print(
                        f"  ⚠️  Line {violation.line_number}:{violation.column} - "
                        f"'{violation.var_name}' is hardcoded to {violation.hardcoded_value}"
                    )
                    print(f"      💡 {violation.suggestion}")
                print()

            print("🔧 How to fix:")
            print("   1. Use os.getenv() for environment variables:")
            print('      Example: DATABASE_URL = os.getenv("DATABASE_URL")')
            print("   2. Provide default values when appropriate:")
            print('      Example: PORT = int(os.getenv("PORT", "8000"))')
            print("   3. For booleans, parse string values:")
            print(
                '      Example: DEBUG = os.getenv("DEBUG", "false").lower() == "true"'
            )
            print("   4. For constants, use lowercase names:")
            print("      Example: default_timeout = 30  # Not DEFAULT_TIMEOUT = 30")
            print("   5. Add bypass comment if intentional:")
            print("      Example: # env-var-ok: constant definition")
            print()
        else:
            print(
                f"✅ Hardcoded Environment Variable Validation PASSED ({self.checked_files} files checked)"
            )

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
            description="Validate Python files for hardcoded environment variables"
        )
        parser.add_argument("files", nargs="+", help="Python files to validate")
        parser.add_argument(
            "--report-bypasses",
            action="store_true",
            help="Report all bypass comment usage",
        )
        args = parser.parse_args()

        validator = HardcodedEnvVarValidator()
        file_paths = [Path(f) for f in args.files]

        # Filter to only Python files
        python_files = [f for f in file_paths if f.suffix == ".py"]

        if not python_files:
            print(
                "✅ Hardcoded Environment Variable Validation PASSED (no Python files to check)"
            )
            return 0

        success = True
        for python_path in python_files:
            if not validator.validate_python_file(python_path):
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
