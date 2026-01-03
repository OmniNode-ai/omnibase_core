#!/usr/bin/env python3
"""
Repository Structure Validation Tool - Omni* Ecosystem Standards

Validates repository structure compliance against the standardized framework.
This tool is the foundation for enforcing consistent structure across all omni* repositories.

Usage:
    python tools/validation/validate_structure.py <repo_path> <repo_name>
    python tools/validation/validate_structure.py . omnibase_core
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ViolationLevel(Enum):
    """Severity levels for structure violations."""

    ERROR = "ERROR"  # Must be fixed before deployment
    WARNING = "WARNING"  # Should be fixed but not blocking
    INFO = "INFO"  # Informational, best practice


@dataclass
class StructureViolation:
    """Represents a structure validation violation."""

    level: ViolationLevel
    category: str
    message: str
    path: str
    suggestion: str = ""


class OmniStructureValidator:
    """Validates omni* repository structure against standardized framework."""

    # Cache directories to ignore during validation
    IGNORED_DIRS = {
        ".mypy_cache",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".onex_cache",
    }

    def __init__(self, repo_path: str, repo_name: str):
        self.repo_path = Path(repo_path).resolve()
        self.repo_name = repo_name
        self.violations: list[StructureViolation] = []
        self.src_path = self.repo_path / "src" / repo_name

    def _contains_typeddict(self, file_path: Path) -> bool:
        """
        Check if a Python file contains actual TypedDict class definitions.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            bool: True if the file contains TypedDict classes, False otherwise
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if any base class is TypedDict
                    for base in node.bases:
                        # Handle direct TypedDict reference: class MyType(TypedDict)
                        if (
                            (isinstance(base, ast.Name) and base.id == "TypedDict")
                            or (
                                isinstance(base, ast.Attribute)
                                and base.attr == "TypedDict"
                            )
                            or (
                                isinstance(base, ast.Attribute)
                                and isinstance(base.value, ast.Name)
                                and base.value.id in ("typing", "typing_extensions")
                                and base.attr == "TypedDict"
                            )
                        ):
                            return True
            return False
        except (OSError, SyntaxError, UnicodeDecodeError):
            # If we can't parse the file, assume it doesn't contain TypedDict
            # to avoid false positives
            return False

    def validate_all(self) -> list[StructureViolation]:
        """Run all structure validations."""
        print(f"🔍 Validating structure for repository: {self.repo_name}")
        print(f"📁 Repository path: {self.repo_path}")
        print(f"🎯 Source path: {self.src_path}")
        print("-" * 60)

        # Core validations
        self.validate_forbidden_directories()
        self.validate_required_structure()
        self.validate_model_organization()
        self.validate_types_organization()
        self.validate_enum_organization()
        self.validate_protocol_locations()
        self.validate_node_structure()
        self.validate_test_structure()
        self.validate_required_files()

        return self.violations

    def validate_forbidden_directories(self):
        """Check for forbidden directory patterns."""
        forbidden_patterns = [
            ("model", "Use /models/ (plural) instead"),
            ("mixin", "Use /mixins/ (plural) instead"),
            ("enum", "Use /enums/ (plural) instead"),
            ("protocol", "Use /protocols/ (plural) instead"),
        ]

        try:
            for root, dirs, _ in os.walk(self.src_path):
                # Filter out cache directories from dirs list to prevent walking into them
                dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

                for dir_name in dirs:
                    for forbidden, suggestion in forbidden_patterns:
                        if dir_name == forbidden:
                            path = Path(root) / dir_name
                            self.violations.append(
                                StructureViolation(
                                    level=ViolationLevel.ERROR,
                                    category="Forbidden Directory",
                                    message=f"Found forbidden directory: /{dir_name}/",
                                    path=str(path.relative_to(self.repo_path)),
                                    suggestion=suggestion,
                                )
                            )
        except (PermissionError, OSError) as e:
            # Log permission errors but continue validation
            print(f"⚠️  Permission error accessing directory: {e}")

        # Check for scattered model directories (ignoring cache directories)
        try:
            for root, dirs, _ in os.walk(self.src_path):
                # Filter out cache directories from dirs list to prevent walking into them
                dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

                if (
                    "models" in dirs
                    and str(Path(root).relative_to(self.src_path)) != "."
                ):
                    # Skip if this is inside a cache directory
                    if not any(
                        ignore_dir in str(Path(root))
                        for ignore_dir in self.IGNORED_DIRS
                    ):
                        path = Path(root) / "models"
                        self.violations.append(
                            StructureViolation(
                                level=ViolationLevel.ERROR,
                                category="Scattered Models",
                                message=f"Models directory found outside root: {path}",
                                path=str(path.relative_to(self.repo_path)),
                                suggestion=f"Move all models to src/{self.repo_name}/models/ organized by domain",
                            )
                        )
        except (PermissionError, OSError) as e:
            # Log permission errors but continue validation
            print(f"⚠️  Permission error accessing directory: {e}")

        # Check for scattered enum directories (ignoring cache directories)
        try:
            for root, dirs, _ in os.walk(self.src_path):
                # Filter out cache directories from dirs list to prevent walking into them
                dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

                if (
                    "enums" in dirs
                    and str(Path(root).relative_to(self.src_path)) != "."
                ):
                    # Skip if this is inside a cache directory
                    if not any(
                        ignore_dir in str(Path(root))
                        for ignore_dir in self.IGNORED_DIRS
                    ):
                        path = Path(root) / "enums"
                        self.violations.append(
                            StructureViolation(
                                level=ViolationLevel.ERROR,
                                category="Scattered Enums",
                                message=f"Enums directory found outside root: {path}",
                                path=str(path.relative_to(self.repo_path)),
                                suggestion=f"Move all enums to src/{self.repo_name}/enums/ organized by domain",
                            )
                        )
        except (PermissionError, OSError) as e:
            # Log permission errors but continue validation
            print(f"⚠️  Permission error accessing directory: {e}")

    def validate_required_structure(self):
        """Validate presence of required directories."""
        required_dirs = [
            ("src", "Source code directory"),
            (f"src/{self.repo_name}", "Main package directory"),
            ("tests", "Test directory"),
            ("docs", "Documentation directory"),
        ]

        for dir_path, description in required_dirs:
            full_path = self.repo_path / dir_path
            if not full_path.exists():
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.ERROR,
                        category="Missing Directory",
                        message=f"Missing required directory: {dir_path}",
                        path=dir_path,
                        suggestion=f"Create {description}: mkdir -p {dir_path}",
                    )
                )

    # Non-model files allowed in models/ directory (validators, helpers, etc.)
    EXEMPTED_MODEL_FILES = {
        "validators_metadata.py",  # Shared validator functions for metadata models
    }

    def validate_model_organization(self):
        """Validate model file organization and naming."""
        models_path = self.src_path / "models"

        if not models_path.exists():
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.WARNING,
                    category="Missing Models Directory",
                    message="No models/ directory found",
                    path=f"src/{self.repo_name}/models/",
                    suggestion="Create models directory organized by domain",
                )
            )
            return

        # Check for domain organization
        expected_domains = ["workflow", "infrastructure", "agent", "core"]
        domain_found = False

        for domain in expected_domains:
            if (models_path / domain).exists():
                domain_found = True
                break

        if not domain_found:
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.WARNING,
                    category="Model Organization",
                    message="Models are not organized by domain",
                    path=f"src/{self.repo_name}/models/",
                    suggestion=f"Organize models into domains: {', '.join(expected_domains)}",
                )
            )

        # Check model file naming
        for root, dirs, files in os.walk(models_path):
            # Filter out cache directories from dirs list to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    # Skip exempted files (validators, helpers, etc.)
                    if file in self.EXEMPTED_MODEL_FILES:
                        continue
                    if not file.startswith("model_"):
                        path = Path(root) / file
                        self.violations.append(
                            StructureViolation(
                                level=ViolationLevel.ERROR,
                                category="Model Naming",
                                message=f"Model file must start with 'model_': {file}",
                                path=str(path.relative_to(self.repo_path)),
                                suggestion=f"Rename to: model_{file}",
                            )
                        )

    def validate_types_organization(self):
        """Validate TypedDict file organization and naming."""
        types_path = self.src_path / "types"
        if not types_path.exists():
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.WARNING,
                    category="Missing Types Directory",
                    message="No types/ directory found",
                    path=f"src/{self.repo_name}/types/",
                    suggestion="Create types directory for TypedDict definitions",
                )
            )
            return

        # Check TypedDict file naming using AST-based detection
        for root, dirs, files in os.walk(types_path):
            # Filter out cache directories from dirs list to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file

                    # Only enforce "typed_dict_" naming for files that actually contain TypedDict classes
                    if self._contains_typeddict(file_path):
                        if not file.startswith("typed_dict_"):
                            self.violations.append(
                                StructureViolation(
                                    level=ViolationLevel.ERROR,
                                    category="TypedDict Naming",
                                    message=f"File containing TypedDict classes must start with 'typed_dict_': {file}",
                                    path=str(file_path.relative_to(self.repo_path)),
                                    suggestion=f"Rename to: typed_dict_{file}",
                                )
                            )
                    # Allow other type files (protocols, aliases, etc.) to use descriptive names
                    # No violation is added for non-TypedDict files regardless of naming

    def validate_enum_organization(self):
        """Validate enum file organization and naming."""
        enums_path = self.src_path / "enums"

        if not enums_path.exists():
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.WARNING,
                    category="Missing Enums Directory",
                    message="No enums/ directory found",
                    path=f"src/{self.repo_name}/enums/",
                    suggestion="Create enums directory organized by domain",
                )
            )
            return

        # Check enum file naming
        for root, dirs, files in os.walk(enums_path):
            # Filter out cache directories from dirs list to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    if not file.startswith("enum_"):
                        path = Path(root) / file
                        self.violations.append(
                            StructureViolation(
                                level=ViolationLevel.ERROR,
                                category="Enum Naming",
                                message=f"Enum file must start with 'enum_': {file}",
                                path=str(path.relative_to(self.repo_path)),
                                suggestion=f"Rename to: enum_{file}",
                            )
                        )

    def validate_protocol_locations(self):
        """Validate protocol file locations."""
        protocols_path = self.src_path / "protocols"

        # Protocol directories are allowed in:
        # - omnibase_spi: Higher-level protocol abstractions
        # - omnibase_core: Core-native protocols for self-contained operation (v0.3.6+)
        # See CLAUDE.md: "dependency inversion - SPI now depends on Core, not vice versa"
        PROTOCOL_ALLOWED_REPOS = {"omnibase_spi", "omnibase_core"}

        if self.repo_name not in PROTOCOL_ALLOWED_REPOS and protocols_path.exists():
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.ERROR,
                    category="Protocol Location",
                    message="Only omnibase_spi and omnibase_core should contain protocols directory",
                    path=f"src/{self.repo_name}/protocols/",
                    suggestion="Remove local protocols, import from omnibase_spi or omnibase_core instead",
                )
            )

        # Count protocol files in repositories that don't have explicit protocol allowance
        if self.repo_name not in PROTOCOL_ALLOWED_REPOS:
            protocol_count = 0
            try:
                for _root, dirs, files in os.walk(self.src_path):
                    # Filter out cache directories from dirs list to prevent walking into them
                    dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]

                    for file in files:
                        if file.startswith("protocol_") and file.endswith(".py"):
                            protocol_count += 1
            except (PermissionError, OSError) as e:
                # Log permission errors but continue validation
                print(f"⚠️  Permission error accessing directory: {e}")

            # TEMPORARY: Allow up to 7 protocols for omnibase_core during migration to omnibase_spi
            # The following protocols are actively used and should eventually be migrated:
            #   - protocol_error_context.py (types)
            #   - protocol_metadata_provider.py (types)
            #   - protocol_schema_value.py (types)
            #   - protocol_validatable.py (types)
            #   - protocol_registry_aware.py (mixins)
            #   - protocol_event_bus.py (mixins)
            #   - protocol_log_context_fallback.py (logging)
            # TODO: Complete migration of these protocols to omnibase_spi
            max_protocols = 7 if self.repo_name == "omnibase_core" else 3

            if protocol_count > max_protocols:
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.ERROR,
                        category="Too Many Protocols",
                        message=f"Found {protocol_count} protocol files (max {max_protocols} allowed for non-SPI repos)",
                        path=f"src/{self.repo_name}/",
                        suggestion="Migrate excess protocols to omnibase_spi",
                    )
                )

    def validate_node_structure(self):
        """Validate ONEX four-node architecture compliance."""
        nodes_path = self.src_path / "nodes"

        if not nodes_path.exists():
            return  # Not all repos need nodes

        for node_dir in nodes_path.iterdir():
            if not node_dir.is_dir():
                continue

            # Skip cache directories and other ignored directories
            if node_dir.name in self.IGNORED_DIRS:
                continue

            # Validate node naming pattern
            if not node_dir.name.startswith("node_"):
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.ERROR,
                        category="Node Naming",
                        message=f"Node directory must start with 'node_': {node_dir.name}",
                        path=str(node_dir.relative_to(self.repo_path)),
                        suggestion=f"Rename to: node_{node_dir.name}",
                    )
                )
                continue

            # Check for node type suffix
            valid_suffixes = ["_compute", "_effect", "_reducer", "_orchestrator"]
            has_valid_suffix = any(
                node_dir.name.endswith(suffix) for suffix in valid_suffixes
            )

            if not has_valid_suffix:
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.ERROR,
                        category="Node Type",
                        message=f"Node must end with type suffix: {node_dir.name}",
                        path=str(node_dir.relative_to(self.repo_path)),
                        suggestion=f"Add suffix: {', '.join(valid_suffixes)}",
                    )
                )

            # Validate version structure
            version_dir = node_dir / "v1_0_0"
            if not version_dir.exists():
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.ERROR,
                        category="Node Version",
                        message="Missing version directory: v1_0_0",
                        path=str(node_dir.relative_to(self.repo_path)),
                        suggestion="Create v1_0_0 directory with node.py and contracts/",
                    )
                )
                continue

            # Check required node files
            required_files = ["node.py"]
            for req_file in required_files:
                file_path = version_dir / req_file
                if not file_path.exists():
                    self.violations.append(
                        StructureViolation(
                            level=ViolationLevel.ERROR,
                            category="Missing Node File",
                            message=f"Missing required file: {req_file}",
                            path=str(version_dir.relative_to(self.repo_path)),
                            suggestion=f"Create {req_file} with proper node implementation",
                        )
                    )

    def validate_test_structure(self):
        """Validate test directory structure mirrors src/."""
        tests_path = self.repo_path / "tests"

        if not tests_path.exists():
            self.violations.append(
                StructureViolation(
                    level=ViolationLevel.WARNING,
                    category="Missing Tests",
                    message="No tests directory found",
                    path="tests/",
                    suggestion="Create tests directory that mirrors src/ structure",
                )
            )
            return

        # Check for test structure organization
        required_test_dirs = ["unit", "integration"]
        for test_dir in required_test_dirs:
            if not (tests_path / test_dir).exists():
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.WARNING,
                        category="Test Organization",
                        message=f"Missing test directory: {test_dir}",
                        path=f"tests/{test_dir}/",
                        suggestion=f"Create {test_dir} test directory",
                    )
                )

    def validate_required_files(self):
        """Validate presence of required configuration files."""
        required_files = [
            ("pyproject.toml", "Python project configuration"),
            ("README.md", "Project documentation"),
            (".gitignore", "Git ignore patterns"),
        ]

        for file_name, description in required_files:
            file_path = self.repo_path / file_name
            if not file_path.exists():
                self.violations.append(
                    StructureViolation(
                        level=ViolationLevel.INFO,
                        category="Missing File",
                        message=f"Missing recommended file: {file_name}",
                        path=file_name,
                        suggestion=f"Create {description}",
                    )
                )


def print_validation_report(violations: list[StructureViolation], repo_name: str):
    """Print formatted validation report."""
    print(f"\n🚨 Repository '{repo_name}' Structure Validation Report")
    print("=" * 60)

    # Count violations by level
    error_count = len([v for v in violations if v.level == ViolationLevel.ERROR])
    warning_count = len([v for v in violations if v.level == ViolationLevel.WARNING])
    info_count = len([v for v in violations if v.level == ViolationLevel.INFO])

    print(f"Summary: {error_count} errors, {warning_count} warnings, {info_count} info")

    if error_count == 0 and warning_count == 0:
        print("✅ SUCCESS: Repository structure is compliant!")
        return True

    print(
        f"❌ FAILURE: {error_count + warning_count} structure violations must be fixed!"
    )
    print()

    # Group violations by category
    by_category: dict[str, list[StructureViolation]] = {}
    for violation in violations:
        if violation.category not in by_category:
            by_category[violation.category] = []
        by_category[violation.category].append(violation)

    # Print violations by category
    for category, cat_violations in by_category.items():
        print(f"📂 {category}")
        print("-" * 40)

        for violation in cat_violations:
            level_emoji = (
                "🚨"
                if violation.level == ViolationLevel.ERROR
                else "⚠️"
                if violation.level == ViolationLevel.WARNING
                else "INFO"
            )
            print(f"{level_emoji} {violation.level.value}: {violation.message}")
            print(f"   📍 Path: {violation.path}")
            if violation.suggestion:
                print(f"   💡 Suggestion: {violation.suggestion}")
            print()

    return error_count == 0


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate omni* repository structure compliance"
    )
    parser.add_argument("repo_path", help="Path to repository root")
    parser.add_argument("repo_name", help="Repository name (e.g., omnibase_core)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    # Validate repository structure
    validator = OmniStructureValidator(args.repo_path, args.repo_name)
    violations = validator.validate_all()

    if args.json:
        import json

        violation_data = [
            {
                "level": v.level.value,
                "category": v.category,
                "message": v.message,
                "path": v.path,
                "suggestion": v.suggestion,
            }
            for v in violations
        ]
        print(json.dumps(violation_data, indent=2))
    else:
        success = print_validation_report(violations, args.repo_name)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
