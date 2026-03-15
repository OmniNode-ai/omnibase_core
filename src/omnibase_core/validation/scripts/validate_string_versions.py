#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Comprehensive ID and Version Validation Hook for ONEX Architecture.

Validates that:
1. Contract YAML files use proper ModelSemVer format instead of string versions
2. Python __init__.py files do not contain hardcoded __version__ strings
3. Python models use UUID instead of str for ID fields
4. Python models use ModelSemVer instead of str for version fields

String versions like "1.0.0" should be ModelSemVer format like {major: 1, minor: 0, patch: 0}.
Versions should only come from contracts, never from __init__.py files.
ID fields should use UUID type instead of str for proper type safety.

Uses AST parsing for reliable detection of semantic version and ID patterns.
This prevents runtime issues and ensures proper type compliance.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.validation.scripts import timeout_utils
from omnibase_core.validation.scripts.python_ast_validator import PythonASTValidator
from omnibase_core.validation.scripts.timeout_utils import timeout_context
from omnibase_core.validation.scripts.validation_violation import ValidationViolation

__all__ = ["StringVersionValidator", "ValidationViolation", "PythonASTValidator"]

# Constants
MAX_PYTHON_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent DoS attacks on Python files
MAX_YAML_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks on YAML files
DIRECTORY_SCAN_TIMEOUT = 30  # seconds
VALIDATION_TIMEOUT = 600  # 10 minutes

# Exclusion patterns for validation (shared between directory and individual file modes)
#
# MATCHING BEHAVIOR:
# - Path component matching: Pattern is checked against each directory/file in the path
#   (e.g., "tests" matches any file under a "tests" directory)
# - Filename prefix matching: Pattern is checked with startswith() against the filename
#   (e.g., "ci-cd" matches "ci-cd.yml" but not "my-ci-cd.yml")
#
# EXCLUSION RATIONALE:
# - protocols: Protocol files define interfaces/type stubs that may reference version
#   formats in docstrings and type hints for documentation purposes. These are abstract
#   interfaces, not runtime implementations, so the string version anti-pattern doesn't apply.
# - tests: Test files may contain version strings as test data
# - archive, archived: Legacy code not subject to current standards
# - deployment, .github, kubernetes, etc.: CI/CD and deployment configs use string versions by convention
EXCLUDE_PATTERNS = [
    "deployment",
    ".github",
    "docker-compose",
    "prometheus",
    "alerts.yml",
    "grafana",
    "kubernetes",
    "ci-cd.yml",  # Generic CI/CD configuration file (e.g., ci-cd.yml, ci-cd-*.yml)
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "archive",  # Exclude archived code
    "archived",  # Exclude archived code (alternative naming)
    "tests",  # Exclude test files
    "examples",  # Exclude examples - may contain demonstration code with various version formats
    "protocols",  # Exclude Protocol classes (see rationale above)
    "hooks",  # Exclude hook models - types match external API contracts (e.g., Claude Code session_id is str)
]


def should_exclude_file(file_path: Path, verbose: bool = False) -> bool:
    """
    Check if a file should be excluded from validation based on EXCLUDE_PATTERNS.

    Args:
        file_path: Path to the file to check
        verbose: If True, print reason for exclusion

    Returns:
        True if the file should be excluded, False otherwise
    """
    path_parts = file_path.parts
    file_name = file_path.name

    for pattern in EXCLUDE_PATTERNS:
        # Check if any path component matches the pattern
        if pattern in path_parts:
            if verbose:
                print(f"Skipping (excluded): {file_path} (path contains '{pattern}')")
            return True
        # Check if filename starts with the pattern
        if file_name.startswith(pattern):
            if verbose:
                print(
                    f"Skipping (excluded): {file_path} (filename starts with '{pattern}')"
                )
            return True

    return False


# Try to import Pydantic models if available
try:
    from omnibase_core.core.model_generic_yaml import ModelGenericYaml
    from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

    PYDANTIC_MODELS_AVAILABLE = True
except ImportError:
    ModelGenericYaml = None
    load_yaml_content_as_model = None  # type: ignore[assignment]
    PYDANTIC_MODELS_AVAILABLE = False


class StringVersionValidator:
    """Validates that YAML contract files don't use string versions and Python files use proper ID/version types."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.ast_violations: list[ValidationViolation] = []
        self.checked_files = 0

    def validate_python_file(self, python_path: Path) -> bool:
        """Validate a Python file for hardcoded __version__ strings."""
        # Check file existence and basic properties
        if not python_path.exists():
            self.errors.append(f"{python_path}: File does not exist")
            return False

        if not python_path.is_file():
            self.errors.append(f"{python_path}: Path is not a regular file")
            return False

        # Check file permissions
        if not os.access(python_path, os.R_OK):
            self.errors.append(f"{python_path}: Permission denied - cannot read file")
            return False

        # Check file size to prevent DoS attacks
        try:
            file_size = python_path.stat().st_size
            if file_size > MAX_PYTHON_FILE_SIZE:
                self.errors.append(
                    f"{python_path}: File too large ({file_size} bytes), max allowed: {MAX_PYTHON_FILE_SIZE}"
                )
                return False
        except OSError as e:
            self.errors.append(f"{python_path}: Cannot check file size: {e}")
            return False

        # Read file content with proper error handling
        try:
            with open(python_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            self.errors.append(f"{python_path}: File encoding error - {e}")
            return False
        except PermissionError as e:
            self.errors.append(f"{python_path}: Permission denied - {e}")
            return False
        except OSError as e:
            self.errors.append(f"{python_path}: OS/IO error reading file - {e}")
            return False

        # Skip empty files
        if not content.strip():
            return True

        self.checked_files += 1
        file_errors: list[str] = []

        # Check for __version__ declarations with error handling
        try:
            self._validate_python_version_declarations(
                content, python_path, file_errors
            )
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: pre-commit hook accumulates errors then exits with code
            self.errors.append(f"{python_path}: Error during content validation - {e}")
            return False

        # AST-based validation for ID and version field types
        try:
            tree = ast.parse(content, filename=str(python_path))
            # Pass source lines to enable inline comment bypass checking
            source_lines = content.splitlines()
            ast_validator = PythonASTValidator(str(python_path), source_lines)
            ast_validator.visit(tree)

            # Add AST violations to our list
            self.ast_violations.extend(ast_validator.violations)

        except SyntaxError as e:
            # Skip files with syntax errors - they'll be caught by other tools
            pass
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: pre-commit hook accumulates errors then exits with code
            self.errors.append(f"{python_path}: Error during AST validation - {e}")
            return False

        if file_errors:
            self.errors.extend([f"{python_path}: {error}" for error in file_errors])
            return False

        return True

    def _validate_python_version_declarations(
        self,
        content: str,
        python_path: Path,
        errors: list[str],
    ) -> None:
        """Check Python content for hardcoded __version__ declarations.

        In __init__.py files, ANY hardcoded string literal assigned to __version__
        is always an error, regardless of bypass markers. The correct pattern is:
            from importlib.metadata import version
            __version__ = version("package-name")

        In non-__init__.py files, the original behavior applies: only semver-like
        strings are flagged, and bypass markers (string-version-ok, version-ok,
        semver-ok) suppress the error.
        """
        lines = content.splitlines()
        is_init_file = python_path.name == "__init__.py"

        # Track bypass comments
        bypass_patterns = [
            "string-version-ok:",
            "version-ok:",
            "semver-ok:",
        ]

        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()

            # Skip comments and empty lines
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Check for __version__ declarations
            if "__version__" in stripped_line and "=" in stripped_line:
                # Extract the assignment
                if stripped_line.startswith("__version__"):
                    assignment_part = stripped_line.split("=", 1)[1].strip()

                    # For __init__.py files: block ANY hardcoded string literal,
                    # bypass markers are not honored (OMN-3832)
                    if is_init_file:
                        # Check if the value is a string literal (quoted)
                        if (
                            assignment_part.startswith('"')
                            and assignment_part.endswith('"')
                        ) or (
                            assignment_part.startswith("'")
                            and assignment_part.endswith("'")
                        ):
                            clean_value = assignment_part.strip("\"'")
                            errors.append(
                                f'Line {line_num}: __version__ = "{clean_value}" is a hardcoded '
                                f"string literal in __init__.py - use "
                                f'importlib.metadata.version("package-name") instead. '
                                f"Bypass markers are not honored in __init__.py files."
                            )
                        # Also check for inline string after comment stripping
                        # e.g. __version__ = "1.0.0"  # string-version-ok: reason
                        elif "#" in assignment_part:
                            code_part = assignment_part.split("#", 1)[0].strip()
                            if (
                                code_part.startswith('"') and code_part.endswith('"')
                            ) or (
                                code_part.startswith("'") and code_part.endswith("'")
                            ):
                                clean_value = code_part.strip("\"'")
                                errors.append(
                                    f'Line {line_num}: __version__ = "{clean_value}" is a hardcoded '
                                    f"string literal in __init__.py - use "
                                    f'importlib.metadata.version("package-name") instead. '
                                    f"Bypass markers are not honored in __init__.py files."
                                )
                        continue

                    # For non-__init__.py files: original behavior
                    # Check for bypass comment on previous line or same line
                    has_bypass = False

                    # Check previous line for bypass comment
                    if line_num > 1:
                        prev_line = lines[line_num - 2].strip()
                        if prev_line.startswith("#"):
                            for pattern in bypass_patterns:
                                if pattern in prev_line:
                                    has_bypass = True
                                    break

                    # Check current line for inline bypass comment
                    if "#" in line:
                        comment_part = line.split("#", 1)[1]
                        for pattern in bypass_patterns:
                            if pattern in comment_part:
                                has_bypass = True
                                break

                    # Skip if bypass comment found
                    if has_bypass:
                        continue

                    # Remove quotes and check if it's a version string
                    clean_value = assignment_part.strip().strip("\"'")

                    if self._is_semantic_version_ast(clean_value):
                        errors.append(
                            f"Line {line_num}: __version__ uses hardcoded string '{clean_value}' - "
                            f"versions should only come from contracts, not __init__.py files"
                        )

    def validate_yaml_file(self, yaml_path: Path) -> bool:
        """Validate a single YAML file for string version usage."""
        # Check file existence and basic properties
        if not yaml_path.exists():
            self.errors.append(f"{yaml_path}: File does not exist")
            return False

        if not yaml_path.is_file():
            self.errors.append(f"{yaml_path}: Path is not a regular file")
            return False

        # Check file permissions
        if not os.access(yaml_path, os.R_OK):
            self.errors.append(f"{yaml_path}: Permission denied - cannot read file")
            return False

        # Check file size to prevent DoS attacks
        try:
            file_size = yaml_path.stat().st_size
            if file_size > MAX_YAML_FILE_SIZE:
                self.errors.append(
                    f"{yaml_path}: File too large ({file_size} bytes), max allowed: {MAX_YAML_FILE_SIZE}"
                )
                return False
        except OSError as e:
            self.errors.append(f"{yaml_path}: Cannot check file size: {e}")
            return False

        # Read file content with proper error handling
        try:
            with open(yaml_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            self.errors.append(f"{yaml_path}: File encoding error - {e}")
            return False
        except PermissionError as e:
            self.errors.append(f"{yaml_path}: Permission denied - {e}")
            return False
        except OSError as e:
            self.errors.append(f"{yaml_path}: OS/IO error reading file - {e}")
            return False

        # Skip empty files
        if not content.strip():
            return True

        # Parse YAML using Pydantic model validation if available
        yaml_data = None
        if PYDANTIC_MODELS_AVAILABLE and load_yaml_content_as_model is not None:
            try:
                yaml_model = load_yaml_content_as_model(content, ModelGenericYaml)
                yaml_data = yaml_model.model_dump()
            except Exception as e:  # noqa: BLE001
                # If we can't parse with Pydantic, log it but continue with AST validation
                # This is not a fatal error since we have fallback validation
                pass

        # Basic YAML syntax validation
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            self.errors.append(f"{yaml_path}: Invalid YAML syntax - {e}")
            return False
        except MemoryError:
            self.errors.append(f"{yaml_path}: YAML file too large to parse in memory")
            return False

        self.checked_files += 1
        file_errors: list[str] = []

        # Use AST-based validation on the raw content (always runs)
        try:
            self._validate_yaml_content_ast(content, yaml_path, file_errors)
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: pre-commit hook accumulates errors then exits with code
            self.errors.append(f"{yaml_path}: Error during AST validation - {e}")
            return False

        # Also validate the parsed structure if we have it
        if yaml_data:
            try:
                self._validate_parsed_yaml(yaml_data, file_errors)
            except Exception as e:  # noqa: BLE001  # fallback-ok: pre-commit hook accumulates errors then exits with code
                self.errors.append(
                    f"{yaml_path}: Error during parsed YAML validation - {e}"
                )
                return False

        if file_errors:
            self.errors.extend([f"{yaml_path}: {error}" for error in file_errors])
            return False

        return True

    def _validate_yaml_content_ast(
        self,
        content: str,
        yaml_path: Path,
        errors: list[str],
    ) -> None:
        """Use AST-like parsing to detect string versions in YAML content."""
        lines = content.splitlines()

        version_field_patterns = [
            "version:",
            "contract_version:",
            "node_version:",
            "onex_compliance_version:",
            "protocol_version:",
        ]

        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()

            # Skip comments and empty lines
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Check for version field patterns
            for pattern in version_field_patterns:
                if pattern in stripped_line:
                    # Extract the value after the colon
                    if ":" in stripped_line:
                        field_name = stripped_line.split(":")[0].strip()
                        value_part = ":".join(stripped_line.split(":")[1:]).strip()

                        # Remove quotes and check if it's a version string
                        clean_value = value_part.strip().strip("\"'")

                        if self._is_semantic_version_ast(clean_value):
                            errors.append(
                                f"Line {line_num}: Field '{field_name}' uses string version '{clean_value}' - "
                                f"should use ModelSemVer format {{major: X, minor: Y, patch: Z}}",
                            )

    def _validate_parsed_yaml(  # ONEX_EXCLUDE: dict_str_any — YAML data is heterogeneous by nature
        self,
        yaml_data: dict[str, Any],  # ONEX_EXCLUDE: dict_str_any
        errors: list[str],
    ) -> None:
        """Validate the parsed YAML structure for string versions."""
        version_fields = [
            "version",
            "contract_version",
            "node_version",
            "onex_compliance_version",
            "protocol_version",
        ]

        # Check top-level fields
        for field in version_fields:
            if field in yaml_data:
                value = yaml_data[field]
                if isinstance(value, str) and self._is_semantic_version_ast(value):
                    errors.append(
                        f"Field '{field}' uses string version '{value}' - "
                        f"should use ModelSemVer format {{major: X, minor: Y, patch: Z}}",
                    )

        # Check nested version fields
        self._check_nested_versions(yaml_data, errors, [])

    def _check_nested_versions(
        self,
        data: Any,
        errors: list[str],
        path: list[str],
    ) -> None:
        """Recursively check for version strings in nested structures."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = path + [key]

                # If the key suggests it's a version field
                if any(version_word in key.lower() for version_word in ["version"]):
                    if isinstance(value, str) and self._is_semantic_version_ast(value):
                        path_str = ".".join(current_path)
                        errors.append(
                            f"Field '{path_str}' uses string version '{value}' - "
                            f"should use ModelSemVer format {{major: X, minor: Y, patch: Z}}",
                        )

                # Recurse into nested structures
                self._check_nested_versions(value, errors, current_path)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = path + [f"[{i}]"]
                self._check_nested_versions(item, errors, current_path)

    def _is_semantic_version_ast(self, value: str) -> bool:
        """
        Use AST-inspired logic to detect semantic versions.

        Checks if a string matches the semantic version pattern X.Y.Z
        where X, Y, Z are integers.
        """
        if not isinstance(value, str) or not value:
            return False

        # Handle the most common patterns
        if "." not in value:
            return False

        # Split on dots and validate each part
        parts = value.split(".")

        # Must be exactly 3 parts for semantic versioning
        if len(parts) != 3:
            return False

        # Each part must be a valid integer (possibly with leading zeros)
        try:
            for part in parts:
                # Must be numeric and not empty
                if not part or not part.isdigit():
                    return False
                # Convert to int to validate (handles leading zeros)
                int(part)
            return True
        except (ValueError, TypeError):
            return False

    def validate_all_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided files (YAML and Python)."""
        if not file_paths:
            return True

        success = True

        for file_path in file_paths:
            try:
                suffix = file_path.suffix.lower()
                if suffix in [".yaml", ".yml"]:
                    if not self.validate_yaml_file(file_path):
                        success = False
                elif suffix == ".py":
                    if not self.validate_python_file(file_path):
                        success = False
                # Silently skip files with other extensions
            except Exception as e:  # noqa: BLE001
                self.errors.append(f"Error processing file {file_path}: {e}")
                success = False

        return success

    def validate_all_yaml_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided YAML files."""
        if not file_paths:
            return True

        success = True

        for yaml_path in file_paths:
            try:
                if not self.validate_yaml_file(yaml_path):
                    success = False
            except Exception as e:  # noqa: BLE001
                self.errors.append(f"Error processing YAML file {yaml_path}: {e}")
                success = False

        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors or self.ast_violations:
            print("❌ ID/Version Validation FAILED")
            print("=" * 50)

            if self.errors:
                print(f"Found {len(self.errors)} string version errors:")
                for error in self.errors:
                    print(f"   • {error}")
                print()

            if self.ast_violations:
                print(f"Found {len(self.ast_violations)} AST validation errors:")

                # Group by file
                by_file: dict[str, list[ValidationViolation]] = {}
                for violation in self.ast_violations:
                    if violation.file_path not in by_file:
                        by_file[violation.file_path] = []
                    by_file[violation.file_path].append(violation)

                for file_path, file_violations in by_file.items():
                    print(f"📁 {file_path}")
                    for violation in file_violations:
                        print(
                            f"  ⚠️  Line {violation.line_number}:{violation.column} - "
                            f"Field '{violation.field_name}' ({violation.violation_type})"
                        )
                        print(f"      💡 {violation.suggestion}")
                    print()

            print("🔧 How to fix:")
            print("   YAML files: Replace string versions with ModelSemVer format:")
            print('   version: "1.0.0"  →  version: {major: 1, minor: 0, patch: 0}')
            print(
                '   contract_version: "2.1.3"  →  contract_version: {major: 2, minor: 1, patch: 3}',
            )
            print(
                "   Python files: Remove __version__ from __init__.py - versions come from contracts only"
            )
            print(
                "   Python models: Use UUID for ID fields, ModelSemVer for version fields"
            )
            print("   Example: node_id: str  →  node_id: UUID")
            print("   Example: version: str  →  version: ModelSemVer")

        else:
            print(
                f"✅ ID/Version Validation PASSED ({self.checked_files} files checked)",
            )


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        # Parse command line arguments using argparse
        parser = argparse.ArgumentParser(
            description="Validate YAML and Python files for string version/ID anti-patterns",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --dir src/                    # Scan src/ directory recursively
  %(prog)s --dir -v src/                 # Scan with verbose output
  %(prog)s file1.yaml file2.py           # Check specific files
  %(prog)s --verbose tests/test.yaml     # Check file with verbose output
            """,
        )
        parser.add_argument(
            "--dir",
            action="store_true",
            dest="scan_dirs",
            help="Recursively scan directories for YAML and Python files",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Show detailed output (excluded files, files being checked)",
        )
        parser.add_argument(
            "paths",
            nargs="*",
            help="Files or directories to validate",
        )

        parsed_args = parser.parse_args()
        scan_dirs = parsed_args.scan_dirs
        verbose = parsed_args.verbose
        args = parsed_args.paths

        if not args:
            print("Error: No paths provided")
            return 1

        try:
            validator = StringVersionValidator()
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: main() reports error and returns exit code
            print(f"Error: Failed to initialize validator: {e}")
            return 1

        if verbose:
            print("Verbose mode enabled")
            print(f"Scan directories mode: {scan_dirs}")
            print(f"Input paths: {args}")
            print()

        yaml_files = []

        try:
            if scan_dirs:
                # Recursively scan directories for YAML and Python files
                for arg in args:
                    try:
                        path = Path(arg)

                        # Check if path exists
                        if not path.exists():
                            print(f"Warning: Path does not exist: {path}")
                            continue

                        if path.is_dir():
                            # Check directory permissions
                            if not os.access(path, os.R_OK):
                                print(f"Warning: Cannot read directory: {path}")
                                continue

                            # Setup timeout for directory scanning (30 seconds)
                            try:
                                with timeout_context("directory_scan"):
                                    # Recursively find all YAML and Python files
                                    # Filter using EXCLUDE_PATTERNS constant (see rationale above)
                                    try:
                                        all_files = (
                                            list(path.rglob("*.yaml"))
                                            + list(path.rglob("*.yml"))
                                            + list(path.rglob("*.py"))
                                        )
                                    except PermissionError as e:
                                        print(
                                            f"Warning: Permission denied scanning directory {path}: {e}"
                                        )
                                        continue
                                    except OSError as e:
                                        print(
                                            f"Warning: OS error scanning directory {path}: {e}"
                                        )
                                        continue

                                    # Filter out excluded files using helper function
                                    try:
                                        for file_path in all_files:
                                            try:
                                                if not should_exclude_file(
                                                    file_path, verbose
                                                ):
                                                    yaml_files.append(file_path)
                                            except Exception as e:  # noqa: BLE001
                                                print(
                                                    f"Warning: Error processing file {file_path}: {e}"
                                                )
                                                continue
                                    except Exception as e:  # noqa: BLE001
                                        print(
                                            f"Warning: Error filtering files in {path}: {e}"
                                        )
                                        continue

                            except timeout_utils.TimeoutError:
                                print(f"Warning: Timeout scanning directory {path}")
                                continue

                        elif path.suffix.lower() in [".yaml", ".yml", ".py"]:
                            if path.exists():
                                yaml_files.append(path)
                            else:
                                print(f"Warning: File does not exist: {path}")
                        else:
                            print(f"Warning: Unsupported file type: {path}")
                    except Exception as e:  # noqa: BLE001
                        print(f"Warning: Error processing argument '{arg}': {e}")
                        continue
            else:
                # Individual file mode - uses should_exclude_file helper
                for arg in args:
                    try:
                        path = Path(arg)

                        if not path.exists():
                            print(f"Warning: File does not exist: {path}")
                            continue

                        # Skip excluded paths using helper function
                        if should_exclude_file(path, verbose):
                            continue

                        if path.suffix.lower() in [".yaml", ".yml", ".py"]:
                            yaml_files.append(path)
                        else:
                            print(f"Warning: Unsupported file type: {path}")
                    except Exception as e:  # noqa: BLE001
                        print(f"Warning: Error processing file argument '{arg}': {e}")
                        continue
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: main() reports error and returns exit code
            print(f"Error: Failed to process file arguments: {e}")
            return 1

        if not yaml_files:
            # No files to check
            print(
                "✅ String Version Validation PASSED (no YAML or Python files to check)"
            )
            return 0

        # Show file count summary in verbose mode
        if verbose:
            yaml_count = sum(
                1 for f in yaml_files if f.suffix.lower() in [".yaml", ".yml"]
            )
            py_count = sum(1 for f in yaml_files if f.suffix.lower() == ".py")
            print(
                f"Files to validate: {len(yaml_files)} total ({yaml_count} YAML, {py_count} Python)"
            )
            print()

        try:
            # Setup timeout for validation (10 minutes)
            with timeout_context("validation"):
                success = validator.validate_all_files(yaml_files)
                validator.print_results()

                # Consider both string version errors and AST violations
                has_violations = bool(validator.errors or validator.ast_violations)
                return 0 if success and not has_violations else 1

        except timeout_utils.TimeoutError:
            print("Error: Validation timeout after 10 minutes")
            return 1
        except (
            Exception  # noqa: BLE001
        ) as e:  # fallback-ok: main() reports error and returns exit code
            print(f"Error: Validation failed with unexpected error: {e}")
            return 1

    except KeyboardInterrupt:
        print("\nError: Validation interrupted by user")
        return 1
    except Exception as e:  # noqa: BLE001  # fallback-ok: main() reports error and returns exit code
        print(f"Error: Unexpected error in main function: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
