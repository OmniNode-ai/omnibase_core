#!/usr/bin/env python3
"""
ONEX File Location Enforcement

Validates that files are located in the correct directories based on their
naming conventions and class types. This prevents organizational drift where
files end up in incorrect locations.

Rules:
- model_*.py files → models/ directory
- enum_*.py files → enums/ directory
- error_*.py files → errors/ directory
- mixin_*.py files → mixins/ directory
- node_*.py files → nodes/ directory
- protocol_*.py files → protocol/ directory
- service_*.py files → services/ directory

Additionally validates that class prefixes match directory structure:
- Model* classes → models/ directory
- Enum* classes → enums/ directory
- Mixin* classes → mixins/ directory
- Node* classes → nodes/ directory
- Protocol* classes → protocol/ directory
- Service* classes → services/ directory
"""

import argparse
import ast
import sys
from pathlib import Path


class FileLocationViolation:
    """Represents a file location violation."""

    def __init__(
        self,
        file_path: Path,
        expected_dir: str,
        actual_dir: str,
        reason: str,
        line_number: int = 1,
    ):
        self.file_path = file_path
        self.expected_dir = expected_dir
        self.actual_dir = actual_dir
        self.reason = reason
        self.line_number = line_number

    def __str__(self) -> str:
        return (
            f"{self.file_path}:{self.line_number}\n"
            f"  Expected: {self.expected_dir}/\n"
            f"  Actual: {self.actual_dir}/\n"
            f"  Reason: {self.reason}"
        )


class FileLocationValidator:
    """Validates file locations based on naming conventions and class types."""

    # File prefix → expected directory mapping
    FILE_PREFIX_RULES = {
        "model_": "models",
        "enum_": "enums",
        "error_": "errors",
        "mixin_": "mixins",
        "node_": "nodes",
        "protocol_": "protocol",
        "service_": "services",
    }

    # Legitimate exceptions - files that can be in other directories
    ALLOWED_EXCEPTIONS = {
        # Helper models can be in their subsystem directory
        "model_onex_container.py": ["container"],
        "model_circuit_breaker.py": ["infrastructure"],
        "model_compute_cache.py": ["infrastructure"],
        "model_effect_transaction.py": ["infrastructure"],
        "model_field_converter.py": ["utils"],
        "model_field_converter_registry.py": ["utils"],
        "model_semver.py": ["primitives"],
        "model_mixin_info.py": ["discovery"],
        "model_ref_info.py": ["utils"],
        "model_service_registry_entry.py": ["mixins"],
        # Validation models
        "model_audit_result.py": ["validation"],
        "model_contract_validation_result.py": ["validation"],
        "model_duplication_info.py": ["validation"],
        "model_duplication_report.py": ["validation"],
        "model_migration_plan.py": ["validation"],
        "model_migration_result.py": ["validation"],
        "model_protocol_info.py": ["validation"],
        "model_protocol_signature_extractor.py": ["validation"],
        "model_union_pattern.py": ["validation"],
        "model_validation_result.py": ["validation"],
        # Infrastructure base classes
        "node_base.py": ["infrastructure"],
        "node_config_provider.py": ["infrastructure"],
        "node_core_base.py": ["infrastructure"],
        # Mixin-specific errors
        "error_contract_violation.py": ["mixins"],
        "error_dependency_failed.py": ["mixins"],
        "error_fail_fast.py": ["mixins"],
        # Error models
        "model_onex_error.py": ["errors"],
        # Service implementations
        "service_logging.py": ["utils"],
        "service_minimal_logging.py": ["utils"],
        "container_service_registry.py": ["container"],
        # Error handling
        "error_handling.py": ["decorators"],
        # Mixin discovery
        "mixin_discovery.py": ["discovery"],
    }

    # Class prefix → expected directory mapping
    CLASS_PREFIX_RULES = {
        "Model": "models",
        "Enum": "enums",
        "Mixin": "mixins",
        "Node": "nodes",
        "Protocol": "protocol",
        "Service": "services",
    }

    # Exceptions - classes that don't need to follow directory rules
    EXCEPTION_PATTERNS = [
        "_",  # Private classes
        "Test",  # Test classes
        "Error",  # Exception classes (can be anywhere)
        "Exception",  # Exception classes
        "Registry",  # Registry classes (ServiceRegistry is a registry FOR services, not a service)
    ]

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.violations: list[FileLocationViolation] = []

    def validate(self) -> bool:
        """
        Validate all file locations in the repository.

        Returns:
            True if all files are in correct locations, False otherwise
        """
        # Find all Python files
        for py_file in self.repo_path.rglob("*.py"):
            # Skip __pycache__, archived, tests, .venv, site-packages
            if any(
                skip in str(py_file)
                for skip in ["__pycache__", "archived", "archive", "tests", ".venv", "site-packages"]
            ):
                continue

            # Skip __init__.py files
            if py_file.name == "__init__.py":
                continue

            self._validate_file(py_file)

        return len(self.violations) == 0

    def _validate_file(self, file_path: Path) -> None:
        """Validate a single file's location."""
        # Skip examples and scripts directories - they have helper classes
        if any(skip_dir in str(file_path) for skip_dir in ["examples/", "scripts/"]):
            return

        # Check if file is in allowed exceptions
        if file_path.name in self.ALLOWED_EXCEPTIONS:
            allowed_dirs = self.ALLOWED_EXCEPTIONS[file_path.name]
            if any(allowed_dir in str(file_path) for allowed_dir in allowed_dirs):
                return  # This is an allowed exception

        # Check file name prefix
        for prefix, expected_dir in self.FILE_PREFIX_RULES.items():
            if file_path.name.startswith(prefix):
                if expected_dir not in str(file_path):
                    actual_dir = self._get_actual_directory(file_path)
                    self.violations.append(
                        FileLocationViolation(
                            file_path=file_path,
                            expected_dir=expected_dir,
                            actual_dir=actual_dir,
                            reason=f"File name '{file_path.name}' starts with '{prefix}' "
                            f"but is not in {expected_dir}/ directory",
                        )
                    )
                return  # Only check one rule per file

        # Check class prefixes
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._validate_class_location(file_path, node)

        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors
            pass

    def _validate_class_location(self, file_path: Path, node: ast.ClassDef) -> None:
        """Validate that a class is in the correct directory."""
        class_name = node.name

        # Skip exception patterns
        if any(pattern in class_name for pattern in self.EXCEPTION_PATTERNS):
            return

        # Check class prefix rules
        for prefix, expected_dir in self.CLASS_PREFIX_RULES.items():
            if class_name.startswith(prefix):
                # Special cases for helper classes
                # Model* classes in nodes/ are OK (helper models)
                if prefix == "Model" and "nodes/" in str(file_path):
                    return
                # Model* classes in validation/ are OK (validation helper models)
                if prefix == "Model" and "validation/" in str(file_path):
                    return
                # Protocol* classes in utils/ are OK (utility protocols)
                if prefix == "Protocol" and "utils/" in str(file_path):
                    return
                # Protocol* classes in validation/ are OK (validation protocols)
                if prefix == "Protocol" and "validation/" in str(file_path):
                    return

                if expected_dir not in str(file_path):
                    actual_dir = self._get_actual_directory(file_path)
                    self.violations.append(
                        FileLocationViolation(
                            file_path=file_path,
                            expected_dir=expected_dir,
                            actual_dir=actual_dir,
                            reason=f"Class '{class_name}' starts with '{prefix}' "
                            f"but is not in {expected_dir}/ directory",
                            line_number=node.lineno,
                        )
                    )
                return  # Only check one rule per class

    def _get_actual_directory(self, file_path: Path) -> str:
        """Extract the actual directory name from file path."""
        parts = file_path.parts
        # Find the directory after 'src' or 'omnibase_core'
        for i, part in enumerate(parts):
            if part in ["src", "omnibase_core"]:
                if i + 1 < len(parts):
                    # Return the next directory
                    for j in range(i + 1, len(parts) - 1):
                        if parts[j] != "omnibase_core":
                            return parts[j]
        return "unknown"

    def generate_report(self) -> str:
        """Generate a validation report."""
        if not self.violations:
            return "✅ All files are in correct locations!"

        report = "🚨 ONEX File Location Violations\n"
        report += "=" * 50 + "\n\n"

        report += f"Found {len(self.violations)} file(s) in incorrect locations:\n\n"

        for violation in sorted(self.violations, key=lambda v: str(v.file_path)):
            report += str(violation) + "\n\n"

        report += "📚 FILE LOCATION RULES:\n"
        report += "=" * 50 + "\n"
        report += "File Prefixes:\n"
        for prefix, directory in self.FILE_PREFIX_RULES.items():
            report += f"  • {prefix}*.py → {directory}/\n"

        report += "\nClass Prefixes:\n"
        for prefix, directory in self.CLASS_PREFIX_RULES.items():
            report += f"  • {prefix}* → {directory}/\n"

        report += "\n💡 How to fix:\n"
        report += "  1. Move the file to the correct directory\n"
        report += "  2. Update imports in other files\n"
        report += "  3. Run tests to verify nothing broke\n"

        return report


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate ONEX file locations based on naming conventions"
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        return 1

    validator = FileLocationValidator(repo_path)
    is_valid = validator.validate()

    if is_valid:
        if args.verbose:
            print("✅ All files are in correct locations!")
        return 0
    else:
        report = validator.generate_report()
        print(report)
        print(
            f"\n❌ FAILURE: {len(validator.violations)} file location violations found!"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
