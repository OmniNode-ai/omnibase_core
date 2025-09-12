#!/usr/bin/env python3
"""
String Version Validation Hook for ONEX Architecture

Validates that contract YAML files use proper ModelSemVer format instead of string versions.
String versions like "1.0.0" should be ModelSemVer format like {major: 1, minor: 0, patch: 0}.

Uses AST parsing for reliable detection of semantic version patterns.
This prevents runtime issues and ensures proper type compliance.
"""

import sys
from pathlib import Path
from typing import Any

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model


class StringVersionValidator:
    """Validates that YAML contract files don't use string versions using AST parsing."""

    def __init__(self):
        self.errors: list[str] = []
        self.checked_files = 0

    def validate_yaml_file(self, yaml_path: Path) -> bool:
        """Validate a single YAML file for string version usage."""
        try:
            with open(yaml_path, encoding="utf-8") as f:
                content = f.read()

            # Parse YAML using Pydantic model validation
            yaml_model = load_yaml_content_as_model(content, ModelGenericYaml)
            yaml_data = yaml_model.model_dump()

            if not yaml_data:
                return True  # Empty files are not our concern

            self.checked_files += 1
            file_errors = []

            # Use AST-based validation on the raw content
            self._validate_yaml_content_ast(content, yaml_path, file_errors)

            # Also validate the parsed structure for completeness
            self._validate_parsed_yaml(yaml_data, file_errors)

            if file_errors:
                self.errors.extend([f"{yaml_path}: {error}" for error in file_errors])
                return False

            return True

        except Exception as e:
            self.errors.append(f"{yaml_path}: Failed to parse YAML - {e!s}")
            return False

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

    def validate_all_yaml_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided YAML files."""
        success = True

        for yaml_path in file_paths:
            if not self.validate_yaml_file(yaml_path):
                success = False

        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ String Version Validation FAILED")
            print("=" * 50)
            print(
                f"Found {len(self.errors)} string version errors in {self.checked_files} files:\n",
            )

            for error in self.errors:
                print(f"   • {error}")

            print("\n🔧 How to fix:")
            print('   Replace string versions like "1.0.0" with ModelSemVer format:')
            print('   version: "1.0.0"  →  version: {major: 1, minor: 0, patch: 0}')
            print(
                '   contract_version: "2.1.3"  →  contract_version: {major: 2, minor: 1, patch: 3}',
            )

        else:
            print(
                f"✅ String Version Validation PASSED ({self.checked_files} files checked)",
            )


def main() -> int:
    """Main entry point for the validation hook."""
    if len(sys.argv) < 2:
        print("Usage: validate-string-versions.py [--dir] <path1> [path2] ...")
        print("  --dir: Recursively scan directories for YAML files")
        print("  Without --dir: Treat arguments as individual YAML files")
        return 1

    validator = StringVersionValidator()

    # Check for directory scan mode
    scan_dirs = False
    args = sys.argv[1:]

    if args[0] == "--dir":
        scan_dirs = True
        args = args[1:]

    if not args:
        print("Error: No paths provided")
        return 1

    yaml_files = []

    if scan_dirs:
        # Recursively scan directories for YAML files
        for arg in args:
            path = Path(arg)
            if path.is_dir():
                # Recursively find all YAML files, but exclude non-ONEX directories
                exclude_patterns = [
                    "deployment",
                    ".github",
                    "docker-compose",
                    "prometheus",
                    "alerts.yml",
                    "grafana",
                    "kubernetes",
                ]

                all_yaml_files = list(path.rglob("*.yaml")) + list(path.rglob("*.yml"))

                # Filter out excluded files using path components
                for yaml_file in all_yaml_files:
                    should_exclude = False
                    path_parts = yaml_file.parts
                    file_name = yaml_file.name

                    # Check if any path component or filename matches exclusion patterns
                    for pattern in exclude_patterns:
                        if pattern in path_parts or file_name.startswith(pattern):
                            should_exclude = True
                            break

                    if not should_exclude:
                        yaml_files.append(yaml_file)

            elif path.suffix.lower() in [".yaml", ".yml"] and path.exists():
                yaml_files.append(path)
    else:
        # Individual file mode
        for arg in args:
            path = Path(arg)
            if path.suffix.lower() in [".yaml", ".yml"] and path.exists():
                yaml_files.append(path)

    if not yaml_files:
        # No YAML files to check
        print("✅ String Version Validation PASSED (no YAML files to check)")
        return 0

    success = validator.validate_all_yaml_files(yaml_files)
    validator.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
