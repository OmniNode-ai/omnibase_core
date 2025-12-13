"""
Unit tests for the validate-all-exports.py validation script.

Tests cover:
- Core functionality (validate_file, should_exclude_file, find_python_files)
- AST edge cases (nested classes, nested functions, type aliases, imports)
- Star import handling
- Error handling (syntax errors, missing files)
- Exclusion patterns
- Cross-platform path handling
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Add scripts directory to path for importing the validation module
scripts_validation_dir = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(scripts_validation_dir))

# Import the module dynamically since it has hyphens in the filename
# We need to use importlib since "validate-all-exports" is not a valid Python identifier
import importlib.util
from importlib import import_module

spec = importlib.util.spec_from_file_location(
    "validate_all_exports", scripts_validation_dir / "validate-all-exports.py"
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load validate-all-exports.py")

validate_all_exports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_all_exports)

# Import classes and functions from the loaded module
ModuleLevelDefinitionsFinder = validate_all_exports.ModuleLevelDefinitionsFinder
AllExtractor = validate_all_exports.AllExtractor
StarImportInfo = validate_all_exports.StarImportInfo
ExportValidationResult = validate_all_exports.ExportValidationResult
validate_file = validate_all_exports.validate_file
should_exclude_file = validate_all_exports.should_exclude_file
find_python_files = validate_all_exports.find_python_files


# Fixtures directory
FIXTURES_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "validation" / "exports"
)


class TestValidateFileCoreFunctionality:
    """Tests for core validate_file() functionality."""

    def test_valid_all_exports_matches_definitions(self) -> None:
        """Test that valid __all__ matching all definitions passes validation."""
        fixture_path = FIXTURES_DIR / "valid_exports.py"
        result = validate_file(fixture_path)

        assert result.is_valid is True
        assert result.has_all is True
        assert result.error is None
        assert len(result.extra_exports) == 0
        assert "MyClass" in result.all_exports
        assert "my_function" in result.all_exports
        assert "MY_CONSTANT" in result.all_exports

    def test_extra_exports_in_all(self) -> None:
        """Test that items in __all__ not defined in module are ERROR cases."""
        fixture_path = FIXTURES_DIR / "extra_exports.py"
        result = validate_file(fixture_path)

        assert result.is_valid is False
        assert result.has_all is True
        assert result.error is None
        assert "NonExistentClass" in result.extra_exports
        assert "ghost_function" in result.extra_exports
        # RealClass is defined, so it should NOT be in extra_exports
        assert "RealClass" not in result.extra_exports

    def test_missing_exports_warning(self) -> None:
        """Test that public names not in __all__ generate warnings with --warn-missing."""
        fixture_path = FIXTURES_DIR / "missing_exports.py"

        # Without warn_missing, no missing_exports
        result_no_warn = validate_file(fixture_path, warn_missing=False)
        assert len(result_no_warn.missing_exports) == 0

        # With warn_missing, should detect missing public names
        result_with_warn = validate_file(fixture_path, warn_missing=True)
        assert "NotExportedClass" in result_with_warn.missing_exports
        assert "not_exported_function" in result_with_warn.missing_exports
        assert "NOT_EXPORTED_CONSTANT" in result_with_warn.missing_exports
        # Private names should NOT be in missing_exports
        assert "_private_function" not in result_with_warn.missing_exports
        assert "_PRIVATE_CONSTANT" not in result_with_warn.missing_exports

    def test_no_all_is_valid(self) -> None:
        """Test that files without __all__ are considered valid (not an error)."""
        fixture_path = FIXTURES_DIR / "no_all.py"
        result = validate_file(fixture_path)

        assert result.is_valid is True
        assert result.has_all is False
        assert result.error is None
        assert len(result.all_exports) == 0


class TestModuleLevelDefinitionsFinder:
    """Tests for the ModuleLevelDefinitionsFinder AST visitor."""

    def test_class_definitions_detected(self) -> None:
        """Test that class definitions at module level are detected."""
        source = """
class MyClass:
    pass

class AnotherClass:
    pass
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MyClass" in finder.class_names
        assert "AnotherClass" in finder.class_names

    def test_function_definitions_detected(self) -> None:
        """Test that function and async function definitions are detected."""
        source = """
def sync_function():
    pass

async def async_function():
    pass
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "sync_function" in finder.function_names
        assert "async_function" in finder.function_names

    def test_constant_assignments_detected(self) -> None:
        """Test that constant assignments (Name = value) are detected."""
        source = """
MY_CONSTANT = 42
ANOTHER_CONSTANT = "string"
typed_var: int = 10
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "MY_CONSTANT" in finder.constant_names
        assert "ANOTHER_CONSTANT" in finder.constant_names
        assert "typed_var" in finder.constant_names

    def test_type_alias_detected(self) -> None:
        """Test that PEP 695 type aliases (Python 3.12+) are detected."""
        fixture_path = FIXTURES_DIR / "type_alias.py"
        result = validate_file(fixture_path)

        assert result.is_valid is True
        assert "MyTypeAlias" in result.defined_names
        assert "MyClass" in result.defined_names

    def test_import_from_detected(self) -> None:
        """Test that 'from x import y' imports are detected."""
        source = """
from os import path
from typing import Any, Optional
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "path" in finder.import_names
        assert "Any" in finder.import_names
        assert "Optional" in finder.import_names

    def test_import_detected(self) -> None:
        """Test that 'import x' statements are detected."""
        source = """
import os
import sys
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "os" in finder.import_names
        assert "sys" in finder.import_names

    def test_import_alias_detected(self) -> None:
        """Test that 'import x as y' and 'from x import y as z' are detected."""
        source = """
import sys as system_module
from typing import Any as AnyType
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert "system_module" in finder.import_names
        assert "AnyType" in finder.import_names
        # Original names should NOT be in import_names when aliased
        assert "sys" not in finder.import_names
        assert "Any" not in finder.import_names

    def test_nested_class_not_detected(self) -> None:
        """Test that classes inside classes are NOT detected as module-level."""
        fixture_path = FIXTURES_DIR / "nested_classes.py"
        result = validate_file(fixture_path)

        # OuterClass should be detected
        assert "OuterClass" in result.defined_names
        # InnerClass and AnotherInner should NOT be detected as module-level
        assert "InnerClass" not in result.defined_names
        assert "AnotherInner" not in result.defined_names

    def test_nested_function_not_detected(self) -> None:
        """Test that functions inside functions are NOT detected as module-level."""
        fixture_path = FIXTURES_DIR / "nested_functions.py"
        result = validate_file(fixture_path)

        # Outer functions should be detected
        assert "outer_function" in result.defined_names
        assert "outer_async_function" in result.defined_names
        # Inner functions should NOT be detected
        assert "inner_function" not in result.defined_names
        assert "inner_async" not in result.defined_names

    def test_dunder_names_excluded(self) -> None:
        """Test that __dunder__ names are excluded from constant_names."""
        # Note: Using __author__ instead of __version__ to avoid triggering
        # validate-string-versions.py which scans for version strings
        source = """
__all__ = ["MyClass"]
__author__ = "Test Author"
MY_CONSTANT = 42
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        # Regular constants should be included
        assert "MY_CONSTANT" in finder.constant_names
        # Dunder names should be excluded
        assert "__all__" not in finder.constant_names
        assert "__author__" not in finder.constant_names

    def test_dotted_import_handling(self) -> None:
        """Test that dotted imports like 'import os.path' are handled correctly."""
        source = """
import os.path
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        # Only the first part is available without alias
        assert "os" in finder.import_names
        assert "os.path" not in finder.import_names


class TestAllExtractor:
    """Tests for the AllExtractor AST visitor."""

    def test_list_all_extraction(self) -> None:
        """Test extraction of __all__ defined as a list."""
        source = """
__all__ = ["Class1", "func1", "CONST1"]
"""
        tree = ast.parse(source)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert "Class1" in extractor.all_names
        assert "func1" in extractor.all_names
        assert "CONST1" in extractor.all_names

    def test_tuple_all_extraction(self) -> None:
        """Test extraction of __all__ defined as a tuple."""
        source = """
__all__ = ("Class1", "func1")
"""
        tree = ast.parse(source)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert "Class1" in extractor.all_names
        assert "func1" in extractor.all_names

    def test_no_all_present(self) -> None:
        """Test when __all__ is not present."""
        source = """
class MyClass:
    pass
"""
        tree = ast.parse(source)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is False
        assert len(extractor.all_names) == 0

    def test_all_line_number_tracked(self) -> None:
        """Test that __all__ line number is tracked."""
        source = """
# Comment line 1
# Comment line 2
__all__ = ["MyClass"]
"""
        tree = ast.parse(source)
        extractor = AllExtractor()
        extractor.visit(tree)

        assert extractor.has_all is True
        assert extractor.all_line == 4


class TestStarImports:
    """Tests for star import handling."""

    def test_star_import_warning(self) -> None:
        """Test that star imports generate warnings (recorded in result)."""
        fixture_path = FIXTURES_DIR / "star_import.py"
        result = validate_file(fixture_path)

        # File should still be valid (star imports are warnings by default)
        assert result.is_valid is True
        assert len(result.star_imports) > 0
        assert result.star_imports[0].module == "os"

    def test_star_import_info_structure(self) -> None:
        """Test StarImportInfo named tuple structure."""
        source = """
from os import *
from sys import *
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert len(finder.star_imports) == 2
        assert finder.star_imports[0].module == "os"
        assert finder.star_imports[0].line_no == 2
        assert finder.star_imports[1].module == "sys"
        assert finder.star_imports[1].line_no == 3

    def test_relative_star_import(self) -> None:
        """Test that relative star imports are tracked with <relative> module name."""
        source = """
from . import *
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        assert len(finder.star_imports) == 1
        assert finder.star_imports[0].module == "<relative>"


class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_handled(self) -> None:
        """Test that syntax errors don't crash and return error result."""
        fixture_path = FIXTURES_DIR / "syntax_error.py"
        result = validate_file(fixture_path)

        assert result.is_valid is False
        assert result.error is not None
        assert "Syntax error" in result.error

    def test_missing_file_handled(self) -> None:
        """Test that missing files are handled gracefully."""
        non_existent_path = FIXTURES_DIR / "non_existent_file.py"
        result = validate_file(non_existent_path)

        assert result.is_valid is False
        assert result.error is not None


class TestShouldExcludeFile:
    """Tests for file exclusion logic."""

    def test_init_files_excluded(self) -> None:
        """Test that __init__.py files are excluded."""
        assert should_exclude_file(Path("src/package/__init__.py")) is True
        assert should_exclude_file(Path("module/__init__.py")) is True

    def test_test_files_excluded(self) -> None:
        """Test that test files are excluded."""
        # Files in tests/ directory
        assert should_exclude_file(Path("tests/unit/test_something.py")) is True
        # Files starting with test_
        assert should_exclude_file(Path("src/test_module.py")) is True
        # Files ending with _test.py
        assert should_exclude_file(Path("src/module_test.py")) is True

    def test_archived_files_excluded(self) -> None:
        """Test that archived/ and archive/ directories are excluded."""
        assert should_exclude_file(Path("src/archived/old_module.py")) is True
        assert should_exclude_file(Path("src/archive/deprecated.py")) is True

    def test_pycache_excluded(self) -> None:
        """Test that __pycache__ directories are excluded."""
        assert (
            should_exclude_file(Path("src/__pycache__/module.cpython-312.pyc")) is True
        )

    def test_validation_scripts_excluded(self) -> None:
        """Test that validation scripts themselves are excluded."""
        assert (
            should_exclude_file(Path("scripts/validation/validate-all-exports.py"))
            is True
        )

    def test_hidden_directories_excluded(self) -> None:
        """Test that hidden directories (starting with .) are excluded."""
        assert should_exclude_file(Path(".git/hooks/pre-commit.py")) is True
        assert should_exclude_file(Path(".venv/lib/module.py")) is True

    def test_regular_files_not_excluded(self) -> None:
        """Test that regular Python files are not excluded."""
        assert should_exclude_file(Path("src/omnibase_core/models/model.py")) is False
        assert should_exclude_file(Path("src/package/module.py")) is False


class TestFindPythonFiles:
    """Tests for file discovery logic."""

    def test_find_files_in_directory(self) -> None:
        """Test finding Python files in a directory.

        Note: We use a temp directory outside 'tests/' since the script
        excludes files under 'tests/' directories.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create some Python files
            (tmp_path / "module1.py").write_text("class Class1: pass")
            (tmp_path / "module2.py").write_text("def func1(): pass")
            # Create a subdirectory with more files
            subdir = tmp_path / "subpackage"
            subdir.mkdir()
            (subdir / "module3.py").write_text("CONST = 1")
            # Create an __init__.py (should be excluded)
            (subdir / "__init__.py").write_text("")

            files = find_python_files([tmp_path])
            file_names = {f.name for f in files}

            assert "module1.py" in file_names
            assert "module2.py" in file_names
            assert "module3.py" in file_names
            # __init__.py should be excluded
            assert "__init__.py" not in file_names

    def test_find_single_file(self) -> None:
        """Test finding a single Python file.

        Note: We use a temp file outside 'tests/' since the script
        excludes files under 'tests/' directories.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            single_file = tmp_path / "single_module.py"
            single_file.write_text("class MyClass: pass")

            files = find_python_files([single_file])

            assert len(files) == 1
            assert files[0] == single_file

    def test_empty_directory(self) -> None:
        """Test finding files in empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = find_python_files([Path(tmpdir)])
            assert files == []

    def test_excluded_directories_skipped(self) -> None:
        """Test that excluded directories (tests, archived, etc.) are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create a regular module
            (tmp_path / "regular.py").write_text("x = 1")
            # Create files in excluded directories
            tests_dir = tmp_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_something.py").write_text("# test")
            archived_dir = tmp_path / "archived"
            archived_dir.mkdir()
            (archived_dir / "old_module.py").write_text("# old")

            files = find_python_files([tmp_path])
            file_names = {f.name for f in files}

            assert "regular.py" in file_names
            assert "test_something.py" not in file_names
            assert "old_module.py" not in file_names


class TestCrossPlatformPathHandling:
    """Tests for cross-platform path handling."""

    def test_path_handling_uses_parts(self) -> None:
        """Test that path handling works across platforms using Path.parts."""
        # Create paths that would work on any platform
        unix_style = Path("src/tests/test_module.py")

        # should_exclude_file uses Path.parts internally
        # This ensures "tests" is detected regardless of separator
        assert should_exclude_file(unix_style) is True

    def test_path_parts_detection(self) -> None:
        """Test that directory components are detected correctly."""
        path = Path("project/archived/old/module.py")
        parts = path.parts

        # Verify parts contains the directory names
        assert "archived" in parts

        # And our function correctly excludes it
        assert should_exclude_file(path) is True


class TestAnnotatedAssignments:
    """Tests for annotated assignment handling."""

    def test_annotated_assignment_detected(self) -> None:
        """Test that annotated assignments are detected."""
        fixture_path = FIXTURES_DIR / "annotated_assignments.py"
        result = validate_file(fixture_path)

        assert result.is_valid is True
        assert "typed_constant" in result.defined_names


class TestImportsAndAliases:
    """Tests for various import patterns."""

    def test_mixed_imports_validated(self) -> None:
        """Test that files with mixed import patterns validate correctly."""
        fixture_path = FIXTURES_DIR / "imports_and_aliases.py"
        result = validate_file(fixture_path)

        assert result.is_valid is True
        assert "os" in result.defined_names
        assert "system_module" in result.defined_names
        assert "Path" in result.defined_names
        assert "AnyType" in result.defined_names


class TestExportValidationResult:
    """Tests for ExportValidationResult named tuple."""

    def test_result_structure(self) -> None:
        """Test ExportValidationResult has expected fields."""
        result = ExportValidationResult(
            file_path=Path("test.py"),
            defined_names={"MyClass"},
            all_exports={"MyClass"},
            extra_exports=set(),
            missing_exports=set(),
            star_imports=[],
            has_all=True,
            is_valid=True,
            error=None,
        )

        assert result.file_path == Path("test.py")
        assert result.defined_names == {"MyClass"}
        assert result.is_valid is True

    def test_result_with_star_import(self) -> None:
        """Test ExportValidationResult with star imports."""
        star_info = StarImportInfo(module="os", line_no=5)
        result = ExportValidationResult(
            file_path=Path("test.py"),
            defined_names={"MyClass"},
            all_exports={"MyClass"},
            extra_exports=set(),
            missing_exports=set(),
            star_imports=[star_info],
            has_all=True,
            is_valid=True,
            error=None,
        )

        assert len(result.star_imports) == 1
        assert result.star_imports[0].module == "os"
        assert result.star_imports[0].line_no == 5


class TestPublicDefinedNames:
    """Tests for public_defined_names property."""

    def test_public_names_excludes_private(self) -> None:
        """Test that public_defined_names excludes private names."""
        source = """
class PublicClass:
    pass

class _PrivateClass:
    pass

def public_function():
    pass

def _private_function():
    pass

PUBLIC_CONSTANT = 1
_PRIVATE_CONSTANT = 2
"""
        tree = ast.parse(source)
        finder = ModuleLevelDefinitionsFinder()
        finder.visit(tree)

        public = finder.public_defined_names

        assert "PublicClass" in public
        assert "public_function" in public
        assert "PUBLIC_CONSTANT" in public

        assert "_PrivateClass" not in public
        assert "_private_function" not in public
        assert "_PRIVATE_CONSTANT" not in public
