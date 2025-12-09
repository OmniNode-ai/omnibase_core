"""
Comprehensive tests for the validate-all-exports.py validation script.

Tests cover:
- ModuleLevelDefinitionsFinder AST visitor
- AllExtractor AST visitor
- validate_file() function
- should_exclude_file() function
- find_python_files() function
- main() entry point
- Happy paths (valid __all__ exports)
- Violation detection (items in __all__ but not defined)
- File exclusions (__init__.py, test files, archived dirs)
- CLI arguments (--verbose, --warn-missing, paths)
- Edge cases (syntax errors, empty files, no __all__)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

# Import the validation script components
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(SCRIPTS_DIR))

# Use importlib to avoid issues with hyphenated filename
import importlib.util

_script_path = SCRIPTS_DIR / "validate-all-exports.py"
spec = importlib.util.spec_from_file_location("validate_all_exports", _script_path)
if spec is None:
    raise ImportError(f"Cannot find module at {_script_path}")
if spec.loader is None:
    raise ImportError(f"Module spec for {_script_path} has no loader")
validate_all_exports = importlib.util.module_from_spec(spec)
# Add to sys.modules before exec to avoid dataclass issues
sys.modules["validate_all_exports"] = validate_all_exports
spec.loader.exec_module(validate_all_exports)

ModuleLevelDefinitionsFinder = validate_all_exports.ModuleLevelDefinitionsFinder
AllExtractor = validate_all_exports.AllExtractor
ExportValidationResult = validate_all_exports.ExportValidationResult
StarImportInfo = validate_all_exports.StarImportInfo
validate_file = validate_all_exports.validate_file
should_exclude_file = validate_all_exports.should_exclude_file
find_python_files = validate_all_exports.find_python_files
main = validate_all_exports.main

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


class TestExportValidationResult:
    """Tests for the ExportValidationResult named tuple."""

    def test_export_validation_result_creation(self) -> None:
        """Test that ExportValidationResult can be created with all fields."""
        result = ExportValidationResult(
            file_path=Path("/test/file.py"),
            defined_names={"foo", "bar"},
            all_exports={"foo", "bar"},
            extra_exports=set(),
            missing_exports=set(),
            star_imports=[],
            has_all=True,
            is_valid=True,
            error=None,
        )
        assert result.file_path == Path("/test/file.py")
        assert result.defined_names == {"foo", "bar"}
        assert result.all_exports == {"foo", "bar"}
        assert result.extra_exports == set()
        assert result.missing_exports == set()
        assert result.star_imports == []
        assert result.has_all is True
        assert result.is_valid is True
        assert result.error is None


class TestModuleLevelDefinitionsFinder:
    """Tests for the ModuleLevelDefinitionsFinder AST visitor."""

    def test_finds_class_definitions(self) -> None:
        """Test that class definitions are found."""
        import ast

        code = """
class MyClass:
    pass

class AnotherClass:
    def method(self):
        pass
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MyClass" in finder.class_names
        assert "AnotherClass" in finder.class_names
        assert len(finder.class_names) == 2

    def test_finds_function_definitions(self) -> None:
        """Test that function definitions are found."""
        import ast

        code = """
def my_function():
    pass

def another_function(x: int) -> int:
    return x
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "my_function" in finder.function_names
        assert "another_function" in finder.function_names
        assert len(finder.function_names) == 2

    def test_finds_async_function_definitions(self) -> None:
        """Test that async function definitions are found."""
        import ast

        code = """
async def async_function():
    pass

async def another_async(x: int) -> int:
    return x
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "async_function" in finder.function_names
        assert "another_async" in finder.function_names

    def test_finds_constant_assignments(self) -> None:
        """Test that constant assignments are found."""
        import ast

        code = """
MY_CONSTANT = 42
ANOTHER_CONSTANT = "hello"
settings = {}
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MY_CONSTANT" in finder.constant_names
        assert "ANOTHER_CONSTANT" in finder.constant_names
        assert "settings" in finder.constant_names

    def test_finds_annotated_assignments(self) -> None:
        """Test that annotated assignments are found."""
        import ast

        code = """
MY_CONSTANT: int = 42
ANOTHER_CONSTANT: str = "hello"
value: list[int] = []
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MY_CONSTANT" in finder.constant_names
        assert "ANOTHER_CONSTANT" in finder.constant_names
        assert "value" in finder.constant_names

    def test_finds_type_aliases(self) -> None:
        """Test that PEP 695 type aliases are found (Python 3.12+)."""
        import ast

        # This project requires Python 3.12+, so no version check needed
        code = """
type MyType = int | str
type AnotherType = list[int]
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MyType" in finder.constant_names
        assert "AnotherType" in finder.constant_names

    def test_finds_regular_imports(self) -> None:
        """Test that regular imports are found."""
        import ast

        code = """
import os
import sys
import pathlib
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "os" in finder.import_names
        assert "sys" in finder.import_names
        assert "pathlib" in finder.import_names

    def test_finds_aliased_imports(self) -> None:
        """Test that aliased imports are found with their alias names."""
        import ast

        code = """
import numpy as np
import pandas as pd
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "np" in finder.import_names
        assert "pd" in finder.import_names

    def test_finds_from_imports(self) -> None:
        """Test that from imports are found."""
        import ast

        code = """
from pathlib import Path
from os import environ
from typing import Any, Optional
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "Path" in finder.import_names
        assert "environ" in finder.import_names
        assert "Any" in finder.import_names
        assert "Optional" in finder.import_names

    def test_finds_aliased_from_imports(self) -> None:
        """Test that aliased from imports are found."""
        import ast

        code = """
from typing import Optional as Opt
from pathlib import Path as P
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "Opt" in finder.import_names
        assert "P" in finder.import_names
        assert "Opt" in finder.import_aliases
        assert "P" in finder.import_aliases

    def test_ignores_star_imports(self) -> None:
        """Test that star imports are ignored (can't track reliably)."""
        import ast

        code = """
from typing import *
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        # Star imports shouldn't add any names since we can't track them
        assert "*" not in finder.import_names

    def test_ignores_nested_definitions(self) -> None:
        """Test that nested definitions are not included."""
        import ast

        code = """
class OuterClass:
    class InnerClass:
        pass

    def method(self):
        def nested_function():
            pass
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "OuterClass" in finder.class_names
        assert "InnerClass" not in finder.class_names
        assert "method" not in finder.function_names
        assert "nested_function" not in finder.function_names

    def test_ignores_dunder_assignments(self) -> None:
        """Test that __dunder__ assignments are ignored."""
        import ast

        code = """
__all__ = ["foo", "bar"]
__doc__ = "module docstring"
MY_CONSTANT = 42
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "__all__" not in finder.constant_names
        assert "__doc__" not in finder.constant_names
        assert "MY_CONSTANT" in finder.constant_names

    def test_all_defined_names_property(self) -> None:
        """Test the all_defined_names property combines all definitions."""
        import ast

        code = """
import os

class MyClass:
    pass

def my_function():
    pass

MY_CONSTANT = 42
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        all_names = finder.all_defined_names
        assert "os" in all_names
        assert "MyClass" in all_names
        assert "my_function" in all_names
        assert "MY_CONSTANT" in all_names

    def test_public_defined_names_excludes_private(self) -> None:
        """Test that public_defined_names excludes private names."""
        import ast

        code = """
def public_function():
    pass

def _private_function():
    pass

PUBLIC_CONSTANT = 42
_PRIVATE_CONSTANT = 100
"""
        tree = ast.parse(code)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        public_names = finder.public_defined_names
        assert "public_function" in public_names
        assert "_private_function" not in public_names
        assert "PUBLIC_CONSTANT" in public_names
        assert "_PRIVATE_CONSTANT" not in public_names


class TestAllExtractor:
    """Tests for the AllExtractor AST visitor."""

    def test_extracts_all_list(self) -> None:
        """Test extraction of __all__ list."""
        import ast

        code = """
__all__ = ["foo", "bar", "baz"]
"""
        tree = ast.parse(code)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert extractor.all_names == {"foo", "bar", "baz"}
        assert extractor.all_line == 2

    def test_extracts_all_tuple(self) -> None:
        """Test extraction of __all__ tuple."""
        import ast

        code = """
__all__ = ("foo", "bar", "baz")
"""
        tree = ast.parse(code)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert extractor.all_names == {"foo", "bar", "baz"}

    def test_handles_empty_all(self) -> None:
        """Test handling of empty __all__."""
        import ast

        code = """
__all__ = []
"""
        tree = ast.parse(code)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert extractor.all_names == set()

    def test_handles_no_all(self) -> None:
        """Test handling when __all__ is not present."""
        import ast

        code = """
def foo():
    pass
"""
        tree = ast.parse(code)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is False
        assert extractor.all_names == set()
        assert extractor.all_line is None

    def test_ignores_non_string_elements(self) -> None:
        """Test that non-string elements in __all__ are ignored."""
        import ast

        code = """
__all__ = ["foo", 123, "bar", None]
"""
        tree = ast.parse(code)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert extractor.all_names == {"foo", "bar"}


class TestValidateFile:
    """Tests for the validate_file() function."""

    def test_validates_correct_all_exports(self, tmp_path: Path) -> None:
        """Test validation of file with correct __all__."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass

def my_function():
    pass

__all__ = ["MyClass", "my_function"]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.has_all is True
        assert result.extra_exports == set()
        assert len(result.all_exports) == 2

    def test_detects_extra_exports(self, tmp_path: Path) -> None:
        """Test detection of items in __all__ but not defined."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass

__all__ = ["MyClass", "NonExistent", "AnotherMissing"]
""")
        result = validate_file(test_file)

        assert result.is_valid is False
        assert result.has_all is True
        assert "NonExistent" in result.extra_exports
        assert "AnotherMissing" in result.extra_exports
        assert "MyClass" not in result.extra_exports

    def test_handles_file_without_all(self, tmp_path: Path) -> None:
        """Test handling of file without __all__."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.has_all is False
        assert result.error is None

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty file."""
        test_file = tmp_path / "module.py"
        test_file.write_text("")

        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.has_all is False

    def test_handles_syntax_error(self, tmp_path: Path) -> None:
        """Test handling of file with syntax error."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
def incomplete(
""")
        result = validate_file(test_file)

        assert result.is_valid is False
        assert result.error is not None
        assert "Syntax error" in result.error

    def test_warn_missing_detects_unlisted_publics(self, tmp_path: Path) -> None:
        """Test that warn_missing mode detects public names not in __all__."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class PublicClass:
    pass

class AnotherPublic:
    pass

__all__ = ["PublicClass"]
""")
        result = validate_file(test_file, warn_missing=True)

        assert result.is_valid is True  # Not having all publics is a warning, not error
        assert "AnotherPublic" in result.missing_exports

    def test_includes_imports_in_defined_names(self, tmp_path: Path) -> None:
        """Test that imported names can be in __all__."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
from typing import Optional

__all__ = ["Optional"]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.extra_exports == set()


class TestShouldExcludeFile:
    """Tests for the should_exclude_file() function."""

    def test_excludes_init_files(self, tmp_path: Path) -> None:
        """Test that __init__.py files are excluded."""
        init_file = tmp_path / "__init__.py"
        init_file.write_text("")

        assert should_exclude_file(init_file) is True

    def test_excludes_test_files(self, tmp_path: Path) -> None:
        """Test that test files are excluded."""
        test_files = [
            tmp_path / "tests" / "test_module.py",
            tmp_path / "test_something.py",
            tmp_path / "module_test.py",
        ]
        for f in test_files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("")
            assert should_exclude_file(f) is True

    def test_excludes_archived_directories(self, tmp_path: Path) -> None:
        """Test that archived directories are excluded."""
        archived_dirs = [
            tmp_path / "archived" / "module.py",
            tmp_path / "archive" / "module.py",
        ]
        for f in archived_dirs:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("")
            assert should_exclude_file(f) is True

    def test_excludes_validation_scripts(self, tmp_path: Path) -> None:
        """Test that validation scripts themselves are excluded."""
        script_file = tmp_path / "scripts" / "validation" / "validate.py"
        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text("")

        assert should_exclude_file(script_file) is True

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are excluded."""
        cache_file = tmp_path / "__pycache__" / "module.cpython-312.pyc"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("")

        assert should_exclude_file(cache_file) is True

    def test_includes_regular_files(self, tmp_path: Path) -> None:
        """Test that regular Python files are included."""
        regular_file = tmp_path / "module.py"
        regular_file.write_text("")

        assert should_exclude_file(regular_file) is False


class TestFindPythonFiles:
    """Tests for the find_python_files() function."""

    def test_finds_python_files_in_directory(self, tmp_path: Path) -> None:
        """Test finding Python files in a directory."""
        (tmp_path / "module1.py").write_text("")
        (tmp_path / "module2.py").write_text("")
        (tmp_path / "not_python.txt").write_text("")

        files = find_python_files([tmp_path])

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_finds_files_recursively(self, tmp_path: Path) -> None:
        """Test finding files in nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "module1.py").write_text("")
        (subdir / "module2.py").write_text("")

        files = find_python_files([tmp_path])

        assert len(files) == 2

    def test_excludes_test_files(self, tmp_path: Path) -> None:
        """Test that test files are excluded."""
        (tmp_path / "module.py").write_text("")
        (tmp_path / "test_module.py").write_text("")

        files = find_python_files([tmp_path])

        assert len(files) == 1
        assert files[0].name == "module.py"

    def test_excludes_init_files(self, tmp_path: Path) -> None:
        """Test that __init__.py files are excluded."""
        (tmp_path / "module.py").write_text("")
        (tmp_path / "__init__.py").write_text("")

        files = find_python_files([tmp_path])

        assert len(files) == 1
        assert files[0].name == "module.py"

    def test_handles_single_file(self, tmp_path: Path) -> None:
        """Test handling of a single file path."""
        single_file = tmp_path / "module.py"
        single_file.write_text("")

        files = find_python_files([single_file])

        assert len(files) == 1
        assert files[0] == single_file

    def test_handles_multiple_paths(self, tmp_path: Path) -> None:
        """Test handling of multiple paths."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "module1.py").write_text("")
        (dir2 / "module2.py").write_text("")

        files = find_python_files([dir1, dir2])

        assert len(files) == 2

    def test_returns_sorted_files(self, tmp_path: Path) -> None:
        """Test that files are returned sorted."""
        (tmp_path / "zebra.py").write_text("")
        (tmp_path / "alpha.py").write_text("")
        (tmp_path / "beta.py").write_text("")

        files = find_python_files([tmp_path])

        assert files == sorted(files)


class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_returns_zero_for_valid_files(self, tmp_path: Path) -> None:
        """Test that main returns 0 when all files are valid."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass

__all__ = ["MyClass"]
""")
        with patch.object(sys, "argv", ["validate-all-exports.py", str(tmp_path)]):
            result = main()
            assert result == 0

    def test_main_returns_one_for_invalid_files(self, tmp_path: Path) -> None:
        """Test that main returns 1 when violations found."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass

__all__ = ["MyClass", "NonExistent"]
""")
        with patch.object(sys, "argv", ["validate-all-exports.py", str(tmp_path)]):
            result = main()
            assert result == 1

    def test_main_returns_zero_for_files_without_all(self, tmp_path: Path) -> None:
        """Test that files without __all__ are not errors."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass
""")
        with patch.object(sys, "argv", ["validate-all-exports.py", str(tmp_path)]):
            result = main()
            assert result == 0

    def test_main_returns_zero_for_empty_directory(self, tmp_path: Path) -> None:
        """Test that empty directory returns 0."""
        with patch.object(sys, "argv", ["validate-all-exports.py", str(tmp_path)]):
            result = main()
            assert result == 0

    def test_main_verbose_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --verbose flag shows additional output."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class MyClass:
    pass

__all__ = ["MyClass"]
""")
        with patch.object(
            sys, "argv", ["validate-all-exports.py", "--verbose", str(tmp_path)]
        ):
            main()

        captured = capsys.readouterr()
        assert "Validating" in captured.out

    def test_main_warn_missing_flag(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --warn-missing flag shows missing exports."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class PublicClass:
    pass

class AnotherPublic:
    pass

__all__ = ["PublicClass"]
""")
        with patch.object(
            sys, "argv", ["validate-all-exports.py", "--warn-missing", str(tmp_path)]
        ):
            result = main()

        captured = capsys.readouterr()
        # Warnings about missing exports should be shown but not fail
        assert result == 0
        assert (
            "WARNINGS" in captured.out
            or "Missing" in captured.out
            or "warning" in captured.out.lower()
        )

    def test_main_default_path(self) -> None:
        """Test that main uses default path when none specified."""
        with patch.object(sys, "argv", ["validate-all-exports.py"]):
            # Will either find the default dir or handle gracefully
            result = main()
            assert result in (0, 1)

    def test_main_handles_nonexistent_path(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test handling of nonexistent path."""
        with patch.object(
            sys, "argv", ["validate-all-exports.py", "/nonexistent/path"]
        ):
            result = main()
            # find_python_files returns empty list for nonexistent paths
            assert result == 0


class TestComplexModules:
    """Tests for complex module scenarios."""

    def test_validates_module_with_all_definition_types(self, tmp_path: Path) -> None:
        """Test validation of module with all types of definitions."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
import os
from pathlib import Path

class MyClass:
    pass

async def async_function():
    pass

def sync_function():
    pass

MY_CONSTANT: int = 42
SETTINGS = {}

__all__ = [
    "os",
    "Path",
    "MyClass",
    "async_function",
    "sync_function",
    "MY_CONSTANT",
    "SETTINGS",
]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert len(result.extra_exports) == 0

    def test_validates_module_with_partial_exports(self, tmp_path: Path) -> None:
        """Test validation when only some definitions are exported."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class PublicClass:
    pass

class _PrivateClass:
    pass

def public_function():
    pass

def _private_function():
    pass

__all__ = ["PublicClass", "public_function"]
""")
        result = validate_file(test_file, warn_missing=True)

        assert result.is_valid is True
        assert result.extra_exports == set()
        # Private names should not be in missing_exports
        assert "_PrivateClass" not in result.missing_exports
        assert "_private_function" not in result.missing_exports

    def test_handles_multiline_all(self, tmp_path: Path) -> None:
        """Test handling of multiline __all__ definition."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class Foo:
    pass

class Bar:
    pass

__all__ = [
    "Foo",
    "Bar",
]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.all_exports == {"Foo", "Bar"}

    def test_handles_all_with_comments(self, tmp_path: Path) -> None:
        """Test handling of __all__ with comments."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
class Foo:
    pass

class Bar:
    pass

__all__ = [
    "Foo",  # Main class
    "Bar",  # Helper class
]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert result.all_exports == {"Foo", "Bar"}


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_unicode_in_file(self, tmp_path: Path) -> None:
        """Test handling of Unicode content."""
        test_file = tmp_path / "module.py"
        test_file.write_text(
            '''
class MyClass:
    """A class with Unicode: """
    pass

__all__ = ["MyClass"]
''',
            encoding="utf-8",
        )
        result = validate_file(test_file)

        assert result.is_valid is True

    def test_handles_very_long_all_list(self, tmp_path: Path) -> None:
        """Test handling of very long __all__ list."""
        class_defs = "\n".join(f"class Class{i}: pass" for i in range(100))
        all_items = ", ".join(f'"Class{i}"' for i in range(100))

        test_file = tmp_path / "module.py"
        test_file.write_text(f"""
{class_defs}

__all__ = [{all_items}]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
        assert len(result.all_exports) == 100

    def test_handles_dotted_import_in_all(self, tmp_path: Path) -> None:
        """Test handling when only first part of dotted import is available."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
import os.path

# Note: os is available, but os.path would need full specification
__all__ = ["os"]
""")
        result = validate_file(test_file)

        assert result.is_valid is True
