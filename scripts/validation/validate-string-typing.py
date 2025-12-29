#!/usr/bin/env python3
"""
Comprehensive String Typing Anti-Pattern Validation Hook for ONEX Architecture

Validates that Pydantic models follow strong typing conventions by detecting:
1. *_id: str fields that should be UUID
2. *_name: str fields that reference entities (should be UUID + display name)
3. category: str, type: str, status: str fields that should be enums
4. Multiple string fields in models representing structured data

Features:
- AST parsing for reliable pattern detection
- Configurable exclusions and severity levels
- File pattern matching (.py files in models/)
- Integration with existing pre-commit pipeline
- Clear error messages with suggestions

This hook helps maintain type safety and prevents string-heavy anti-patterns
that lead to runtime issues and poor data validation.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Constants
MAX_PYTHON_FILE_SIZE = 10 * 1024 * 1024  # 10MB - prevent DoS attacks
VALIDATION_TIMEOUT = 600  # 10 minutes
DIRECTORY_SCAN_TIMEOUT = 30  # seconds

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class StringTypingViolation:
    """Represents a string typing validation violation."""

    file_path: str
    line_number: int
    column: int
    field_name: str
    violation_type: str
    severity: str  # 'error' or 'warning'
    current_annotation: str
    suggested_fix: str
    explanation: str


@dataclass
class ValidationConfig:
    """Configuration for string typing validation."""

    # Fields that can legitimately be strings
    allowed_string_fields: set[str]

    # Models that are excluded from validation
    excluded_models: set[str]

    # Files that are excluded from validation
    excluded_files: set[str]

    # Field patterns that should be UUIDs
    uuid_patterns: list[str]

    # Field patterns that should be enums
    enum_patterns: dict[str, list[str]]

    # Maximum allowed string fields per model
    max_string_fields_per_model: int

    # Whether to treat warnings as errors
    strict_mode: bool

    @classmethod
    def default(cls) -> ValidationConfig:
        """Create default configuration."""
        return cls(
            allowed_string_fields={
                # Legitimate string content
                "description",
                "content",
                "text",
                "message",
                "notes",
                "comment",
                "summary",
                "details",
                "body",
                "title",
                "label",
                "caption",
                # Paths and URLs
                "path",
                "url",
                "uri",
                "file_path",
                "directory_path",
                "endpoint",
                "address",
                "location",
                "source",
                "destination",
                "target",
                # Patterns and templates
                "pattern",
                "template",
                "format",
                "expression",
                "regex",
                "query",
                "command",
                "script",
                "code",
                # Metadata and configuration
                "metadata",
                "config",
                "settings",
                "options",
                "parameters",
                "args",
                "kwargs",
                "data",
                "payload",
                "raw_data",
                # Version and compatibility strings (when justified)
                "version_pattern",
                "version_spec",
                "compatibility_string",
                "version_range",
                "constraint",
                # Human-readable identifiers (when UUID is not appropriate)
                "display_name",
                "human_readable_name",
                "friendly_name",
                "short_name",
                "alias",
                "nickname",
                # External system identifiers (when not under our control)
                "external_id",
                "third_party_id",
                "legacy_id",
                "system_id",
                # Specific justified cases
                "encoding",
                "charset",
                "locale",
                "timezone",
                "language",
                "mime_type",
                "content_type",
                "media_type",
            },
            excluded_models={
                # Base classes and abstract models
                "BaseModel",
                "ModelFieldAccessor",
                "ModelTypedAccessor",
                # Test models
                "TestModel",
                "MockModel",
                "SampleModel",
                # Legacy models (temporary exclusions)
                "LegacyModel",
            },
            excluded_files={
                # Test files
                "test_*.py",
                "*_test.py",
                "tests.py",
                # Example files
                "example*.py",
                "*_example.py",
                "examples.py",
                # Legacy and archived files
                "legacy_*.py",
                "*_legacy.py",
                "archived_*.py",
                # Base classes and mixins
                "base_*.py",
                "*_base.py",
                "mixin*.py",
                "*_mixin.py",
            },
            uuid_patterns=[
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
                r"^entity_id$",
                r"^object_id$",
                r"^resource_id$",
                r"^task_id$",
                r"^job_id$",
                r"^workflow_id$",
                r"^process_id$",
                r"^instance_id$",
                r"^reference_id$",
                r"^correlation_id$",
            ],
            enum_patterns={
                "status": [
                    "active",
                    "inactive",
                    "pending",
                    "completed",
                    "failed",
                    "running",
                ],
                "state": ["new", "processing", "finished", "error", "cancelled"],
                "type": ["user", "admin", "system", "guest", "service"],
                "category": ["primary", "secondary", "tertiary", "other"],
                "priority": ["low", "medium", "high", "critical", "urgent"],
                "level": ["debug", "info", "warning", "error", "critical"],
                "mode": ["auto", "manual", "hybrid", "disabled"],
                "role": ["read", "write", "admin", "owner", "viewer"],
                "visibility": ["public", "private", "internal", "restricted"],
                "format": ["json", "xml", "yaml", "csv", "text"],
            },
            max_string_fields_per_model=5,
            strict_mode=False,
        )

    @classmethod
    def from_file(cls, config_path: Path) -> ValidationConfig:
        """Load configuration from JSON file."""
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            # Convert sets and lists from JSON
            config = cls.default()

            if "allowed_string_fields" in data:
                config.allowed_string_fields = set(data["allowed_string_fields"])

            if "excluded_models" in data:
                config.excluded_models = set(data["excluded_models"])

            if "excluded_files" in data:
                config.excluded_files = set(data["excluded_files"])

            if "uuid_patterns" in data:
                config.uuid_patterns = data["uuid_patterns"]

            if "enum_patterns" in data:
                config.enum_patterns = data["enum_patterns"]

            if "max_string_fields_per_model" in data:
                config.max_string_fields_per_model = data["max_string_fields_per_model"]

            if "strict_mode" in data:
                config.strict_mode = data["strict_mode"]

            return config

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            print("Using default configuration.")
            return cls.default()


class PydanticModelAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Pydantic models for string typing anti-patterns."""

    def __init__(self, file_path: str, config: ValidationConfig):
        self.file_path = file_path
        self.config = config
        self.violations: list[StringTypingViolation] = []
        self.imports: set[str] = set()
        self.current_class: str | None = None
        self.current_model_fields: list[str] = []
        self.is_pydantic_model = False

    def visit_Import(self, node: ast.Import):
        """Track imports to understand available types."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports to understand available types."""
        if node.module:
            for alias in node.names:
                if alias.name == "*":
                    # Handle star imports
                    if node.module == "uuid":
                        self.imports.add("UUID")
                    elif "pydantic" in node.module:
                        self.imports.add("BaseModel")
                else:
                    self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions to identify Pydantic models."""
        old_class = self.current_class
        old_fields = self.current_model_fields
        old_is_pydantic = self.is_pydantic_model

        self.current_class = node.name
        self.current_model_fields = []
        self.is_pydantic_model = self._is_pydantic_model(node)

        # Skip excluded models
        if self.current_class in self.config.excluded_models:
            self.is_pydantic_model = False

        self.generic_visit(node)

        # Analyze the complete model after visiting all fields
        if self.is_pydantic_model and self.current_model_fields:
            self._analyze_model_string_usage()

        # Restore previous state
        self.current_class = old_class
        self.current_model_fields = old_fields
        self.is_pydantic_model = old_is_pydantic

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit annotated assignments (field definitions)."""
        if (
            self.is_pydantic_model
            and isinstance(node.target, ast.Name)
            and self.current_class
        ):
            field_name = node.target.id
            annotation_str = self._get_annotation_string(node.annotation)

            # Track all fields for model-level analysis
            self.current_model_fields.append(field_name)

            # Check individual field patterns
            self._check_field_annotation(
                field_name, annotation_str, node.lineno, node.col_offset
            )

        self.generic_visit(node)

    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Check if a class is a Pydantic model."""
        # Check direct inheritance from BaseModel
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            elif isinstance(base, ast.Attribute):
                # Handle pydantic.BaseModel
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == "pydantic"
                    and base.attr == "BaseModel"
                ):
                    return True

        # Check if BaseModel is in imports and used
        return "BaseModel" in self.imports and any(
            isinstance(base, ast.Name) and base.id == "BaseModel" for base in node.bases
        )

    def _check_field_annotation(
        self, field_name: str, annotation_str: str, line_number: int, column: int
    ):
        """Check if a field annotation violates string typing rules."""
        # Skip allowed string fields
        if field_name in self.config.allowed_string_fields:
            return

        # Check if it's a string type
        if not self._is_string_type(annotation_str):
            return

        # Check UUID patterns
        if self._matches_uuid_patterns(field_name):
            self.violations.append(
                StringTypingViolation(
                    file_path=self.file_path,
                    line_number=line_number,
                    column=column,
                    field_name=field_name,
                    violation_type="string_id",
                    severity="error",
                    current_annotation=annotation_str,
                    suggested_fix="UUID",
                    explanation=f"Field '{field_name}' appears to be an identifier and should use UUID type for proper type safety and validation",
                )
            )
            return

        # Check enum patterns
        enum_suggestion = self._check_enum_patterns(field_name)
        if enum_suggestion:
            self.violations.append(
                StringTypingViolation(
                    file_path=self.file_path,
                    line_number=line_number,
                    column=column,
                    field_name=field_name,
                    violation_type="string_enum",
                    severity="warning" if not self.config.strict_mode else "error",
                    current_annotation=annotation_str,
                    suggested_fix=f"Enum{field_name.title()}",
                    explanation=f"Field '{field_name}' appears to represent a categorical value and should use an enum. Common values: {', '.join(enum_suggestion[:3])}{'...' if len(enum_suggestion) > 3 else ''}",
                )
            )
            return

        # Check for entity reference patterns
        if self._is_entity_reference(field_name):
            self.violations.append(
                StringTypingViolation(
                    file_path=self.file_path,
                    line_number=line_number,
                    column=column,
                    field_name=field_name,
                    violation_type="string_entity_reference",
                    severity="warning" if not self.config.strict_mode else "error",
                    current_annotation=annotation_str,
                    suggested_fix="UUID + display_name: str (separate fields)",
                    explanation=f"Field '{field_name}' appears to reference an entity. Consider using a UUID for the reference and a separate display_name field for human-readable text",
                )
            )

    def _analyze_model_string_usage(self):
        """Analyze the overall string usage in a model."""
        string_field_count = 0

        # Count fields that are likely to be strings based on their names
        for field_name in self.current_model_fields:
            if (
                field_name not in self.config.allowed_string_fields
                and not self._matches_uuid_patterns(field_name)
                and not self._check_enum_patterns(field_name)
            ):
                string_field_count += 1

        # Check if the model has too many string fields
        if string_field_count > self.config.max_string_fields_per_model:
            # Find a representative violation location (first field)
            violation_line = 1
            violation_col = 0

            self.violations.append(
                StringTypingViolation(
                    file_path=self.file_path,
                    line_number=violation_line,
                    column=violation_col,
                    field_name=self.current_class or "Unknown",
                    violation_type="excessive_string_fields",
                    severity="warning",
                    current_annotation="",
                    suggested_fix="Use more specific types (UUID, enums, separate models)",
                    explanation=f"Model '{self.current_class}' has {string_field_count} string fields (limit: {self.config.max_string_fields_per_model}). Consider using more specific types or breaking into multiple models",
                )
            )

    def _matches_uuid_patterns(self, field_name: str) -> bool:
        """Check if field name matches UUID patterns."""
        import re

        return any(
            re.match(pattern, field_name) for pattern in self.config.uuid_patterns
        )

    def _check_enum_patterns(self, field_name: str) -> list[str] | None:
        """Check if field name matches enum patterns and return suggested values."""
        field_lower = field_name.lower()

        for pattern, values in self.config.enum_patterns.items():
            if pattern in field_lower or field_lower.endswith(f"_{pattern}"):
                return values

        return None

    def _is_entity_reference(self, field_name: str) -> bool:
        """Check if field appears to reference an entity."""
        entity_patterns = ["_name", "name", "_title", "title", "_label", "label"]

        # Check if it's a name field but not a display name
        field_lower = field_name.lower()
        return (
            any(pattern in field_lower for pattern in entity_patterns)
            and "display" not in field_lower
            and "human" not in field_lower
            and "friendly" not in field_lower
        )

    def _is_string_type(self, annotation_str: str) -> bool:
        """Check if annotation represents a string type."""
        # Direct string types
        if annotation_str in ["str", "String"]:
            return True

        # Optional string types
        if annotation_str in ["str | None", "Optional[str]", "str | None"]:
            return True

        # String unions (but not including UUID or enums)
        if (
            "str" in annotation_str
            and "UUID" not in annotation_str
            and "Enum" not in annotation_str
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


class StringTypingValidator:
    """Main validator for string typing anti-patterns in Pydantic models."""

    def __init__(self, config: ValidationConfig | None = None):
        self.config = config or ValidationConfig.default()
        self.violations: list[StringTypingViolation] = []
        self.checked_files = 0
        self.errors: list[str] = []

    def validate_file(self, file_path: Path) -> bool:
        """Validate a single Python file."""
        # Check file existence and basic properties
        if not file_path.exists():
            self.errors.append(f"{file_path}: File does not exist")
            return False

        if not file_path.is_file():
            self.errors.append(f"{file_path}: Path is not a regular file")
            return False

        # Check file permissions
        if not os.access(file_path, os.R_OK):
            self.errors.append(f"{file_path}: Permission denied - cannot read file")
            return False

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_PYTHON_FILE_SIZE:
                self.errors.append(
                    f"{file_path}: File too large ({file_size} bytes), max allowed: {MAX_PYTHON_FILE_SIZE}"
                )
                return False
        except OSError as e:
            self.errors.append(f"{file_path}: Cannot check file size: {e}")
            return False

        # Check if file should be excluded
        if self._should_exclude_file(file_path):
            return True

        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            self.errors.append(f"{file_path}: Error reading file - {e}")
            return False

        # Skip empty files
        if not content.strip():
            return True

        self.checked_files += 1

        # AST-based validation
        try:
            tree = ast.parse(content, filename=str(file_path))
            analyzer = PydanticModelAnalyzer(str(file_path), self.config)
            analyzer.visit(tree)

            # Add violations to our list
            self.violations.extend(analyzer.violations)

        except SyntaxError:
            # Skip files with syntax errors - they'll be caught by other tools
            pass
        except Exception as e:
            self.errors.append(f"{file_path}: Error during AST validation - {e}")
            return False

        return True

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from validation."""
        import fnmatch

        file_name = file_path.name

        # Check exact matches and pattern matches
        for pattern in self.config.excluded_files:
            if fnmatch.fnmatch(file_name, pattern):
                return True

        return False

    def validate_directory(self, directory: Path) -> bool:
        """Validate all Python files in a directory and subdirectories."""
        if not directory.exists() or not directory.is_dir():
            self.errors.append(f"{directory}: Directory does not exist")
            return False

        success = True

        try:
            # Find Python files in models directory
            python_files = list(directory.rglob("*.py"))
            # Sort files for deterministic order across different systems
            python_files.sort(key=lambda p: str(p))

            for file_path in python_files:
                if not self.validate_file(file_path):
                    success = False

        except Exception as e:
            self.errors.append(f"Error scanning directory {directory}: {e}")
            return False

        return success

    def print_results(self) -> None:
        """Print validation results."""
        total_violations = len(self.violations)
        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]

        if self.errors or total_violations > 0:
            print("🔍 String Typing Validation Results")
            print("=" * 50)

            if self.errors:
                print(f"❌ {len(self.errors)} validation errors:")
                for error in self.errors:
                    print(f"   • {error}")
                print()

            if total_violations > 0:
                print(f"📊 Found {total_violations} typing issues:")
                print(f"   • {len(errors)} errors")
                print(f"   • {len(warnings)} warnings")
                print()

                # Group by file
                by_file: dict[str, list[StringTypingViolation]] = {}
                for violation in self.violations:
                    if violation.file_path not in by_file:
                        by_file[violation.file_path] = []
                    by_file[violation.file_path].append(violation)

                # Sort violations by file path and line number for reproducible output
                for file_path, violations in by_file.items():
                    violations.sort(key=lambda v: (v.line_number, v.column))

                # Process files in sorted order for deterministic output
                for file_path in sorted(by_file.keys()):
                    file_violations = by_file[file_path]
                    # Use reliable relative path computation with Path APIs
                    try:
                        relative_path = str(Path(file_path).relative_to(Path.cwd()))
                    except ValueError:
                        relative_path = file_path
                    print(f"📁 {relative_path}")

                    for violation in file_violations:
                        severity_icon = "❌" if violation.severity == "error" else "⚠️"
                        print(
                            f"  {severity_icon} Line {violation.line_number}:{violation.column} - {violation.field_name}"
                        )
                        print(f"      Type: {violation.violation_type}")
                        print(f"      Current: {violation.current_annotation}")
                        print(f"      Suggested: {violation.suggested_fix}")
                        print(f"      💡 {violation.explanation}")
                        print()

                print("🔧 Quick Fix Guide:")
                print("   1. ID fields: user_id: str → user_id: UUID")
                print("   2. Status fields: status: str → status: StatusEnum")
                print(
                    "   3. Entity names: user_name: str → user_id: UUID + display_name: str"
                )
                print(
                    "   4. Too many strings: Break model into smaller, more specific models"
                )
                print()

            if len(errors) > 0:
                print("❌ VALIDATION FAILED (errors found)")
            elif len(warnings) > 0 and self.config.strict_mode:
                print("❌ VALIDATION FAILED (warnings in strict mode)")
            else:
                print("⚠️  VALIDATION PASSED (warnings only)")

        else:
            print(
                f"✅ String Typing Validation PASSED ({self.checked_files} files checked)"
            )

    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        errors = [v for v in self.violations if v.severity == "error"]
        if self.config.strict_mode:
            return len(errors) > 0 or len(self.violations) > 0
        return len(errors) > 0 or len(self.errors) > 0


import timeout_utils

# Import cross-platform timeout utility
from timeout_utils import timeout_context


def setup_timeout_handler():
    """Legacy compatibility function - use timeout_context instead."""
    # No-op for compatibility


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
            print(
                "Usage: validate-string-typing.py [--config CONFIG] [--strict] [--dir] <path1> [path2] ..."
            )
            print("  --config: Path to configuration JSON file")
            print("  --strict: Treat warnings as errors")
            print("  --dir: Recursively scan directories for Python files")
            print("  Without --dir: Treat arguments as individual Python files")
            print("  --help, -h: Show this help message")
            return 0 if "--help" in sys.argv or "-h" in sys.argv else 1

        # Parse arguments
        args = sys.argv[1:]
        config_path = None
        strict_mode = False
        scan_dirs = False

        while args:
            if args[0] == "--config" and len(args) > 1:
                config_path = Path(args[1])
                args = args[2:]
            elif args[0] == "--strict":
                strict_mode = True
                args = args[1:]
            elif args[0] == "--dir":
                scan_dirs = True
                args = args[1:]
            else:
                break

        if not args:
            print("Error: No paths provided")
            return 1

        # Load configuration
        config = ValidationConfig.default()
        if config_path:
            config = ValidationConfig.from_file(config_path)

        if strict_mode:
            config.strict_mode = True

        validator = StringTypingValidator(config)

        # Process files
        success = True

        if scan_dirs:
            # Directory scanning mode
            for arg in args:
                path = Path(arg)
                if path.is_dir():
                    if not validator.validate_directory(path):
                        success = False
                elif path.is_file() and path.suffix == ".py":
                    if not validator.validate_file(path):
                        success = False
                else:
                    print(f"Warning: Skipping {path} (not a directory or Python file)")
        else:
            # Individual file mode
            for arg in args:
                path = Path(arg)
                if path.suffix == ".py":
                    if not validator.validate_file(path):
                        success = False
                else:
                    print(f"Warning: Skipping {path} (not a Python file)")

        # Setup timeout and complete validation
        with timeout_context("validation"):
            validator.print_results()
            return 0 if success and not validator.has_errors() else 1

    except timeout_utils.TimeoutError:
        print("Error: Validation timeout after 10 minutes")
        return 1
    except KeyboardInterrupt:
        print("\nError: Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error in main function: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
