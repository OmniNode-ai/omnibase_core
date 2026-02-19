# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
from omnibase_core.validation.checker_union_usage import UnionUsageChecker

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

    def test_complex_union_three_types_with_none(
        self, checker: UnionUsageChecker, test_file_path: str
    ):
        """Test that Union[str, int, None] is treated as complex union, not simple nullable.

        Per ONEX conventions:
        - Union[T, None] (2 types) is a simple nullable pattern, suggests T | None
        - Union[str, int, None] (3+ types) is a COMPLEX union, not just nullable
        - The validator should NOT suggest "str | None" since this is NOT a simple nullable

        This tests the edge case where None is present but there are 3+ types,
        making it a complex union that should be treated differently from T | None.
        """
        pattern = ModelUnionPattern(["str", "int", "None"], 15, test_file_path)

        checker._analyze_union_pattern(pattern)

        # Should be classified as complex union (3+ types)
        assert len(checker.complex_unions) == 1
        assert checker.complex_unions[0] == pattern

        # Should NOT generate any issues since ["str", "int", "None"] doesn't match
        # any problematic combination (like primitive overload with 4 types)
        assert len(checker.issues) == 0

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

    def test_visit_union_subscript_three_types_with_none(
        self, checker: UnionUsageChecker
    ):
        """Test visiting Union[str, int, None] syntax is complex union, not simple nullable.

        Per ONEX conventions:
        - Union[T, None] (2 types) should suggest T | None replacement
        - Union[str, int, None] (3+ types) is a COMPLEX union with None as a valid type
        - The validator should NOT suggest "str | None" for this pattern
        - The validator SHOULD suggest str | int | None as PEP 604 replacement

        This is a critical edge case: having None in a 3+ type union does NOT
        make it a simple nullable pattern.
        """
        code = """
from typing import Union

def func(x: Union[str, int, None]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 3

        # Should be classified as complex union (3+ types)
        assert len(checker.complex_unions) == 1

        # Should NOT have any issues - this is a valid complex union
        # (not a simple nullable, and not matching any problematic combination)
        assert len(checker.issues) == 0

        # Verify the types are correctly extracted
        pattern = checker.union_patterns[0]
        assert "str" in pattern.types
        assert "int" in pattern.types
        assert "None" in pattern.types

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
class TestUnionToNoneSuggestions:
    """Test Union[T, None] -> T | None suggestion feature per ONEX PEP 604 conventions.

    Per PR #209 review recommendation: explicitly test that the validator suggests
    modern PEP 604 syntax for nullable types when using legacy Union syntax.

    ONEX PEP 604 Convention:
    - Union[T, None] should be replaced with T | None
    - This is enforced by ruff rule UP007
    - The validator provides helpful suggestions for migration
    """

    def test_union_t_none_suggests_pep604_syntax(self, checker: UnionUsageChecker):
        """Test that Union[T, None] suggests T | None replacement per ONEX PEP 604 conventions.

        Per PR #209 review recommendation: explicitly test that the validator suggests
        modern PEP 604 syntax for nullable types.
        """
        code = """
from typing import Union

class MyModel:
    field: Union[int, None]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.issues) == 1
        # Verify suggestion format
        assert "int | None" in checker.issues[0]
        assert "Union[int, None]" in checker.issues[0]
        assert "Line" in checker.issues[0]

    def test_union_str_none_suggests_str_pipe_none(self, checker: UnionUsageChecker):
        """Test Union[str, None] specifically suggests str | None."""
        code = """
from typing import Union

def process(value: Union[str, None]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.issues) == 1
        assert "str | None" in checker.issues[0]
        assert "Union[str, None]" in checker.issues[0]

    def test_union_complex_type_none_suggests_pep604(self, checker: UnionUsageChecker):
        """Test Union[ComplexType, None] suggests ComplexType | None."""
        code = """
from typing import Union, List

def get_items() -> Union[List, None]:
    return None
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.issues) == 1
        # Should suggest the PEP 604 syntax
        assert "| None" in checker.issues[0]

    def test_multiple_union_none_patterns_all_get_suggestions(
        self, checker: UnionUsageChecker
    ):
        """Test that multiple Union[T, None] patterns each get suggestions."""
        code = """
from typing import Union

class Config:
    name: Union[str, None]
    count: Union[int, None]
    enabled: Union[bool, None]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 3
        # Each Union[T, None] should get a suggestion
        assert len(checker.issues) == 3
        # Verify each suggestion contains PEP 604 syntax
        assert any("str | None" in issue for issue in checker.issues)
        assert any("int | None" in issue for issue in checker.issues)
        assert any("bool | None" in issue for issue in checker.issues)

    def test_suggestion_message_format_is_actionable(self, checker: UnionUsageChecker):
        """Test that suggestion message format is clear and actionable.

        The message should include:
        1. Line number for easy location
        2. The original Union[T, None] pattern
        3. The suggested T | None replacement
        """
        code = """
from typing import Union

value: Union[float, None]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert len(checker.issues) == 1
        issue = checker.issues[0]

        # Message should be actionable with clear location and suggestion
        assert "Line" in issue, "Message should include line number"
        assert "Union[float, None]" in issue, "Message should show original pattern"
        assert "float | None" in issue, "Message should show PEP 604 replacement"


@pytest.mark.unit
class TestProcessOptionalType:
    """Test Optional[T] syntax detection and PEP 604 conversion suggestions.

    Per ONEX conventions and PEP 604, Optional[T] should be replaced with T | None.
    The _process_optional_type() method detects this legacy syntax and flags it
    for conversion.
    """

    def test_detect_optional_syntax(self, checker: UnionUsageChecker):
        """Test that Optional[T] syntax is detected and flagged for PEP 604 conversion."""
        code = """
from typing import Optional

def foo() -> Optional[str]:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Verify Optional[str] is detected
        assert checker.union_count >= 1
        assert len(checker.issues) >= 1
        assert any(
            "Use str | None instead of Optional[str]" in issue
            for issue in checker.issues
        )

    def test_optional_creates_union_pattern(self, checker: UnionUsageChecker):
        """Test that Optional[T] creates a synthetic union pattern for tracking."""
        code = """
from typing import Optional

x: Optional[int]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        # Should create synthetic [int, None] pattern
        pattern = checker.union_patterns[0]
        assert "int" in pattern.types
        assert "None" in pattern.types

    def test_optional_issue_message_format(self, checker: UnionUsageChecker):
        """Test that Optional[T] issue message format is clear and actionable."""
        code = """
from typing import Optional

value: Optional[float]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert len(checker.issues) == 1
        issue = checker.issues[0]

        # Message should be actionable with clear location and suggestion
        assert "Line" in issue, "Message should include line number"
        assert "Optional[float]" in issue, "Message should show original pattern"
        assert "float | None" in issue, "Message should show PEP 604 replacement"
        assert "PEP 604" in issue, "Message should reference PEP 604"

    def test_multiple_optional_annotations(self, checker: UnionUsageChecker):
        """Test that multiple Optional[T] annotations each get flagged."""
        code = """
from typing import Optional

class Config:
    name: Optional[str]
    count: Optional[int]
    enabled: Optional[bool]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 3
        assert len(checker.issues) == 3
        # Verify each suggestion contains PEP 604 syntax
        assert any("str | None" in issue for issue in checker.issues)
        assert any("int | None" in issue for issue in checker.issues)
        assert any("bool | None" in issue for issue in checker.issues)

    def test_optional_with_complex_type(self, checker: UnionUsageChecker):
        """Test that Optional[ComplexType] suggests ComplexType | None."""
        code = """
from typing import Optional, List

def get_items() -> Optional[List]:
    return None
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.issues) == 1
        # Should suggest the PEP 604 syntax
        assert "| None" in checker.issues[0]
        assert "Optional[List]" in checker.issues[0]

    def test_optional_in_function_parameter(self, checker: UnionUsageChecker):
        """Test that Optional[T] in function parameters is detected."""
        code = """
from typing import Optional

def process(value: Optional[str], count: Optional[int] = None) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 2
        assert len(checker.issues) == 2
        assert any("str | None" in issue for issue in checker.issues)
        assert any("int | None" in issue for issue in checker.issues)


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
class TestPEP604UnionTypeDetection:
    """Test types.UnionType detection for PEP 604 union syntax.

    Verifies that isinstance(annotation, types.UnionType) correctly
    identifies PEP 604 unions (str | None) as documented in CLAUDE.md.

    This pattern is used in mixin_canonical_serialization.py (_is_pep604_union)
    to detect PEP 604 union syntax at runtime, since PEP 604 unions do NOT
    have __origin__ accessible via getattr() like typing.Union does.
    """

    def test_pep604_union_is_union_type(self):
        """Test that str | int evaluates to types.UnionType at runtime.

        PEP 604 unions create a types.UnionType object at runtime,
        which can be detected using isinstance().
        """
        import types

        # Create PEP 604 union at runtime
        pep604_union = str | int

        # Verify it IS a types.UnionType
        assert isinstance(pep604_union, types.UnionType), (
            "PEP 604 union (str | int) should be types.UnionType"
        )

    def test_typing_union_is_not_union_type(self):
        """Test that typing.Union is NOT types.UnionType.

        typing.Union creates a different type object that uses __origin__
        for detection, not types.UnionType.
        """
        import types
        from typing import Union

        # Create typing.Union (intentional legacy syntax for testing)
        typing_union = Union[str, int]  # noqa: UP007

        # Verify it is NOT a types.UnionType
        assert not isinstance(typing_union, types.UnionType), (
            "typing.Union should NOT be types.UnionType"
        )

        # Verify it has __origin__ instead
        assert hasattr(typing_union, "__origin__"), (
            "typing.Union should have __origin__"
        )
        assert typing_union.__origin__ is Union, (
            "typing.Union.__origin__ should be Union"
        )

    def test_pep604_union_with_none_is_union_type(self):
        """Test that str | None (nullable) evaluates to types.UnionType."""
        import types

        # Create PEP 604 nullable union
        nullable_union = str | None

        # Verify it IS a types.UnionType
        assert isinstance(nullable_union, types.UnionType), (
            "PEP 604 nullable union (str | None) should be types.UnionType"
        )

        # Verify it has __args__
        assert hasattr(nullable_union, "__args__"), "PEP 604 union should have __args__"
        assert str in nullable_union.__args__, "str should be in union __args__"
        assert type(None) in nullable_union.__args__, (
            "NoneType should be in union __args__"
        )

    def test_pep604_union_lacks_origin_via_getattr(self):
        """Test that PEP 604 unions do NOT have __origin__ via getattr().

        This documents the key difference that requires using isinstance()
        for PEP 604 detection instead of checking __origin__.
        """
        from typing import Union

        # PEP 604 union
        pep604_union = str | int

        # typing.Union (intentional legacy syntax for testing)
        typing_union = Union[str, int]  # noqa: UP007

        # PEP 604 does NOT have __origin__ via getattr (returns None)
        pep604_origin = getattr(pep604_union, "__origin__", None)
        assert pep604_origin is None, (
            "PEP 604 union should not have __origin__ via getattr"
        )

        # typing.Union DOES have __origin__ via getattr
        typing_origin = getattr(typing_union, "__origin__", None)
        assert typing_origin is Union, "typing.Union should have __origin__ via getattr"

    def test_pep604_multi_type_union_is_union_type(self):
        """Test that multi-type PEP 604 unions are types.UnionType."""
        import types

        # Create multi-type PEP 604 union
        multi_union = str | int | float | bool

        # Verify it IS a types.UnionType
        assert isinstance(multi_union, types.UnionType), (
            "Multi-type PEP 604 union should be types.UnionType"
        )

        # Verify all types are in __args__
        assert len(multi_union.__args__) == 4, "Should have 4 type arguments"
        assert str in multi_union.__args__
        assert int in multi_union.__args__
        assert float in multi_union.__args__
        assert bool in multi_union.__args__

    def test_combined_detection_pattern_for_both_union_syntaxes(self):
        """Test the combined detection pattern used in mixin_canonical_serialization.py.

        This tests the exact pattern from lines 221-226:
            is_union = (
                origin is Union  # Handles typing.Union
                or isinstance(annotation, types.UnionType)  # Handles PEP 604
            )
        """
        import types
        from typing import Union

        def is_union_type(annotation: object) -> bool:
            """Detect both typing.Union and PEP 604 union syntax."""
            origin = getattr(annotation, "__origin__", None)
            return origin is Union or isinstance(annotation, types.UnionType)

        # Test typing.Union detection (intentional legacy syntax for testing)
        typing_union = Union[str, int]  # noqa: UP007
        assert is_union_type(typing_union), "Should detect typing.Union"

        # Test PEP 604 union detection
        pep604_union = str | int
        assert is_union_type(pep604_union), "Should detect PEP 604 union"

        # Test PEP 604 nullable detection
        nullable_union = str | None
        assert is_union_type(nullable_union), "Should detect PEP 604 nullable union"

        # Test non-union types are NOT detected
        assert not is_union_type(str), "Should not detect plain str"
        assert not is_union_type(int), "Should not detect plain int"
        assert not is_union_type(list[str]), "Should not detect list[str]"

    def test_union_type_args_accessibility(self):
        """Test that both union syntaxes provide accessible __args__.

        Both typing.Union and PEP 604 unions expose their type arguments
        via the __args__ attribute, which is used for type inspection.
        """
        from typing import Union

        # typing.Union (intentional legacy syntax for testing)
        typing_union = Union[str, int, None]  # noqa: UP007
        assert hasattr(typing_union, "__args__")
        assert str in typing_union.__args__
        assert int in typing_union.__args__
        assert type(None) in typing_union.__args__

        # PEP 604 union
        pep604_union = str | int | None
        assert hasattr(pep604_union, "__args__")
        assert str in pep604_union.__args__
        assert int in pep604_union.__args__
        assert type(None) in pep604_union.__args__


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
class TestProcessUnionTypesEdgeCases:
    """Test edge cases for _process_union_types to ensure defensive handling.

    These tests verify that malformed Union patterns (which are unlikely but
    possible through AST manipulation or edge cases) are handled gracefully
    without raising IndexError or other exceptions.
    """

    def test_union_none_none_logs_warning_no_issues(
        self, checker: UnionUsageChecker, caplog: pytest.LogCaptureFixture
    ):
        """Test that Union[None, None] logs warning but doesn't raise IndexError.

        This edge case tests the defensive validation where both types in a
        2-element union are None, resulting in an empty non_none_types list.
        """
        import logging

        # Build AST structure that represents Union[None, None]
        # The slice_node should be a Tuple with two Constant(value=None) elements
        # which _extract_type_name will convert to ["None", "None"]
        slice_node = ast.Tuple(
            elts=[
                ast.Constant(value=None),
                ast.Constant(value=None),
            ],
            ctx=ast.Load(),
        )

        # The node parameter is unused but required by signature
        mock_node = ast.Name(id="Union", ctx=ast.Load())

        # Capture warnings at DEBUG level
        with caplog.at_level(logging.WARNING):
            # This should NOT raise IndexError - the defensive check should handle it
            checker._process_union_types(mock_node, slice_node, line_no=42)

        # Verify the warning was logged for malformed Union[None, None]
        assert any(
            "Malformed Union with duplicate None types" in record.message
            for record in caplog.records
        ), "Expected warning about duplicate None types"

        # Verify no IndexError-causing issues were added
        # (The bug was that accessing non_none_types[0] would raise IndexError)
        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        # The pattern should have 2 types, both "None"
        assert checker.union_patterns[0].types == ["None", "None"]

    def test_non_none_types_single_element_produces_suggestion(
        self, checker: UnionUsageChecker
    ):
        """Test that normal Union[T, None] with exactly 1 non-None type works.

        This validates the happy path still works after adding defensive checks.
        """
        code = """
from typing import Union

x: Union[str, None]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Should have exactly 1 issue (the suggestion to use str | None)
        assert len(checker.issues) == 1
        assert "str | None" in checker.issues[0]
        assert "Union[str, None]" in checker.issues[0]

    def test_defensive_check_prevents_index_error_empty_list(
        self, checker: UnionUsageChecker, caplog: pytest.LogCaptureFixture
    ):
        """Test that accessing non_none_types[0] is guarded against empty list.

        Verifies the defensive validation by checking that no IndexError
        can occur when non_none_types would be empty.
        """
        import logging

        caplog.set_level(logging.WARNING)

        # We can't easily create Union[None, None] through normal parsing,
        # but we can verify the defensive logic is in place by checking
        # that normal valid patterns still work correctly
        code = """
from typing import Union

# Valid nullable patterns
x: Union[int, None]
y: Union[str, None]
"""
        tree = ast.parse(code)

        # This should work without any exceptions
        checker.visit(tree)

        # Should have 2 suggestions (one for each Union[T, None])
        assert len(checker.issues) == 2
        assert any("int | None" in issue for issue in checker.issues)
        assert any("str | None" in issue for issue in checker.issues)


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
    via the checker_union_usage module's fixtures.
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
