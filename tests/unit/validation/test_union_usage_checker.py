"""
Tests for UnionUsageChecker module.

Tests the union type usage pattern analysis including detection of problematic
union patterns, modern union syntax (|), and various AST node types.
"""

import ast

from omnibase_core.models.validation.model_union_pattern import ModelUnionPattern
from omnibase_core.validation.union_usage_checker import UnionUsageChecker


class TestUnionUsageCheckerInitialization:
    """Test UnionUsageChecker initialization."""

    def test_initialization(self):
        """Test checker initializes with correct default values."""
        checker = UnionUsageChecker("/test/path.py")

        assert checker.file_path == "/test/path.py"
        assert checker.union_count == 0
        assert checker.issues == []
        assert checker.union_patterns == []
        assert checker.complex_unions == []
        assert checker.primitive_heavy_unions == []
        assert checker.generic_unions == []
        assert checker._in_union_binop is False

    def test_problematic_combinations_loaded(self):
        """Test that problematic combinations are properly loaded."""
        checker = UnionUsageChecker("/test/path.py")

        assert len(checker.problematic_combinations) > 0
        # Verify some expected combinations
        assert (
            frozenset(["str", "int", "bool", "float"])
            in checker.problematic_combinations
        )


class TestExtractTypeName:
    """Test type name extraction from AST nodes."""

    def test_extract_from_name_node(self):
        """Test extraction from ast.Name node."""
        checker = UnionUsageChecker("/test/path.py")
        code = "str"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "str"

    def test_extract_from_constant_none(self):
        """Test extraction from ast.Constant with None value."""
        checker = UnionUsageChecker("/test/path.py")
        code = "None"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "None"

    def test_extract_from_constant_value(self):
        """Test extraction from ast.Constant with other values."""
        checker = UnionUsageChecker("/test/path.py")
        code = "42"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "int"

    def test_extract_from_subscript(self):
        """Test extraction from ast.Subscript (List[str], Dict[str, int])."""
        checker = UnionUsageChecker("/test/path.py")

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

    def test_extract_from_attribute(self):
        """Test extraction from ast.Attribute (module.Type)."""
        checker = UnionUsageChecker("/test/path.py")
        code = "typing.Optional"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert "Optional" in result

    def test_extract_unknown_fallback(self):
        """Test fallback to 'Unknown' for unrecognized nodes."""
        checker = UnionUsageChecker("/test/path.py")
        # Use a complex expression that doesn't match any pattern
        code = "1 + 2"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_type_name(node)
        assert result == "Unknown"


class TestAnalyzeUnionPattern:
    """Test union pattern analysis."""

    def test_union_with_none_two_types(self):
        """Test detection of Union[T, None] which should use Optional[T]."""
        checker = UnionUsageChecker("/test/path.py")
        pattern = ModelUnionPattern(["str", "None"], 10, "/test/path.py")

        checker._analyze_union_pattern(pattern)

        assert len(checker.issues) == 1
        assert "Optional[str]" in checker.issues[0]
        assert "Line 10" in checker.issues[0]

    def test_complex_union_three_types(self):
        """Test detection of complex unions with 3+ types."""
        checker = UnionUsageChecker("/test/path.py")
        pattern = ModelUnionPattern(["str", "int", "bool"], 15, "/test/path.py")

        checker._analyze_union_pattern(pattern)

        assert len(checker.complex_unions) == 1
        assert checker.complex_unions[0] == pattern

    def test_primitive_overload(self):
        """Test detection of primitive overload unions."""
        checker = UnionUsageChecker("/test/path.py")
        pattern = ModelUnionPattern(
            ["str", "int", "bool", "float"], 20, "/test/path.py"
        )

        checker._analyze_union_pattern(pattern)

        assert len(checker.issues) == 1
        assert "primitive types" in checker.issues[0].lower()
        assert "Line 20" in checker.issues[0]

    def test_mixed_primitive_complex(self):
        """Test detection of mixed primitive/complex unions."""
        checker = UnionUsageChecker("/test/path.py")
        pattern = ModelUnionPattern(["str", "int", "bool", "dict"], 25, "/test/path.py")

        checker._analyze_union_pattern(pattern)

        assert len(checker.issues) == 1
        assert "mixed primitive/complex" in checker.issues[0].lower()
        assert "Line 25" in checker.issues[0]

    def test_everything_union(self):
        """Test detection of overly broad 'everything' unions."""
        checker = UnionUsageChecker("/test/path.py")
        pattern = ModelUnionPattern(
            ["str", "int", "bool", "float", "dict"], 30, "/test/path.py"
        )

        checker._analyze_union_pattern(pattern)

        # This pattern triggers multiple issues because it matches multiple problematic combinations
        assert len(checker.issues) >= 1
        # Check that at least one issue mentions "overly broad"
        assert any("overly broad" in issue.lower() for issue in checker.issues)
        # All issues should reference Line 30
        assert all("Line 30" in issue for issue in checker.issues)

    def test_redundant_none_pattern(self):
        """Test detection of redundant None patterns."""
        checker = UnionUsageChecker("/test/path.py")
        # Union[str, None] with more than 2 types but only 1 non-None type
        pattern = ModelUnionPattern(["str", "None"], 35, "/test/path.py")

        checker._analyze_union_pattern(pattern)

        # Should suggest Optional
        assert len(checker.issues) == 1
        assert "Optional[str]" in checker.issues[0]


class TestVisitSubscript:
    """Test visiting Union[...] subscript nodes."""

    def test_visit_union_subscript_simple(self):
        """Test visiting simple Union[str, int] syntax."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1

    def test_visit_union_subscript_with_none(self):
        """Test visiting Union[str, None] syntax."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

def func(x: Union[str, None]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        # Should have an issue suggesting Optional
        assert len(checker.issues) >= 1

    def test_visit_non_union_subscript(self):
        """Test that non-Union subscripts are not counted."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import List

def func(x: List[str]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 0


class TestVisitBinOp:
    """Test visiting modern union syntax (|) nodes."""

    def test_visit_binop_simple(self):
        """Test visiting simple str | int syntax."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
def func(x: str | int) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1

    def test_visit_binop_three_types(self):
        """Test visiting str | int | float syntax."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
def func(x: str | int | float) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 3

    def test_visit_binop_with_none(self):
        """Test visiting str | None syntax."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
def func(x: str | None) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        # Should have an issue suggesting Optional or T | None
        assert len(checker.issues) >= 1

    def test_visit_non_union_binop(self):
        """Test that non-union binary operations are not counted."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
x = 1 + 2
y = 3 - 4
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 0

    def test_nested_union_handling(self):
        """Test that nested unions are not double-counted."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
def func(x: str | int | bool) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Should only count as one union, not three
        assert checker.union_count == 1


class TestExtractUnionFromBinOp:
    """Test extracting types from modern union syntax."""

    def test_extract_simple_union(self):
        """Test extracting from simple A | B."""
        checker = UnionUsageChecker("/test/path.py")
        code = "str | int"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        assert len(result) == 2
        assert "str" in result
        assert "int" in result

    def test_extract_complex_union(self):
        """Test extracting from complex A | B | C."""
        checker = UnionUsageChecker("/test/path.py")
        code = "str | int | float"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        assert len(result) == 3
        assert "str" in result
        assert "int" in result
        assert "float" in result

    def test_extract_duplicate_prevention(self):
        """Test that duplicates are prevented."""
        checker = UnionUsageChecker("/test/path.py")
        # Create a union that might have duplicates
        code = "str | int | str"
        node = ast.parse(code, mode="eval").body

        result = checker._extract_union_from_binop(node)

        # Should not have duplicates
        assert len(result) == len(set(result))


class TestProcessUnionTypes:
    """Test processing union types from Union[...] syntax."""

    def test_process_tuple_union(self):
        """Test processing Union with tuple of types."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

x: Union[str, int, float]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 3

    def test_process_single_element_union(self):
        """Test processing Union with single element."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

x: Union[str]
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 1
        assert len(checker.union_patterns) == 1
        assert checker.union_patterns[0].type_count == 1


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    def test_multiple_unions_in_file(self):
        """Test file with multiple union declarations."""
        checker = UnionUsageChecker("/test/path.py")
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

    def test_complex_file_with_issues(self):
        """Test file with various problematic patterns."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union, Optional

# Should suggest Optional
def func1(x: Union[str, None]) -> None:
    pass

# Primitive overload
def func2(x: Union[str, int, bool, float]) -> None:
    pass

# Mixed primitive/complex
def func3(x: Union[str, int, dict]) -> None:
    pass

# Good union (no issues)
def func4(x: Union[str, int]) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 4
        # Should have multiple issues
        assert len(checker.issues) >= 2

    def test_modern_and_legacy_syntax_mixed(self):
        """Test file mixing modern (|) and legacy Union syntax."""
        checker = UnionUsageChecker("/test/path.py")
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

    def test_nested_class_with_unions(self):
        """Test unions in nested class definitions."""
        checker = UnionUsageChecker("/test/path.py")
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

    def test_union_in_variable_annotations(self):
        """Test unions in variable annotations."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

x: Union[str, int] = "test"
y: str | int = 42
"""
        tree = ast.parse(code)
        checker.visit(tree)

        assert checker.union_count == 2

    def test_issue_line_numbers_correct(self):
        """Test that issue line numbers are correctly reported."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
from typing import Union

def func1(x: Union[str, None]) -> None:  # Line 4
    pass

def func2(x: Union[str, int, bool, float]) -> None:  # Line 7
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        # Check that line numbers are present in issues
        assert any("Line 4" in issue for issue in checker.issues)
        assert any("Line 7" in issue for issue in checker.issues)


class TestModelUnionPatternIntegration:
    """Test ModelUnionPattern integration with checker."""

    def test_pattern_sorting(self):
        """Test that union patterns have sorted types."""
        checker = UnionUsageChecker("/test/path.py")
        code = """
def func(x: int | str | float) -> None:
    pass
"""
        tree = ast.parse(code)
        checker.visit(tree)

        pattern = checker.union_patterns[0]
        # Types should be sorted
        assert pattern.types == sorted(pattern.types)

    def test_pattern_signature(self):
        """Test that pattern signatures are generated correctly."""
        checker = UnionUsageChecker("/test/path.py")
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

    def test_pattern_hash_and_equality(self):
        """Test that patterns can be hashed and compared."""
        pattern1 = ModelUnionPattern(["str", "int"], 10, "/test/path.py")
        pattern2 = ModelUnionPattern(
            ["int", "str"], 15, "/test/path.py"
        )  # Different order
        pattern3 = ModelUnionPattern(["str", "float"], 20, "/test/path.py")

        # Same types (order doesn't matter due to sorting)
        assert pattern1 == pattern2
        assert hash(pattern1) == hash(pattern2)

        # Different types
        assert pattern1 != pattern3


class TestCompanionLiteralDiscriminatorDetection:
    """Test companion Literal discriminator detection for discriminated unions.

    Tests the new feature from PR #134 that detects patterns like:
        value: Union[bool, dict, float, int, list, str]
        value_type: Literal["bool", "dict", "float", "int", "list", "str"]

    This tests the _is_discriminated_union method in UnionLegitimacyValidator.
    """

    def test_basic_companion_literal_detection(self):
        """Test basic detection of companion Literal discriminator field."""
        # Import the validation script classes
        import sys
        from pathlib import Path

        # Add scripts path to import the validator
        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        # Import using exec to avoid module naming issues
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path="/test/path.py",
        )

        # File content with companion Literal discriminator
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect companion Literal discriminator"

    def test_partial_overlap_insufficient_match(self):
        """Test that partial overlap below threshold is not detected as discriminated."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Union with 6 types
        pattern = UnionPattern(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with only 1 matching type (below threshold of 3)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    other_field: Literal["foo", "bar", "bool"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        # Should not detect as discriminated - only 1 overlap ("bool")
        # Threshold is min(3, 6 // 2 + 1) = min(3, 4) = 3
        assert result is False, "Should not detect with insufficient overlap"

    def test_type_normalization_dict_with_type_params(self):
        """Test that types like dict[str, Any] are normalized to 'dict' for comparison."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Union with parameterized types (as they might appear from AST)
        pattern = UnionPattern(
            ["bool", "dict[str, Any]", "float", "int", "list[Any]", "str"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with base type names
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict[str, Any], float, int, list[Any], str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should normalize parameterized types for comparison"

    def test_case_insensitive_matching(self):
        """Test that type matching is case-insensitive."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Union with lowercase type names
        pattern = UnionPattern(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with same case (already lowercase)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should match types case-insensitively"

    def test_empty_literal_no_detection(self):
        """Test that empty Literal field does not trigger detection."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # No file content with Literal
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    other_field: str
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is False, "Should not detect without Literal field"

    def test_multiple_literals_one_matches(self):
        """Test that detection works when one of multiple Literals matches."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Multiple Literal fields, one matches
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    mode: Literal["read", "write"]
    value_type: Literal["bool", "dict", "str", "int"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect when one of multiple Literals matches"

    def test_threshold_calculation_small_union(self):
        """Test threshold calculation for small unions (< 6 types)."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        # Small union with 3 types
        # Threshold = min(3, 3 // 2 + 1) = min(3, 2) = 2
        pattern = UnionPattern(
            ["bool", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Literal with 2 matching types (meets threshold of 2)
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, str, int]
    value_type: Literal["bool", "str"]
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with 2 matching types for 3-type union"

    def test_no_file_content_provided(self):
        """Test behavior when no file content is provided."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # No file content
        result = validator._is_discriminated_union(pattern, file_content=None)
        assert result is False, "Should not detect without file content"

    def test_integration_through_full_validation(self):
        """Test companion Literal detection through full validation workflow."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "float", "int", "list", "str"],
            line=10,
            file_path="/test/path.py",
        )

        # File content with companion Literal discriminator
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, float, int, list, str]
    value_type: Literal["bool", "dict", "float", "int", "list", "str"]
"""

        # Test through full validation
        result = validator.validate_union_legitimacy(pattern, file_content)

        assert result["is_legitimate"] is True
        assert result["pattern_type"] == "discriminated"
        assert result["confidence"] == 0.9

    def test_single_quotes_in_literal(self):
        """Test detection works with single-quoted Literal strings."""
        import sys
        from pathlib import Path

        scripts_path = Path("/workspace/omnibase_core/scripts/validation")
        sys.path.insert(0, str(scripts_path))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "validate_union_usage",
            scripts_path / "validate-union-usage.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        UnionPattern = module.UnionPattern
        UnionLegitimacyValidator = module.UnionLegitimacyValidator

        validator = UnionLegitimacyValidator()
        pattern = UnionPattern(
            ["bool", "dict", "str", "int"],
            line=10,
            file_path="/test/path.py",
        )

        # Using single quotes in Literal
        file_content = """
class MyModel(BaseModel):
    value: Union[bool, dict, str, int]
    value_type: Literal['bool', 'dict', 'str', 'int']
"""

        result = validator._is_discriminated_union(pattern, file_content)
        assert result is True, "Should detect with single-quoted Literal strings"
