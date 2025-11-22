"""
Test suite for YAML validation allowlist accuracy.

This test validates that the .yaml-validation-allowlist.yaml file is accurate:
1. All listed functions actually exist in the codebase
2. All listed functions actually use yaml.safe_load()
3. All listed files actually exist

This prevents the allowlist from becoming stale as the codebase evolves.
"""

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ALLOWLIST_FILE = PROJECT_ROOT / ".yaml-validation-allowlist.yaml"


@pytest.fixture
def allowlist_config() -> dict[str, Any]:
    """Load the YAML validation allowlist configuration."""
    with ALLOWLIST_FILE.open("r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def allowed_files(allowlist_config: dict[str, Any]) -> list[str]:
    """Get list of allowed files from allowlist."""
    return allowlist_config.get("allowed_files", [])


@pytest.fixture
def allowed_functions(allowlist_config: dict[str, Any]) -> list[str]:
    """Get list of allowed functions from allowlist."""
    return allowlist_config.get("allowed_functions", [])


class TestAllowlistFileExistence:
    """Test that all files in the allowlist actually exist."""

    def test_allowed_files_exist(self, allowed_files: list[str]) -> None:
        """Verify all files in allowlist actually exist in the codebase."""
        missing_files = []

        for file_path in allowed_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        assert not missing_files, (
            f"The following files are in the allowlist but don't exist:\n"
            f"{chr(10).join(f'  - {f}' for f in missing_files)}\n\n"
            f"Update .yaml-validation-allowlist.yaml to remove non-existent files."
        )

    def test_allowed_files_are_python_files(self, allowed_files: list[str]) -> None:
        """Verify all allowed files are Python files (.py extension)."""
        non_python_files = [f for f in allowed_files if not f.endswith(".py")]

        assert not non_python_files, (
            f"The following allowed files are not Python files:\n"
            f"{chr(10).join(f'  - {f}' for f in non_python_files)}\n\n"
            f"Only Python files should be in the allowlist."
        )


class TestAllowlistFunctionExistence:
    """Test that all functions in the allowlist actually exist."""

    def _get_function_definitions_from_file(
        self, file_path: Path
    ) -> dict[str, ast.FunctionDef]:
        """
        Parse a Python file and extract all function definitions.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary mapping function names to their AST nodes
        """
        try:
            with file_path.open("r") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return {}

        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = node

        return functions

    def test_allowed_functions_exist_in_allowed_files(
        self, allowed_files: list[str], allowed_functions: list[str]
    ) -> None:
        """Verify all allowed functions actually exist in the allowed files."""
        # Collect all function names from allowed files
        found_functions = set()

        for file_path in allowed_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue  # Skip non-existent files (caught by other test)

            functions = self._get_function_definitions_from_file(full_path)
            found_functions.update(functions.keys())

        # Check which allowed functions are missing
        missing_functions = [
            func for func in allowed_functions if func not in found_functions
        ]

        assert not missing_functions, (
            f"The following functions are in the allowlist but don't exist in allowed files:\n"
            f"{chr(10).join(f'  - {f}' for f in missing_functions)}\n\n"
            f"Update .yaml-validation-allowlist.yaml to remove non-existent functions."
        )


class TestAllowlistFunctionUsesYamlSafeLoad:
    """Test that allowed functions actually use yaml.safe_load()."""

    def _function_uses_yaml_safe_load(
        self, func_node: ast.FunctionDef
    ) -> tuple[bool, list[str]]:
        """
        Check if a function uses yaml.safe_load() or yaml.load().

        Args:
            func_node: AST node for the function

        Returns:
            Tuple of (uses_yaml_load, list_of_yaml_calls)
        """
        yaml_calls = []
        uses_safe_load = False

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # Check for yaml.safe_load() or yaml.load()
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        # Pattern: yaml.safe_load() or yaml.load()
                        if node.func.value.id == "yaml":
                            call_name = node.func.attr
                            yaml_calls.append(call_name)
                            if call_name in ("safe_load", "load"):
                                uses_safe_load = True

        return uses_safe_load, yaml_calls

    def test_allowed_functions_use_yaml_safe_load(
        self, allowed_files: list[str], allowed_functions: list[str]
    ) -> None:
        """
        Verify all allowed functions actually use yaml.safe_load() or yaml.load().

        This ensures the allowlist only contains functions that genuinely need
        yaml.safe_load() access, preventing the allowlist from becoming bloated.
        """
        functions_without_yaml = []

        # Collect all functions from allowed files
        all_functions: dict[str, tuple[Path, ast.FunctionDef]] = {}

        for file_path in allowed_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue  # Skip non-existent files (caught by other test)

            try:
                with full_path.open("r") as f:
                    tree = ast.parse(f.read(), filename=str(full_path))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    all_functions[node.name] = (full_path, node)

        # Check each allowed function
        for func_name in allowed_functions:
            if func_name not in all_functions:
                continue  # Skip non-existent functions (caught by other test)

            file_path, func_node = all_functions[func_name]
            uses_yaml, yaml_calls = self._function_uses_yaml_safe_load(func_node)

            if not uses_yaml:
                functions_without_yaml.append(
                    f"{func_name} (in {file_path.relative_to(PROJECT_ROOT)})"
                )

        assert not functions_without_yaml, (
            f"The following functions are in the allowlist but don't use yaml.safe_load():\n"
            f"{chr(10).join(f'  - {f}' for f in functions_without_yaml)}\n\n"
            f"These functions may no longer need to be in the allowlist.\n"
            f"Review and remove them from .yaml-validation-allowlist.yaml if appropriate."
        )


class TestAllowlistStructure:
    """Test the structure of the allowlist file itself."""

    def test_allowlist_file_exists(self) -> None:
        """Verify the allowlist file exists."""
        assert ALLOWLIST_FILE.exists(), (
            f"YAML validation allowlist not found at {ALLOWLIST_FILE}\n"
            f"Expected file: .yaml-validation-allowlist.yaml in project root"
        )

    def test_allowlist_has_required_sections(
        self, allowlist_config: dict[str, Any]
    ) -> None:
        """Verify allowlist has required sections."""
        required_sections = ["allowed_files", "allowed_filenames", "allowed_functions"]
        missing_sections = [s for s in required_sections if s not in allowlist_config]

        assert not missing_sections, (
            f"Allowlist missing required sections:\n"
            f"{chr(10).join(f'  - {s}' for s in missing_sections)}"
        )

    def test_allowlist_sections_are_lists(
        self, allowlist_config: dict[str, Any]
    ) -> None:
        """Verify all sections in allowlist are lists."""
        sections = ["allowed_files", "allowed_filenames", "allowed_functions"]
        non_list_sections = [
            s for s in sections if not isinstance(allowlist_config.get(s), list)
        ]

        assert not non_list_sections, (
            f"The following allowlist sections are not lists:\n"
            f"{chr(10).join(f'  - {s}' for s in non_list_sections)}"
        )

    def test_allowlist_has_no_duplicates(
        self, allowlist_config: dict[str, Any]
    ) -> None:
        """Verify no duplicate entries in allowlist sections."""
        sections = ["allowed_files", "allowed_filenames", "allowed_functions"]
        duplicates = []

        for section in sections:
            items = allowlist_config.get(section, [])
            seen = set()
            for item in items:
                if item in seen:
                    duplicates.append(f"{section}: {item}")
                seen.add(item)

        assert not duplicates, (
            f"Found duplicate entries in allowlist:\n"
            f"{chr(10).join(f'  - {d}' for d in duplicates)}"
        )


class TestAllowlistCoverage:
    """Test that the allowlist covers all necessary functions."""

    def test_util_safe_yaml_loader_functions_are_allowed(self) -> None:
        """
        Verify key functions in util_safe_yaml_loader.py are in the allowlist.

        These are the core YAML utility functions that MUST be allowed.
        """
        yaml_loader_path = (
            PROJECT_ROOT / "src/omnibase_core/utils/util_safe_yaml_loader.py"
        )

        if not yaml_loader_path.exists():
            pytest.skip("util_safe_yaml_loader.py not found")

        # Parse the file to find functions that use yaml.safe_load()
        with yaml_loader_path.open("r") as f:
            tree = ast.parse(f.read(), filename=str(yaml_loader_path))

        # Find functions that use yaml
        functions_using_yaml = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function uses yaml.safe_load()
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, ast.Call):
                        if isinstance(inner_node.func, ast.Attribute):
                            if isinstance(inner_node.func.value, ast.Name):
                                if (
                                    inner_node.func.value.id == "yaml"
                                    and inner_node.func.attr in ("safe_load", "load")
                                ):
                                    functions_using_yaml.append(node.name)
                                    break

        # Load allowlist
        with ALLOWLIST_FILE.open("r") as f:
            allowlist = yaml.safe_load(f)

        allowed_functions = set(allowlist.get("allowed_functions", []))

        # Check coverage
        missing_functions = [
            f for f in functions_using_yaml if f not in allowed_functions
        ]

        assert not missing_functions, (
            f"The following functions in util_safe_yaml_loader.py use yaml.safe_load() "
            f"but are not in the allowlist:\n"
            f"{chr(10).join(f'  - {f}' for f in missing_functions)}\n\n"
            f"Add these to .yaml-validation-allowlist.yaml"
        )
