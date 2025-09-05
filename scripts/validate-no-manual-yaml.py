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
from typing import List


class ManualYamlValidationDetector:
    """Detects manual YAML validation that bypasses Pydantic models."""

    def __init__(self):
        self.errors: List[str] = []
        self.checked_files = 0

    def validate_python_file(self, py_path: Path) -> bool:
        """Check Python file for manual YAML validation patterns."""
        try:
            with open(py_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST to detect problematic patterns
            tree = ast.parse(content, filename=str(py_path))

            self.checked_files += 1
            file_errors = []

            # Check for manual YAML validation patterns with context tracking
            self._current_function = None
            self._check_node_with_context(tree, py_path, file_errors)

            if file_errors:
                self.errors.extend([f"{py_path}: {error}" for error in file_errors])
                return False

            return True

        except Exception as e:
            self.errors.append(f"{py_path}: Failed to parse Python file - {str(e)}")
            return False

    def _check_node_with_context(
        self, node: ast.AST, file_path: Path, errors: List[str]
    ) -> None:
        """Check AST node with function context tracking."""
        # Track function context
        if isinstance(node, ast.FunctionDef):
            old_function = getattr(self, "_current_function", None)
            self._current_function = node.name

            # Check children
            for child in ast.iter_child_nodes(node):
                self._check_node_with_context(child, file_path, errors)

            # Restore previous context
            self._current_function = old_function
        else:
            # Check this node for validation patterns
            self._check_yaml_validation_patterns(node, file_path, errors)

            # Check children
            for child in ast.iter_child_nodes(node):
                self._check_node_with_context(child, file_path, errors)

    def _check_yaml_validation_patterns(
        self, node: ast.AST, file_path: Path, errors: List[str]
    ) -> None:
        """Check AST node for manual YAML validation patterns."""

        # Pattern 1: yaml.safe_load() followed by model validation
        if isinstance(node, ast.Call):
            if self._is_yaml_safe_load(node) and not self._is_in_from_yaml_method(node):
                errors.append(
                    f"Line {node.lineno}: Found yaml.safe_load() - "
                    f"use Pydantic model.model_validate() instead"
                )

        # Pattern 2: Direct YAML field checking
        if isinstance(node, ast.Subscript):
            if self._is_yaml_field_access(node):
                errors.append(
                    f"Line {node.lineno}: Direct YAML field access detected - "
                    f"use Pydantic model properties instead"
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
                        f"Pydantic models should handle validation"
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
        return getattr(self, "_current_function", None) == "from_yaml"

    def _is_yaml_field_access(self, node: ast.Subscript) -> bool:
        """Check if this looks like direct YAML field access."""
        if (
            isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            # Common YAML field names that suggest manual validation
            yaml_fields = [
                "node_name",
                "node_type",
                "contract_version",
                "version",
                "description",
                "input_model",
                "output_model",
            ]
            if node.slice.value in yaml_fields:
                return True
        return False

    def validate_all_python_files(self, file_paths: List[Path]) -> bool:
        """Validate all provided Python files."""
        success = True

        for py_path in file_paths:
            if not self.validate_python_file(py_path):
                success = False

        return success

    def print_results(self) -> None:
        """Print validation results."""
        if self.errors:
            print("❌ Manual YAML Validation Detection FAILED")
            print("=" * 60)
            print(
                f"Found {len(self.errors)} manual YAML validation violations in {self.checked_files} files:\n"
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
                f"✅ Manual YAML Validation Check PASSED ({self.checked_files} files checked)"
            )


def main() -> int:
    """Main entry point for the validation hook."""
    if len(sys.argv) < 2:
        print("Usage: validate-no-manual-yaml.py <path1.py> [path2.py] ...")
        return 1

    detector = ManualYamlValidationDetector()

    # Process all provided Python files
    python_files = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.suffix == ".py" and path.exists():
            python_files.append(path)

    if not python_files:
        print("✅ Manual YAML Validation Check PASSED (no Python files to check)")
        return 0

    success = detector.validate_all_python_files(python_files)
    detector.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
