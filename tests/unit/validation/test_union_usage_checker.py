"""
Tests for UnionUsageChecker module.

Tests the union type usage pattern analysis including detection of problematic
union patterns, modern union syntax (|), and various AST node types.
"""

import ast
import importlib.util
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern
from omnibase_core.validation.union_usage_checker import UnionUsageChecker

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_file_path() -> str:
    """Provide a standard test file path for checker initialization.

    Returns:
        A standardized test file path string used across all checker tests.
    """
    return "/test/path.py"


@pytest.fixture
def checker(test_file_path: str) -> UnionUsageChecker:
    """Provide a fresh UnionUsageChecker instance for testing.

    Args:
        test_file_path: The test file path fixture.

    Returns:
        A new UnionUsageChecker instance initialized with the test path.
    """
    return UnionUsageChecker(test_file_path)


@pytest.fixture
def validation_scripts_path() -> Path:
    """Provide the path to validation scripts directory.

    Returns:
        Path to the scripts/validation directory.
    """
    # Dynamically compute path relative to this test file
    # tests/unit/validation/test_union_usage_checker.py -> project root
    return Path(__file__).parent.parent.parent.parent / "scripts" / "validation"


@pytest.fixture
def union_validation_module(
    validation_scripts_path: Path,
) -> Generator[Any, None, None]:
    """Load the validate-union-usage.py module for testing.

    This fixture handles the dynamic import of the validation script,
    eliminating repeated boilerplate in discriminator detection tests.

    Args:
        validation_scripts_path: Path to the validation scripts directory.

    Yields:
        The loaded module containing UnionPattern and UnionLegitimacyValidator.
    """
    # Ensure the scripts path is in sys.path
    scripts_path_str = str(validation_scripts_path)
    path_was_added = scripts_path_str not in sys.path
    if path_was_added:
        sys.path.insert(0, scripts_path_str)

    try:
        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            validation_scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        yield module
    finally:
        # Clean up sys.path only if we added the path
        if path_was_added and scripts_path_str in sys.path:
            sys.path.remove(scripts_path_str)


@pytest.fixture
def union_pattern_class(union_validation_module: Any) -> type:
    """Provide the UnionPattern class from the validation module.

    Args:
        union_validation_module: The loaded validation module.

    Returns:
        The UnionPattern class.
    """
    return union_validation_module.UnionPattern


@pytest.fixture
def union_legitimacy_validator_class(union_validation_module: Any) -> type:
    """Provide the UnionLegitimacyValidator class from the validation module.

    Args:
        union_validation_module: The loaded validation module.

    Returns:
        The UnionLegitimacyValidator class.
    """
    return union_validation_module.UnionLegitimacyValidator


@pytest.fixture
def legitimacy_validator(union_legitimacy_validator_class: type) -> Any:
    """Provide a fresh UnionLegitimacyValidator instance.

    Args:
        union_legitimacy_validator_class: The validator class from the module.

    Returns:
        A new UnionLegitimacyValidator instance.
    """
    return union_legitimacy_validator_class()


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestUnionUsageCheckerInitialization:
    """Test UnionUsageChecker initialization."""

    def test_initialization(self, checker: UnionUsageChecker, test_file_path: str):
        """Test checker initializes with correct default values."""
        assert checker.file_path == test_file_path
        assert checker.union_count == 0
        assert checker.issues == []
        assert checker.union_patterns == []
        assert checker.complex_unions == []
        assert checker.primitive_heavy_unions == []
        assert checker.generic_unions == []
        assert checker._in_union_binop is False

    def test_problematic_combinations_loaded(self, checker: UnionUsageChecker):
        """Test that problematic combinations are properly loaded."""
        assert len(checker.problematic_combinations) > 0
        # Verify some expected combinations
        assert (
            frozenset(["str", "int", "bool", "float"])
            in checker.problematic_combinations
        )


@pytest.mark.unit
class TestExtractTypeName:
    """Test type name extraction from AST nodes."""

    def test_extract_from_name_node(self, checker: UnionUsageChecker):
        """Test extraction from ast.Name node."""
        code = "str"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "str"

    def test_extract_from_constant_none(self, checker: UnionUsageChecker):
        """Test extraction from ast.Constant with None value."""
        code = "None"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "None"

    def test_extract_from_constant_value(self, checker: UnionUsageChecker):
        """Test extraction from ast.Constant with other values."""
        code = "42"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "int"

    def test_extract_from_subscript(self, checker: UnionUsageChecker):
        """Test extraction from ast.Subscript (List[str], Dict[str, int])."""
        # Test List[str]
        code = "List[str]"
        node = ast.parse(code, mode="eval").body
        result = checker._extract_type_name(node)
        assert result == "List"

        # Test Dict[str, int]
        code = "Dict[str, int]"
        node = ast.parse(code, mode="eval").body
        result = checker._extract_type_name(node)
        assert result == "Dict"

    def test_extract_from_attribute(self, checker: UnionUsageChecker):
        """Test extraction from ast.Attribute (module.Type)."""
        code = "typing.Optional"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert "Optional" in result

    def test_extract_unknown_fallback(self, checker: UnionUsageChecker):
        """Test fallback to 'Unknown' for unrecognized nodes."""
        # Use a complex expression that doesn't match any pattern
        code = "1 + 2"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "Unknown"


@pytest.mark.unit
class TestAnalyzeUnionPattern:
    """Test union pattern analysis."""

    def test_union_with_none_two_types_is_valid(
        self, checker: UnionUsageChecker, test_file_path: str
    ):
        """Test that T | None pattern is NOT flagged as violation per ONEX conventions.

        Per ONEX conventions, T | None is the PREFERRED syntax for nullable types
        and should not be flagged as an issue.
        """
        pattern = ModelUnionPattern(["str", "None"], 10, test_file_path)

        checker._analyze_union_pattern(pattern)

        # Per ONEX conventions, T | None is preferred - no issues should be raised
        assert len(checker.issues) == 0

    def test_complex_union_three_types(
        self, checker: UnionUsageChecker, test_file_path: str
    ):
        """Test detection of complex unions with 3+ types."""
        pattern = ModelUnionPattern(["str", "int", "bool"], 15, test_file_path)

        checker._analyze_union_pattern(pattern)

        assert len(checker.complex_unions) == 1
        assert checker.complex_unions[0] == pattern

    def test_primitive_overload(self, checker: UnionUsageChecker, test_file_path: str):
        """Test detection of primitive overload unions."""
        pattern = ModelUnionPattern(["str", "int", "bool", "float"], 20, test_file_path)

        checker._analyze_union_pattern(pattern)

        assert len(checker.issues) == 1
        assert "primitive types" in checker.issues[0].lower()
        assert "Line 20" in checker.issues[0]

    def test_mixed_primitive_complex(
        self, checker: UnionUsageChecker, test_file_path: str
    ):
        """Test detection of mixed primitive/complex unions."""
        pattern = ModelUnionPattern(["str", "int", "bool", "dict"], 25, test_file_path)

        checker._analyze_union_pattern(pattern)

        assert len(checker.issues) == 1
        assert "mixed primitive/complex" in checker.issues[0].lower()
        assert "Line 25" in checker.issues[0]

    def test_everything_union(self, checker: UnionUsageChecker, test_file_path: str):
        """Test detection of overly broad 'everything' unions."""
        pattern = ModelUnionPattern(
            ["str", "int", "bool", "float", "dict"], 30, test_file_path
        )

        checker._analyze_union_pattern(pattern)

        # This pattern triggers multiple issues because it matches multiple problematic combinations
        assert len(checker.issues) >= 1
        # Check that at least one issue mentions "overly broad"
        assert any("overly broad" in issue.lower() for issue in checker.issues)
        # All issues should reference Line 30
        assert all("Line 30" in issue for issue in checker.issues)

    def test_nullable_pattern_not_flagged(
        self, checker: UnionUsageChecker, test_file_path: str
    ):
        """Test that nullable patterns (T | None) are NOT flagged per ONEX conventions.

        Per ONEX conventions, T | None is the PREFERRED syntax for nullable types.
        The validator should not raise any issues for this pattern.
        """
        pattern = ModelUnionPattern(["str", "None"], 35, test_file_path)

        checker._analyze_union_pattern(pattern)

        # Per ONEX conventions, T | None is preferred - no issues should be raised
        assert len(checker.issues) == 0


@pytest.mark.unit
class TestVisitSubscript:
    """Test visiting Union[...] subscript nodes."""

    def test_visit_union_subscript_simple(self, checker: UnionUsageChecker):
        """Test visiting simple Union[str, int] syntax."""
        code = """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1

    def test_visit_union_subscript_with_none(self, checker: UnionUsageChecker):
        """Test visiting Union[str, None] syntax suggests T | None replacement.

        Per ONEX conventions, Union[T, None] should be replaced with T | None.
        The validator should suggest the modern PEP 604 syntax.
        """
        code = """
from typing import Union

def func(x: Union[str, None]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        # Should have an issue suggesting T | None instead of Union[T, None]
        assert len(checker.issues) == 1
        assert "str | None" in checker.issues[0]
        assert "Union[str, None]" in checker.issues[0]

    def test_visit_non_union_subscript(self, checker: UnionUsageChecker):
        """Test that non-Union subscripts are not counted."""
        code = """
from typing import List

def func(x: List[str]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 0


@pytest.mark.unit
class TestVisitBinOp:
    """Test visiting modern union syntax (|) nodes."""

    def test_visit_binop_simple(self, checker: UnionUsageChecker):
        """Test visiting simple str | int syntax."""
        code = """
def func(x: str | int) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1

    def test_visit_binop_three_types(self, checker: UnionUsageChecker):
        """Test visiting str | int | float syntax."""
        code = """
def func(x: str | int | float) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 3

    def test_visit_binop_with_none(self, checker: UnionUsageChecker):
        """Test visiting str | None syntax is NOT flagged per ONEX conventions.

        Per ONEX conventions, T | None is the PREFERRED syntax for nullable types.
        The validator should NOT raise any issues for this pattern.
        """
        code = """
def func(x: str | None) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        # Per ONEX conventions, T | None is preferred - no issues should be raised
        assert len(checker.issues) == 0

    def test_visit_non_union_binop(self, checker: UnionUsageChecker):
        """Test that non-union binary operations are not counted."""
        code = """
x = 1 + 2
y = 3 - 4
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 0

    def test_nested_union_handling(self, checker: UnionUsageChecker):
        """Test that nested unions are not double-counted."""
        code = """
def func(x: str | int | bool) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Should only count as one union, not three
        assert checker.union_count == 1


@pytest.mark.unit
class TestExtractUnionFromBinOp:
    """Test extracting types from modern union syntax."""

    def test_extract_simple_union(self, checker: UnionUsageChecker):
        """Test extracting from simple A | B."""
        code = "str | int"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        assert len(result) == 2
        assert "str" in result
        assert "int" in result

    def test_extract_complex_union(self, checker: UnionUsageChecker):
        """Test extracting from complex A | B | C."""
        code = "str | int | float"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        assert len(result) == 3
        assert "str" in result
        assert "int" in result
        assert "float" in result

    def test_extract_duplicate_prevention(self, checker: UnionUsageChecker):
        """Test that duplicates are prevented."""
        # Create a union that might have duplicates
        code = "str | int | str"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        # Should not have duplicates
        assert len(result) == len(set(result))


@pytest.mark.unit
class TestProcessUnionTypes:
    """Test processing union types from Union[...] syntax."""

    def test_process_tuple_union(self, checker: UnionUsageChecker):
        """Test processing Union with tuple of types."""
        code = """
from typing import Union

x: Union[str, int, float]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 3

    def test_process_single_element_union(self, checker: UnionUsageChecker):
        """Test processing Union with single element."""
        code = """
from typing import Union

x: Union[str]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 1


@pytest.mark.unit
class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    def test_multiple_unions_in_file(self, checker: UnionUsageChecker):
        """Test file with multiple union declarations."""
        code = """
from typing import Union

def func1(x: Union[str, int]) -> None:
    pass

def func2(y: str | float) -> None:
    pass

def func3(z: Union[str, int, bool, float]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 3
        assert len(checker.union_patterns) == 3

    def test_complex_file_with_issues(self, checker: UnionUsageChecker):
        """Test file with various problematic patterns.

        Per ONEX conventions:
        - Union[str, None] should suggest str | None (1 issue)
        - Primitive overload (4+ primitive types) is flagged (1 issue)
        - Union[str, int] is acceptable (no issue for 2-type unions)
        - Union[str, int, float] is NOT flagged (only 3 types, no problematic combo)
        """
        code = """
from typing import Union, Optional

# Should suggest str | None instead of Union[str, None]
def func1(x: Union[str, None]) -> None:
    pass

# Primitive overload - should be flagged
def func2(x: Union[str, int, bool, float]) -> None:
    pass

# Three types but not a problematic combination - not flagged
def func3(x: Union[str, int, float]) -> None:
    pass

# Good union (no issues) - 2 types without None
def func4(x: Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 4
        # Should have 2 issues:
        # 1. Union[str, None] -> str | None suggestion
        # 2. Primitive overload for Union[str, int, bool, float]
        assert len(checker.issues) == 2
        # Check for Union[str, None] -> str | None suggestion
        assert any("str | None" in issue for issue in checker.issues)
        # Check for primitive overload
        assert any("primitive types" in issue.lower() for issue in checker.issues)

    def test_modern_and_legacy_syntax_mixed(self, checker: UnionUsageChecker):
        """Test file mixing modern (|) and legacy Union syntax."""
        code = """
from typing import Union

def func1(x: str | int) -> None:
    pass

def func2(y: Union[float, bool]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 2
        assert len(checker.union_patterns) == 2

    def test_nested_class_with_unions(self, checker: UnionUsageChecker):
        """Test unions in nested class definitions."""
        code = """
from typing import Union

class Outer:
    def method1(self, x: Union[str, int]) -> None:
        pass

    class Inner:
        def method2(self, y: str | float) -> None:
            pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 2

    def test_union_in_variable_annotations(self, checker: UnionUsageChecker):
        """Test unions in variable annotations."""
        code = """
from typing import Union

x: Union[str, int] = "test"
y: str | int = 42
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 2

    def test_issue_line_numbers_correct(self, checker: UnionUsageChecker):
        """Test that issue line numbers are correctly reported.

        Per ONEX conventions:
        - Union[str, None] should suggest str | None (Line 4)
        - Primitive overload (4+ types) is flagged (Line 7)
        """
        code = """
from typing import Union

def func1(x: Union[str, None]) -> None:  # Line 4 - suggest str | None
    pass

def func2(x: Union[str, int, bool, float]) -> None:  # Line 7 - primitive overload
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Should have 2 issues:
        # 1. Union[str, None] -> str | None suggestion (Line 4)
        # 2. Primitive overload (Line 7)
        assert len(checker.issues) == 2
        assert any("Line 4" in issue for issue in checker.issues)
        assert any("Line 7" in issue for issue in checker.issues)
        # Verify the correct issue types
        assert any("str | None" in issue for issue in checker.issues)
        assert any("primitive types" in issue.lower() for issue in checker.issues)


@pytest.mark.unit
class TestModelUnionPatternIntegration:
    """Test ModelUnionPattern integration with checker."""

    def test_pattern_sorting(self, checker: UnionUsageChecker):
        """Test that union patterns have sorted types."""
        code = """
def func(x: int | str | float) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        pattern = checker.union_patterns[0]
        # Types should be sorted
        assert pattern.types == sorted(pattern.types)

    def test_pattern_signature(self, checker: UnionUsageChecker):
        """Test that pattern signatures are generated correctly."""
        code = """
def func(x: str | int) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        pattern = checker.union_patterns[0]
        signature = pattern.get_signature()
        assert "Union[" in signature
        assert "str" in signature
        assert "int" in signature

    def test_pattern_hash_and_equality(self, test_file_path: str):
        """Test that patterns can be hashed and compared."""
        pattern1 = ModelUnionPattern(["str", "int"], 10, test_file_path)
        pattern2 = ModelUnionPattern(
            ["int", "str"], 15, test_file_path
        )  # Different order
        pattern3 = ModelUnionPattern(["str", "float"], 20, test_file_path)

        # Verify object identity: these are different instances
        assert pattern1 is not pattern2
        assert pattern1 is not pattern3
        assert pattern2 is not pattern3

        # Same types (order doesn't matter due to sorting) - value equality
        assert pattern1 == pattern2
        assert hash(pattern1) == hash(pattern2)

        # Different types - value inequality
        assert pattern1 != pattern3
        assert hash(pattern1) != hash(pattern3)


@pytest.mark.unit
class TestCheckerCompanionLiteralDiscriminator:
    """Test companion Literal discriminator detection for discriminated unions.

    Tests the feature that detects patterns like:
        value: Union[bool, dict, float, int, list, str]
        value_type: Literal["bool", "dict", "float", "int", "list", "str"]

    This tests the _is_discriminated_union method in UnionLegitimacyValidator
    via the union_usage_checker module's fixtures.
    """

    def test_basic_companion_literal_detection(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test basic detection of companion Literal discriminator field."""
        pattern = union_pattern_class(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path=test_file_path,
        )

        # File content with companion Literal discriminator
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect companion Literal discriminator"

    def test_partial_overlap_insufficient_match(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that partial overlap below threshold is not detected as discriminated."""
        # Union with 6 types
        pattern = union_pattern_class(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with only 1 matching type (below threshold of 3)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    other_field: Literal["foo", "bar", "bool"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        # Should not detect as discriminated - only 1 overlap ("bool")
        # Threshold is min(3, 6 // 2 + 1) = min(3, 4) = 3
        assert result is False, "Should not detect with insufficient overlap"

    def test_type_normalization_dict_with_type_params(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that types like dict[str, Any] are normalized to 'dict' for comparison."""
        # Union with parameterized types (as they might appear from AST)
        pattern = union_pattern_class(
            ["bool", "dict[str, Any]", "float", "int", "list[Any]", "str"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with base type names
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict[str, Any], float, int, list[Any], str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should normalize parameterized types for comparison"

    def test_case_insensitive_matching(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that type matching is case-insensitive."""
        # Union with lowercase type names
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with same case (already lowercase)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should match types case-insensitively"

    def test_empty_literal_no_detection(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that empty Literal field does not trigger detection."""
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # No file content with Literal
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    other_field: str
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect without Literal field"

    def test_multiple_literals_one_matches(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that detection works when one of multiple Literals matches."""
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Multiple Literal fields, one matches
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    mode: Literal["read", "write"]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect when one of multiple Literals matches"

    def test_threshold_calculation_small_union(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test threshold calculation for small unions (< 6 types)."""
        # Small union with 3 types
        # Threshold = min(3, 3 // 2 + 1) = min(3, 2) = 2
        pattern = union_pattern_class(
            ["bool", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with 2 matching types (meets threshold of 2)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["bool", "str"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with 2 matching types for 3-type union"

    def test_no_file_content_provided(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test behavior when no file content is provided."""
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # No file content
        result = legitimacy_validator._is_discriminated_union(
            pattern, file_content=None
        )
        assert result is False, "Should not detect without file content"

    def test_integration_through_full_validation(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test companion Literal detection through full validation workflow."""
        pattern = union_pattern_class(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path=test_file_path,
        )

        # File content with companion Literal discriminator
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        # Test through full validation
        result = legitimacy_validator.validate_union_legitimacy(pattern, file_content)

        assert result["is_legitimate"] is True
        assert result["pattern_type"] == "discriminated"
        assert result["confidence"] == 0.9

    def test_single_quotes_in_literal(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test detection works with single-quoted Literal strings."""
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Using single quotes in Literal
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal['bool', 'dict', 'str', 'int']
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with single-quoted Literal strings"

    def test_large_union_with_companion_literal(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test detection works for large unions (> 10 types).

        Verifies the threshold calculation works correctly for larger unions
        where the minimum threshold of 3 is used.
        """
        # Large union with 12 types
        large_types = [
            "bool",
            "dict",
            "float",
            "int",
            "list",
            "str",
            "bytes",
            "tuple",
            "set",
            "frozenset",
            "complex",
            "None",
        ]
        pattern = union_pattern_class(
            large_types,
            line=10,
            file_path=test_file_path,
        )

        # Literal with 4 matching types (exceeds threshold of 3)
        file_content = """
class LargeModel(BaseModel):
    value: Union[bool, dict, float, int, list, str, bytes, tuple, set, frozenset, complex, None]
    value_type: Literal["bool", "dict", "float", "int"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect large union with sufficient overlap"

    def test_whitespace_in_type_names(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test that whitespace in type names is handled correctly.

        The implementation uses .strip() to normalize whitespace, so types
        with leading/trailing whitespace should still match.
        """
        # Types with potential whitespace (simulating edge case)
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with matching types
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should handle type names correctly"

    def test_threshold_at_boundary(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test threshold behavior at exact boundary.

        For a 4-type union: threshold = min(3, 4 // 2 + 1) = min(3, 3) = 3
        With exactly 3 matching, it should pass.
        """
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with exactly 3 matching types (at threshold)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal["bool", "dict", "str"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect at exact threshold boundary"

    def test_threshold_one_below_boundary(
        self,
        union_pattern_class: type,
        legitimacy_validator: Any,
        test_file_path: str,
    ):
        """Test threshold behavior one below boundary.

        For a 4-type union: threshold = min(3, 4 // 2 + 1) = min(3, 3) = 3
        With only 2 matching, it should NOT pass.
        """
        pattern = union_pattern_class(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path=test_file_path,
        )

        # Literal with only 2 matching types (below threshold)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal["bool", "dict"]
"""

        result = legitimacy_validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect below threshold boundary"
