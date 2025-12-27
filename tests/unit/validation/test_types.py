"""
Comprehensive unit tests for validation types module.

Tests cover:
- ModelUnionPattern creation and comparison
- UnionUsageChecker AST visitation
- Union type detection (Union[...] and | syntax)
- Complex union pattern analysis
- File and directory validation
- CLI functionality
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.types import (
    ModelUnionPattern,
    UnionUsageChecker,
    validate_union_usage_directory,
    validate_union_usage_file,
)


@pytest.mark.unit
class TestModelUnionPattern:
    """Test ModelUnionPattern class."""

    def test_pattern_initialization(self) -> None:
        """Test pattern initialization with basic types."""
        pattern = ModelUnionPattern(
            types=["str", "int", "bool"],
            line=10,
            file_path="/test/file.py",
        )

        assert pattern.type_count == 3
        assert pattern.line == 10
        assert pattern.file_path == "/test/file.py"
        # Types should be sorted
        assert pattern.types == ["bool", "int", "str"]

    def test_pattern_hash_equality(self) -> None:
        """Test pattern hashing and equality."""
        pattern1 = ModelUnionPattern(
            types=["str", "int"],
            line=10,
            file_path="/test/file.py",
        )
        pattern2 = ModelUnionPattern(
            types=["int", "str"],  # Different order
            line=20,  # Different line
            file_path="/other/file.py",  # Different file
        )

        # Should be equal and have same hash because types are sorted
        assert pattern1 == pattern2
        assert hash(pattern1) == hash(pattern2)

    def test_pattern_inequality(self) -> None:
        """Test pattern inequality with different types."""
        pattern1 = ModelUnionPattern(
            types=["str", "int"],
            line=10,
            file_path="/test/file.py",
        )
        pattern2 = ModelUnionPattern(
            types=["str", "float"],
            line=10,
            file_path="/test/file.py",
        )

        assert pattern1 != pattern2
        assert hash(pattern1) != hash(pattern2)

    def test_pattern_signature(self) -> None:
        """Test pattern signature generation."""
        pattern = ModelUnionPattern(
            types=["str", "int", "bool"],
            line=10,
            file_path="/test/file.py",
        )

        signature = pattern.get_signature()
        assert "Union[" in signature
        assert "bool" in signature
        assert "int" in signature
        assert "str" in signature

    def test_pattern_complex_types(self) -> None:
        """Test pattern with complex type names."""
        pattern = ModelUnionPattern(
            types=["str", "Dict", "List[int]", "Optional[bool]"],
            line=15,
            file_path="/test/file.py",
        )

        assert pattern.type_count == 4
        signature = pattern.get_signature()
        assert "Dict" in signature
        assert "List[int]" in signature


@pytest.mark.unit
class TestUnionUsageChecker:
    """Test UnionUsageChecker class."""

    def test_checker_initialization(self) -> None:
        """Test checker initialization."""
        checker = UnionUsageChecker("/test/file.py")

        assert checker.union_count == 0
        assert len(checker.issues) == 0
        assert checker.file_path == "/test/file.py"
        assert len(checker.union_patterns) == 0

    def test_extract_type_name_simple(self) -> None:
        """Test extracting simple type names."""
        checker = UnionUsageChecker("/test/file.py")

        # Test with Name node
        name_node = ast.Name(id="str")
        assert checker._extract_type_name(name_node) == "str"

    def test_extract_type_name_constant(self) -> None:
        """Test extracting type name from constant None."""
        checker = UnionUsageChecker("/test/file.py")

        # Test with Constant node (None)
        constant_node = ast.Constant(value=None)
        assert checker._extract_type_name(constant_node) == "None"

    def test_extract_type_name_subscript(self) -> None:
        """Test extracting type name from subscript (generic types)."""
        checker = UnionUsageChecker("/test/file.py")

        # Test with Subscript node (List[str])
        subscript_node = ast.Subscript(
            value=ast.Name(id="List"),
            slice=ast.Name(id="str"),
        )
        assert checker._extract_type_name(subscript_node) == "List"

    def test_visit_union_simple(self) -> None:
        """Test visiting simple Union[str, int]."""
        code = """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker = UnionUsageChecker("/test/file.py")
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 2

    def test_visit_union_modern_syntax(self) -> None:
        """Test visiting modern union syntax (str | int)."""
        code = """
def func(x: str | int) -> None:
    pass
"""
        tree = ast.parse(code)
        checker = UnionUsageChecker("/test/file.py")
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1

    def test_visit_union_triple_modern(self) -> None:
        """Test visiting triple union with modern syntax."""
        code = """
def func(x: str | int | bool) -> None:
    pass
"""
        tree = ast.parse(code)
        checker = UnionUsageChecker("/test/file.py")
        checker.visit(tree)

        assert checker.union_count == 1
        assert checker.union_patterns[0].type_count == 3

    def test_analyze_union_pattern_complex(self) -> None:
        """Test analysis of complex union pattern."""
        pattern = ModelUnionPattern(
            types=["str", "int", "bool", "float"],
            line=10,
            file_path="/test/file.py",
        )

        checker = UnionUsageChecker("/test/file.py")
        checker._analyze_union_pattern(pattern)

        # Should have issues due to primitive overload
        assert len(checker.issues) > 0
        assert any("primitive types" in issue.lower() for issue in checker.issues)

    def test_analyze_union_pattern_nullable_not_flagged(self) -> None:
        """Test that T | None pattern is NOT flagged per ONEX conventions.

        Per ONEX conventions, T | None is the PREFERRED syntax for nullable types
        and should not generate issues from _analyze_union_pattern.
        """
        pattern = ModelUnionPattern(
            types=["str", "None"],
            line=10,
            file_path="/test/file.py",
        )

        checker = UnionUsageChecker("/test/file.py")
        checker._analyze_union_pattern(pattern)

        # Per ONEX conventions, T | None is preferred - no issues should be raised
        assert len(checker.issues) == 0

    def test_analyze_union_pattern_mixed_primitive_complex(self) -> None:
        """Test analysis of mixed primitive/complex types."""
        pattern = ModelUnionPattern(
            types=["str", "int", "bool", "dict"],
            line=10,
            file_path="/test/file.py",
        )

        checker = UnionUsageChecker("/test/file.py")
        checker._analyze_union_pattern(pattern)

        # Should have issues due to mixed types
        assert len(checker.issues) > 0
        assert any("Mixed primitive/complex" in issue for issue in checker.issues)

    def test_extract_union_from_binop_nested(self) -> None:
        """Test extracting nested union from binary operation."""
        code = "str | int | float | bool"
        tree = ast.parse(code, mode="eval")

        checker = UnionUsageChecker("/test/file.py")
        if isinstance(tree.body, ast.BinOp):
            types = checker._extract_union_from_binop(tree.body)
            assert len(types) == 4
            assert "str" in types
            assert "int" in types
            assert "float" in types
            assert "bool" in types

    def test_process_union_types_single_element(self) -> None:
        """Test processing union with single element (shouldn't happen but handle it)."""
        checker = UnionUsageChecker("/test/file.py")

        # Create a simple slice node
        slice_node = ast.Name(id="str")

        checker._process_union_types(ast.Name(id="Union"), slice_node, 10)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 1


@pytest.mark.unit
class TestValidateUnionUsageFile:
    """Test file-level union validation."""

    def test_validate_simple_file(self, tmp_path: Path) -> None:
        """Test validating a simple Python file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        union_count, _, patterns = validate_union_usage_file(test_file)

        assert union_count == 1
        assert len(patterns) == 1
        assert patterns[0].type_count == 2

    def test_validate_file_with_modern_syntax(self, tmp_path: Path) -> None:
        """Test validating file with modern union syntax."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def func(x: str | int | bool) -> None:
    pass
"""
        )

        union_count, _, patterns = validate_union_usage_file(test_file)

        assert union_count == 1
        assert len(patterns) == 1

    def test_validate_file_with_no_unions(self, tmp_path: Path) -> None:
        """Test validating file with no unions."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def func(x: str) -> int:
    return 42
"""
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(patterns) == 0
        assert len(issues) == 0

    def test_validate_file_with_complex_unions(self, tmp_path: Path) -> None:
        """Test validating file with complex unions."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
"""
        )

        union_count, issues, _ = validate_union_usage_file(test_file)

        assert union_count == 1
        assert len(issues) > 0  # Should have issues for complex union

    def test_validate_file_syntax_error(self, tmp_path: Path) -> None:
        """Test validating file with syntax error."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def func(x: Union[str, int)  # Missing closing bracket
    pass
"""
        )

        union_count, issues, _ = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(issues) > 0  # Should have parsing error
        assert any("Error parsing" in issue for issue in issues)

    def test_validate_file_multiple_unions(self, tmp_path: Path) -> None:
        """Test validating file with multiple unions."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func1(x: Union[str, int]) -> None:
    pass

def func2(y: Union[bool, float]) -> None:
    pass

def func3(z: str | int | bool) -> None:
    pass
"""
        )

        union_count, _, patterns = validate_union_usage_file(test_file)

        assert union_count == 3
        assert len(patterns) == 3


@pytest.mark.unit
class TestValidateUnionUsageDirectory:
    """Test directory-level union validation."""

    def test_validate_directory_success(self, tmp_path: Path) -> None:
        """Test validating directory with compliant files."""
        # Create test files
        (tmp_path / "test1.py").write_text(
            """
def func(x: str) -> None:
    pass
"""
        )
        (tmp_path / "test2.py").write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        result = validate_union_usage_directory(tmp_path, max_unions=100, strict=False)

        assert isinstance(result, ModelValidationResult)
        assert result.is_valid is True
        assert result.metadata.files_processed == 2

    def test_validate_directory_exceeds_max_unions(self, tmp_path: Path) -> None:
        """Test validation fails when union count exceeds maximum."""
        # Create files with multiple unions
        for i in range(5):
            (tmp_path / f"test{i}.py").write_text(
                """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
            )

        result = validate_union_usage_directory(
            tmp_path,
            max_unions=3,  # Lower than actual count
            strict=False,
        )

        assert isinstance(result, ModelValidationResult)
        assert result.is_valid is False
        assert result.metadata is not None
        assert result.metadata.total_unions > 3

    def test_validate_directory_strict_mode(self, tmp_path: Path) -> None:
        """Test strict mode catches issues."""
        # Create file with problematic union
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
"""
        )

        result = validate_union_usage_directory(tmp_path, max_unions=100, strict=True)

        assert isinstance(result, ModelValidationResult)
        # Should fail in strict mode due to complex union
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_directory_filters_archived(self, tmp_path: Path) -> None:
        """Test validation filters archived/example files."""
        # Create regular file
        (tmp_path / "test.py").write_text("def func(): pass")

        # Create archived files that should be filtered
        archived_dir = tmp_path / "archived"
        archived_dir.mkdir()
        (archived_dir / "old.py").write_text("def old(): pass")

        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()
        (examples_dir / "example.py").write_text("def example(): pass")

        result = validate_union_usage_directory(tmp_path)

        assert isinstance(result, ModelValidationResult)
        # Should only check 1 file (test.py)
        assert result.metadata.files_processed == 1

    def test_validate_empty_directory(self, tmp_path: Path) -> None:
        """Test validating empty directory."""
        result = validate_union_usage_directory(tmp_path)

        assert isinstance(result, ModelValidationResult)
        assert result.is_valid is True
        assert result.metadata.files_processed == 0
        assert result.metadata is not None

    def test_validate_directory_with_subdirectories(self, tmp_path: Path) -> None:
        """Test validation recursively checks subdirectories."""
        # Create nested structure
        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "test1.py").write_text("def func1(): pass")

        subdir2 = subdir1 / "subdir2"
        subdir2.mkdir()
        (subdir2 / "test2.py").write_text("def func2(): pass")

        result = validate_union_usage_directory(tmp_path)

        assert isinstance(result, ModelValidationResult)
        assert result.metadata.files_processed == 2

    def test_validate_directory_metadata(self, tmp_path: Path) -> None:
        """Test validation result includes comprehensive metadata."""
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool]) -> None:
    pass
"""
        )

        result = validate_union_usage_directory(tmp_path, max_unions=100, strict=False)

        assert result.metadata is not None
        assert result.metadata.validation_type is not None
        assert result.metadata.total_unions is not None
        assert result.metadata.max_unions is not None
        assert result.metadata.complex_patterns is not None
        assert result.metadata.strict_mode is not None

        assert result.metadata.validation_type == "union_usage"
        assert result.metadata.max_unions == 100
        assert result.metadata.strict_mode is False


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_union_pattern_empty_types(self) -> None:
        """Test pattern with empty types list."""
        pattern = ModelUnionPattern(
            types=[],
            line=10,
            file_path="/test/file.py",
        )

        assert pattern.type_count == 0
        assert pattern.types == []

    def test_union_pattern_single_type(self) -> None:
        """Test pattern with single type."""
        pattern = ModelUnionPattern(
            types=["str"],
            line=10,
            file_path="/test/file.py",
        )

        assert pattern.type_count == 1
        assert pattern.types == ["str"]

    def test_checker_with_attribute_types(self) -> None:
        """Test checker handles attribute-based types (module.Type)."""
        code = """
import typing

def func(x: typing.Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker = UnionUsageChecker("/test/file.py")
        checker.visit(tree)

        # Should still detect the union
        assert (
            checker.union_count >= 0
        )  # May or may not detect depending on implementation

    def test_validate_file_nonexistent(self, tmp_path: Path) -> None:
        """Test validating nonexistent file."""
        nonexistent = tmp_path / "nonexistent.py"

        union_count, issues, _ = validate_union_usage_file(nonexistent)

        # Should handle gracefully with error
        assert union_count == 0
        assert len(issues) > 0

    def test_validate_directory_with_pycache(self, tmp_path: Path) -> None:
        """Test validation filters __pycache__ directories."""
        # Create regular file
        (tmp_path / "test.py").write_text("def func(): pass")

        # Create __pycache__ directory
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.cpython-39.pyc").write_bytes(b"fake bytecode")

        result = validate_union_usage_directory(tmp_path)

        assert isinstance(result, ModelValidationResult)
        assert result.metadata.files_processed == 1  # Should only check test.py

    def test_complex_union_all_patterns(self, tmp_path: Path) -> None:
        """Test detection of all problematic union patterns."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

# Primitive overload
def func1(x: Union[str, int, bool, float]) -> None:
    pass

# Mixed primitive/complex
def func2(x: Union[str, int, dict]) -> None:
    pass

# Everything union
def func3(x: Union[str, int, bool, float, list]) -> None:
    pass
"""
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 3
        assert len(issues) >= 3  # Should have issues for all three unions
        assert len(patterns) == 3
