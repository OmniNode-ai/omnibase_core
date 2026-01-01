#!/usr/bin/env python3
"""
Precommit hook to prevent manual YAML validation bypassing Pydantic models.

This hook ensures all contract validation goes through backing Pydantic models
instead of direct YAML validation, maintaining consistency and catching
real validation issues.
"""

import ast
import sys
from pathlib import Path

import yaml


class ManualYamlValidationDetector:
    """Detects manual YAML validation that bypasses Pydantic models."""

    def __init__(self, config_path: Path | None = None):
        self.errors: list[str] = []
        self.checked_files = 0
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Path | None) -> dict:
        """Load allowlist configuration from YAML file."""
        if config_path is None:
            # Default to project root
            config_path = (
                Path(__file__).parent.parent.parent / ".yaml-validation-allowlist.yaml"
            )

        if not config_path.exists():
            # Fallback to empty config
            return {
                "allowed_files": [],
                "allowed_filenames": [],
                "allowed_functions": [],
            }

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config if isinstance(config, dict) else {}
        except Exception:
            # If config fails to load, use empty config
            return {
                "allowed_files": [],
                "allowed_filenames": [],
                "allowed_functions": [],
            }

    def validate_python_file(self, py_path: Path) -> bool:
        """Check Python file for manual YAML validation patterns."""
        # Validate file existence and basic properties
        if not py_path.exists():
            self.errors.append(f"{py_path}: File does not exist")
            return False

        if not py_path.is_file():
            self.errors.append(f"{py_path}: Path is not a regular file")
            return False

        if py_path.stat().st_size == 0:
            # Empty files are valid, just skip them
            self.checked_files += 1
            return True

        # Check if file is too large (> 10MB) to prevent memory issues
        max_file_size = 10 * 1024 * 1024  # 10MB
        if py_path.stat().st_size > max_file_size:
            self.errors.append(
                f"{py_path}: File too large ({py_path.stat().st_size} bytes), skipping"
            )
            return False

        content = None
        try:
            # Try UTF-8 first, then fallback encodings
            encodings_to_try = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

            for encoding in encodings_to_try:
                try:
                    with open(py_path, encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    if encoding == encodings_to_try[-1]:  # Last encoding failed
                        self.errors.append(
                            f"{py_path}: Unable to decode file with any supported encoding "
                            f"(tried: {', '.join(encodings_to_try)})"
                        )
                        return False
                    continue

        except FileNotFoundError:
            self.errors.append(f"{py_path}: File not found")
            return False
        except PermissionError:
            self.errors.append(f"{py_path}: Permission denied - cannot read file")
            return False
        except OSError as e:
            self.errors.append(f"{py_path}: OS error reading file - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{py_path}: Unexpected error reading file - {e}")
            return False

        # Parse AST with comprehensive error handling
        try:
            tree = ast.parse(content, filename=str(py_path))
        except SyntaxError as e:
            self.errors.append(
                f"{py_path}: Python syntax error at line {e.lineno}, column {e.offset}: {e.msg}"
            )
            return False
        except ValueError as e:
            self.errors.append(f"{py_path}: Invalid Python code - {e}")
            return False
        except Exception as e:
            self.errors.append(f"{py_path}: Failed to parse Python AST - {e}")
            return False

        self.checked_files += 1
        file_errors = []

        # Check for manual YAML validation patterns with error handling
        try:
            self._current_function = None
            self._check_node_with_context(tree, py_path, file_errors)
        except Exception as e:
            self.errors.append(f"{py_path}: Error during pattern analysis - {e}")
            return False

        if file_errors:
            self.errors.extend([f"{py_path}: {error}" for error in file_errors])
            return False

        return True

    def _check_node_with_context(
        self,
        node: ast.AST,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Check AST node with function context tracking."""
        try:
            # Track function context
            if isinstance(node, ast.FunctionDef):
                old_function = getattr(self, "_current_function", None)
                self._current_function = node.name

                # Check children with error handling
                try:
                    for child in ast.iter_child_nodes(node):
                        self._check_node_with_context(child, file_path, errors)
                except Exception as e:
                    errors.append(
                        f"Error analyzing function '{node.name}' at line {node.lineno}: {e}"
                    )

                # Restore previous context
                self._current_function = old_function
            else:
                # Check this node for validation patterns
                try:
                    self._check_yaml_validation_patterns(node, file_path, errors)
                except Exception as e:
                    errors.append(
                        f"Error checking patterns at line {getattr(node, 'lineno', 'unknown')}: {e}"
                    )

                # Check children with error handling
                try:
                    for child in ast.iter_child_nodes(node):
                        self._check_node_with_context(child, file_path, errors)
                except Exception as e:
                    errors.append(
                        f"Error analyzing child nodes at line {getattr(node, 'lineno', 'unknown')}: {e}"
                    )

        except Exception as e:
            # Catch-all for any unexpected errors in node traversal
            errors.append(
                f"Unexpected error during AST traversal at line {getattr(node, 'lineno', 'unknown')}: {e}"
            )

    def _check_yaml_validation_patterns(
        self,
        node: ast.AST,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Check AST node for manual YAML validation patterns."""

        # Pattern 1: yaml.safe_load() followed by model validation
        if isinstance(node, ast.Call):
            if (
                self._is_yaml_safe_load(node)
                and not self._is_in_from_yaml_method(node)
                and not self._is_in_safe_yaml_loader(file_path)
                and not self._is_in_yaml_utility_function()
                and not self._is_in_test_file(file_path)
            ):
                errors.append(
                    f"Line {node.lineno}: Found yaml.safe_load() - "
                    f"use Pydantic model.model_validate() instead",
                )

        # Pattern 2: Direct YAML field checking
        if isinstance(node, ast.Subscript):
            if (
                self._is_yaml_field_access(node)
                and not self._is_in_safe_yaml_loader(file_path)
                and not self._is_in_test_file(file_path)
            ):
                errors.append(
                    f"Line {node.lineno}: Direct YAML field access detected - "
                    f"use Pydantic model properties instead",
                )

        # Pattern 3: Manual essential_fields validation
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "essential_fields"
                    and isinstance(node.value, ast.List)
                ):
                    errors.append(
                        f"Line {node.lineno}: Manual essential_fields validation - "
                        f"Pydantic models should handle validation",
                    )

        # Pattern 4: Custom serialize() methods that duplicate Pydantic functionality
        if isinstance(node, ast.FunctionDef):
            if self._is_custom_serialize_method(node):
                errors.append(
                    f"Line {node.lineno}: Custom serialize() method detected - "
                    f"use Pydantic's model_dump() instead",
                )

    def _is_yaml_safe_load(self, node: ast.Call) -> bool:
        """Check if this is a yaml.safe_load() call."""
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "yaml"
                and node.func.attr == "safe_load"
            ):
                return True
        return False

    def _is_in_from_yaml_method(self, node: ast.AST) -> bool:
        """Check if the node is inside a from_yaml classmethod."""
        current_function = getattr(self, "_current_function", None)
        return current_function is not None and current_function.startswith("from_yaml")

    def _extract_allowlist_values(self, config_key: str, dict_key: str) -> list[str]:
        """
        Extract and normalize allowlist values from config.

        Handles both old format (list of strings) and new format (list of dicts).
        Empty strings are filtered out as they are meaningless for matching.

        Args:
            config_key: Top-level config key (e.g., "allowed_files")
            dict_key: Dictionary key when using new format (e.g., "file")

        Returns:
            List of non-empty string values
        """
        raw_values = self.config.get(config_key, [])
        extracted_values = []

        for entry in raw_values:
            if isinstance(entry, dict):
                # New format: {"file": "path", "reason": "..."}
                value = entry.get(dict_key, "")
            elif isinstance(entry, str):
                # Old format: ["path1", "path2"]
                value = entry
            else:
                # Skip invalid entries
                continue

            # Filter out empty strings - they cannot match any actual path/filename/function
            if value:
                extracted_values.append(value)

        return extracted_values

    def _is_in_safe_yaml_loader(self, file_path: Path) -> bool:
        """
        Check if file is in the allowlist for YAML utilities.

        Empty strings are filtered from allowlists as they cannot match real paths.
        """
        # Check filename against allowed filenames
        allowed_filenames = self._extract_allowlist_values(
            "allowed_filenames", "filename"
        )
        if file_path.name in allowed_filenames:
            return True

        # Check full path against allowed files
        allowed_files = self._extract_allowlist_values("allowed_files", "file")
        file_str = str(file_path)
        return any(file_str.endswith(allowed_path) for allowed_path in allowed_files)

    def _is_in_yaml_utility_function(self) -> bool:
        """
        Check if we're in a legitimate YAML utility function.

        Empty strings are filtered from allowlists as they cannot match real function names.
        """
        current_function = getattr(self, "_current_function", None)
        if current_function is None:
            return False

        allowed_functions = self._extract_allowlist_values(
            "allowed_functions", "function"
        )
        return current_function in allowed_functions

    def _is_in_test_file(self, file_path: Path) -> bool:
        """Check if we're in a test file where YAML usage might be legitimate."""
        test_file_patterns = {
            "test_",
            "_test.py",
            "tests/",
        }
        file_str = str(file_path)
        return any(pattern in file_str for pattern in test_file_patterns)

    def _is_yaml_field_access(self, node: ast.Subscript) -> bool:
        """Check if this looks like direct YAML field access (not serialization)."""
        if not (
            isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            return False

        var_name = node.value.id
        field_name = node.slice.value

        # Skip legitimate serialization patterns
        if self._is_serialization_pattern(var_name, field_name):
            return False

        # Common YAML field names that suggest manual validation
        yaml_fields = [
            "node_name",
            "node_type",
            "contract_version",
            "input_model",
            "output_model",
        ]

        # Only flag if variable name suggests YAML data AND it's a known field
        yaml_var_patterns = ["yaml_data", "data", "loaded_data", "config_data"]

        return field_name in yaml_fields and (
            var_name in yaml_var_patterns or "yaml" in var_name.lower()
        )

    def _is_serialization_pattern(self, var_name: str, field_name: str) -> bool:
        """Check if this is a legitimate serialization pattern."""
        # Common serialization variable names
        serialization_vars = [
            "schema",
            "result",
            "context",
            "output",
            "response",
            "payload",
            "export",
            "dict_data",
            "json_data",
            "serialized",
        ]

        # Common serialization field names (broader than YAML validation)
        serialization_fields = [
            "version",
            "description",
            "title",
            "name",
            "status",
            "timestamp",
            "created_at",
            "updated_at",
            "id",
            "uuid",
        ]

        return (
            var_name in serialization_vars
            or field_name in serialization_fields
            or "serialize" in var_name.lower()
            or "export" in var_name.lower()
            or "build" in var_name.lower()
        )

    def validate_all_python_files(self, file_paths: list[Path]) -> bool:
        """Validate all provided Python files."""
        if not file_paths:
            return True

        success = True
        processed_files = 0

        for py_path in file_paths:
            try:
                if not self.validate_python_file(py_path):
                    success = False
                processed_files += 1
            except Exception as e:
                self.errors.append(
                    f"{py_path}: Unexpected error during validation - {e}"
                )
                success = False

        # Sanity check: ensure we processed the expected number of files
        if processed_files != len(file_paths):
            self.errors.append(
                f"Warning: Expected to process {len(file_paths)} files, "
                f"but only processed {processed_files}"
            )

        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ Manual YAML Validation Detection FAILED")
            print("=" * 60)
            print(
                f"Found {len(self.errors)} manual YAML validation violations in {self.checked_files} files:\n",
            )

            for error in self.errors:
                print(f"   • {error}")

            print("\n🔧 How to fix:")
            print("   Replace manual YAML validation with Pydantic model validation:")
            print("   ")
            print("   ❌ BAD:")
            print("   yaml_data = yaml.safe_load(content)")
            print("   if 'node_name' not in yaml_data:")
            print("       # manual validation")
            print("   ")
            print("   ✅ GOOD:")
            print("   model = ModelContract.model_validate(yaml_data)")
            print("   # Pydantic handles all validation automatically")
            print("   ")
            print("   Benefits of Pydantic validation:")
            print("   • Type safety and automatic validation")
            print("   • Consistent error messages")
            print("   • Single source of truth")
            print("   • No validation bypass opportunities")

        else:
            print(
                f"✅ Manual YAML Validation Check PASSED ({self.checked_files} files checked)",
            )


def main() -> int:
    """Main entry point for the validation hook."""
    try:
        # Handle help argument specially
        if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
            print("Usage: validate-no-manual-yaml.py <path1.py> [path2.py] ...")
            print(
                "\nPrecommit hook to prevent manual YAML validation bypassing Pydantic models."
            )
            print(
                "\nThis hook ensures all contract validation goes through backing Pydantic models"
            )
            print(
                "instead of direct YAML validation, maintaining consistency and catching"
            )
            print("real validation issues.")
            print("\nArguments:")
            print("  path1.py [path2.py] ...  Python files to validate")
            return 0 if "--help" in sys.argv or "-h" in sys.argv else 1

        detector = ManualYamlValidationDetector()

        # Process all provided Python files with comprehensive error handling
        python_files = []
        invalid_args = []

        for arg in sys.argv[1:]:
            try:
                path = Path(arg)

                # Check if path exists
                if not path.exists():
                    invalid_args.append(f"File does not exist: {arg}")
                    continue

                # Check if it's a Python file
                if path.suffix != ".py":
                    invalid_args.append(f"Not a Python file: {arg}")
                    continue

                # Check if it's a regular file (not a directory or special file)
                if not path.is_file():
                    invalid_args.append(f"Not a regular file: {arg}")
                    continue

                python_files.append(path)

            except Exception as e:
                invalid_args.append(f"Error processing argument '{arg}': {e}")

        # Report invalid arguments
        if invalid_args:
            print("❌ Argument Processing Errors:")
            for error in invalid_args:
                print(f"   • {error}")

            # Continue with valid files if any exist
            if not python_files:
                print("\nNo valid Python files to process.")
                return 1

        if not python_files:
            print("✅ Manual YAML Validation Check PASSED (no Python files to check)")
            return 0

        try:
            success = detector.validate_all_python_files(python_files)
            detector.print_results()
            return 0 if success else 1
        except Exception as e:
            print(f"❌ Validation process failed: {e}")
            return 1

    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error in main(): {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
