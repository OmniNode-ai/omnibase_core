#!/usr/bin/env python3
"""
Comprehensive ID and Version Validation Hook for ONEX Architecture

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

import ast
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any, List, NamedTuple

import yaml


class ValidationViolation(NamedTuple):
    """Represents a validation violation."""

    file_path: str
    line_number: int
    column: int
    field_name: str
    violation_type: str
    suggestion: str


# Constants
MAX_PYTHON_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent DoS attacks on Python files
MAX_YAML_FILE_SIZE = 50 * 1024 * 1024  # 50MB - prevent DoS attacks on YAML files
DIRECTORY_SCAN_TIMEOUT = 30  # seconds
VALIDATION_TIMEOUT = 600  # 10 minutes

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Try to import Pydantic models if available (may not exist in empty package structure)
try:
    from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

    from ..core.model_generic_yaml import ModelGenericYaml

    PYDANTIC_MODELS_AVAILABLE = True
except ImportError:
    # Empty package structure - models are archived
    ModelGenericYaml = None
    load_yaml_content_as_model = None
    PYDANTIC_MODELS_AVAILABLE = False


class PythonASTValidator(ast.NodeVisitor):
    """AST visitor to validate ID and version field types in Python files."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[ValidationViolation] = []
        self.imports = set()

        # Patterns for version fields that should use ModelSemVer
        self.version_patterns = [
            r"^version$",
            r"^.*_version$",
            r"^version_.*$",
            r"^schema_version$",
            r"^protocol_version$",
            r"^node_version$",
        ]

        # Patterns for ID fields that should use UUID
        self.id_patterns = [
            r"^.*_id$",
            r"^id$",
            r"^execution_id$",
            r"^request_id$",
            r"^session_id$",
            r"^node_id$",
            r"^connection_id$",
            r"^trace_id$",
            r"^span_id$",
            r"^parent_span_id$",
            r"^example_id$",
            r"^user_id$",
        ]

        # Exceptions - fields that can legitimately be strings
        self.exceptions = {
            "version_pattern",  # Regex patterns can be strings
            "version_spec",  # Version specifications can be strings
            "validation_pattern",  # Regex patterns
            "version_compatibility",  # Compatibility strings
            "execution_id",  # Some execution IDs may need to be strings for compatibility
            "version_str",  # Parameter names for parsing functions
        }

    def visit_Import(self, node: ast.Import):
        """Track imports to understand what types are available."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports to understand what types are available."""
        if node.module:
            for alias in node.names:
                if alias.name == "*":
                    # Handle star imports
                    if node.module == "uuid":
                        self.imports.add("UUID")
                    elif "semver" in node.module:
                        self.imports.add("ModelSemVer")
                else:
                    self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit annotated assignments (field definitions)."""
        if isinstance(node.target, ast.Name):
            field_name = node.target.id
            self._check_field_annotation(
                field_name, node.annotation, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg):
        """Visit function arguments."""
        if node.annotation:
            self._check_field_annotation(
                node.arg, node.annotation, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def _check_field_annotation(
        self, field_name: str, annotation: ast.AST, line_number: int, column: int
    ):
        """Check if a field annotation violates ID/version typing rules."""
        # Skip exceptions
        if field_name in self.exceptions:
            return

        annotation_str = self._get_annotation_string(annotation)

        # Check version fields
        if self._matches_patterns(field_name, self.version_patterns):
            if self._is_string_type(annotation_str):
                suggestion = "Use ModelSemVer instead of str for version fields"
                self.violations.append(
                    ValidationViolation(
                        file_path=self.file_path,
                        line_number=line_number,
                        column=column,
                        field_name=field_name,
                        violation_type="string_version",
                        suggestion=suggestion,
                    )
                )

        # Check ID fields
        elif self._matches_patterns(field_name, self.id_patterns):
            if self._is_string_type(annotation_str):
                suggestion = "Use UUID instead of str for ID fields"
                self.violations.append(
                    ValidationViolation(
                        file_path=self.file_path,
                        line_number=line_number,
                        column=column,
                        field_name=field_name,
                        violation_type="string_id",
                        suggestion=suggestion,
                    )
                )

    def _matches_patterns(self, field_name: str, patterns: List[str]) -> bool:
        """Check if field name matches any of the given regex patterns."""
        return any(re.match(pattern, field_name) for pattern in patterns)

    def _is_string_type(self, annotation_str: str) -> bool:
        """Check if annotation represents a string type."""
        # Direct string types
        if annotation_str in ["str", "String"]:
            return True

        # Optional string types
        if annotation_str in ["str | None", "Optional[str]", "str | None"]:
            return True

        # String unions (but not including UUID or ModelSemVer)
        if (
            "str" in annotation_str
            and "UUID" not in annotation_str
            and "ModelSemVer" not in annotation_str
        ):
            return True

        return False

    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Convert AST annotation to string representation."""
        try:
            return ast.unparse(annotation)
        except AttributeError:
            # Fallback for older Python versions
            return self._ast_to_string(annotation)

    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string (fallback implementation)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return (
                f"{self._ast_to_string(node.value)}[{self._ast_to_string(node.slice)}]"
            )
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return (
                f"{self._ast_to_string(node.left)} | {self._ast_to_string(node.right)}"
            )
        elif isinstance(node, ast.Tuple):
            elements = [self._ast_to_string(elt) for elt in node.elts]
            return f"({', '.join(elements)})"
        else:
            return str(type(node).__name__)


class StringVersionValidator:
    """Validates that YAML contract files don't use string versions and Python files use proper ID/version types."""

    def __init__(self):
        self.errors: list[str] = []
        self.ast_violations: List[ValidationViolation] = []
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
            self.errors.append(f"{python_path}: OS error reading file - {e}")
            return False
        except IOError as e:
            self.errors.append(f"{python_path}: IO error reading file - {e}")
            return False

        # Skip empty files
        if not content.strip():
            return True

        self.checked_files += 1
        file_errors = []

        # Check for __version__ declarations with error handling
        try:
            self._validate_python_version_declarations(
                content, python_path, file_errors
            )
        except Exception as e:
            self.errors.append(f"{python_path}: Error during content validation - {e}")
            return False

        # AST-based validation for ID and version field types
        try:
            tree = ast.parse(content, filename=str(python_path))
            ast_validator = PythonASTValidator(str(python_path))
            ast_validator.visit(tree)

            # Add AST violations to our list
            self.ast_violations.extend(ast_validator.violations)

        except SyntaxError as e:
            # Skip files with syntax errors - they'll be caught by other tools
            pass
        except Exception as e:
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
        """Check Python content for hardcoded __version__ declarations."""
        lines = content.split("\n")

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
            self.errors.append(f"{yaml_path}: OS error reading file - {e}")
            return False
        except IOError as e:
            self.errors.append(f"{yaml_path}: IO error reading file - {e}")
            return False

        # Skip empty files
        if not content.strip():
            return True

        # Parse YAML using Pydantic model validation if available
        yaml_data = None
        if PYDANTIC_MODELS_AVAILABLE:
            try:
                yaml_model = load_yaml_content_as_model(content, ModelGenericYaml)
                yaml_data = yaml_model.model_dump()
            except Exception as e:
                # If we can't parse with Pydantic, log it but continue with AST validation
                # This is not a fatal error since we have fallback validation
                pass

        # Basic YAML syntax validation
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            self.errors.append(f"{yaml_path}: Invalid YAML syntax - {e}")
            return False
        except yaml.constructor.ConstructorError as e:
            self.errors.append(f"{yaml_path}: YAML constructor error - {e}")
            return False
        except yaml.parser.ParserError as e:
            self.errors.append(f"{yaml_path}: YAML parser error - {e}")
            return False
        except yaml.scanner.ScannerError as e:
            self.errors.append(f"{yaml_path}: YAML scanner error - {e}")
            return False
        except MemoryError:
            self.errors.append(f"{yaml_path}: YAML file too large to parse in memory")
            return False

        self.checked_files += 1
        file_errors = []

        # Use AST-based validation on the raw content (always runs)
        try:
            self._validate_yaml_content_ast(content, yaml_path, file_errors)
        except Exception as e:
            self.errors.append(f"{yaml_path}: Error during AST validation - {e}")
            return False

        # Also validate the parsed structure if we have it
        if yaml_data:
            try:
                self._validate_parsed_yaml(yaml_data, file_errors)
            except Exception as e:
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
        lines = content.split("\n")

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

    def _validate_parsed_yaml(
        self,
        yaml_data: dict[str, Any],
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
                if not isinstance(file_path, Path):
                    self.errors.append(
                        f"Invalid file path type: {type(file_path)} - {file_path}"
                    )
                    success = False
                    continue

                suffix = file_path.suffix.lower()
                if suffix in [".yaml", ".yml"]:
                    if not self.validate_yaml_file(file_path):
                        success = False
                elif suffix == ".py":
                    if not self.validate_python_file(file_path):
                        success = False
                # Silently skip files with other extensions
            except Exception as e:
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
                if not isinstance(yaml_path, Path):
                    self.errors.append(
                        f"Invalid YAML path type: {type(yaml_path)} - {yaml_path}"
                    )
                    success = False
                    continue

                if not self.validate_yaml_file(yaml_path):
                    success = False
            except Exception as e:
                self.errors.append(f"Error processing YAML file {yaml_path}: {e}")
                success = False

        return success

    def print_results(self) -> None:
        """Print validation results."""
        total_violations = len(self.errors) + len(self.ast_violations)

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
                by_file = {}
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


import timeout_utils

# Import cross-platform timeout utility
from timeout_utils import timeout_context


def setup_timeout_handler():
    """Legacy compatibility function - use timeout_context instead."""
    pass  # No-op for compatibility


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        if len(sys.argv) < 2:
            print("Usage: validate-string-versions.py [--dir] <path1> [path2] ...")
            print("  --dir: Recursively scan directories for YAML and Python files")
            print("  Without --dir: Treat arguments as individual YAML/Python files")
            return 1

        try:
            validator = StringVersionValidator()
        except Exception as e:
            print(f"Error: Failed to initialize validator: {e}")
            return 1

        # Check for directory scan mode
        scan_dirs = False
        args = sys.argv[1:]

        try:
            if args and args[0] == "--dir":
                scan_dirs = True
                args = args[1:]
        except Exception as e:
            print(f"Error: Failed to parse arguments: {e}")
            return 1

        if not args:
            print("Error: No paths provided")
            return 1

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
                                    # Recursively find all YAML and Python files, but exclude non-ONEX directories
                                    exclude_patterns = [
                                        "deployment",
                                        ".github",
                                        "docker-compose",
                                        "prometheus",
                                        "alerts.yml",
                                        "grafana",
                                        "kubernetes",
                                        "ci-cd.yml",  # GitHub Actions CI file
                                        "__pycache__",
                                        ".mypy_cache",
                                        ".pytest_cache",
                                        "node_modules",
                                        "archive",  # Exclude archived code
                                        "archived",  # Exclude archived code (alternative naming)
                                        "tests",  # Exclude test files
                                        "examples_validation_container_usage.py",  # Exclude specific example files
                                    ]

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

                                    # Filter out excluded files using path components
                                    try:
                                        for file_path in all_files:
                                            try:
                                                should_exclude = False
                                                path_parts = file_path.parts
                                                file_name = file_path.name

                                                # Check if any path component or filename matches exclusion patterns
                                                for pattern in exclude_patterns:
                                                    if (
                                                        pattern in path_parts
                                                        or file_name.startswith(pattern)
                                                    ):
                                                        should_exclude = True
                                                        break

                                                if not should_exclude:
                                                    yaml_files.append(file_path)
                                            except Exception as e:
                                                print(
                                                    f"Warning: Error processing file {file_path}: {e}"
                                                )
                                                continue
                                    except Exception as e:
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
                    except Exception as e:
                        print(f"Warning: Error processing argument '{arg}': {e}")
                        continue
            else:
                # Individual file mode
                for arg in args:
                    try:
                        path = Path(arg)

                        if not path.exists():
                            print(f"Warning: File does not exist: {path}")
                            continue

                        if path.suffix.lower() in [".yaml", ".yml", ".py"]:
                            yaml_files.append(path)
                        else:
                            print(f"Warning: Unsupported file type: {path}")
                    except Exception as e:
                        print(f"Warning: Error processing file argument '{arg}': {e}")
                        continue
        except Exception as e:
            print(f"Error: Failed to process file arguments: {e}")
            return 1

        if not yaml_files:
            # No files to check
            print(
                "✅ String Version Validation PASSED (no YAML or Python files to check)"
            )
            return 0

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
        except Exception as e:
            print(f"Error: Validation failed with unexpected error: {e}")
            return 1

    except KeyboardInterrupt:
        print("\nError: Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error in main function: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
